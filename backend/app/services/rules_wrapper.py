from __future__ import annotations
import json
import numpy as np
from .rules_engine.rules import Status, load_config
from .rules_engine.checker import RulesChecker
from .rules_engine.loader import load_csv, _downsample
from ..core.db import db


def _sanitize_for_json(obj):
    """Recursively sanitize NaN/Inf for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.floating):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _severity_from_status(status: Status) -> str:
    return {"FAIL": "critical", "WARN": "warning", "PASS": "info"}[status.value]


class RulesEngine:
    MAX_VIOLATIONS = 2000

    def __init__(self, processor):
        self.processor = processor
        self._config = load_config()

    def get_active_rules(self) -> list[dict]:
        """Return rule metadata with YAML threshold values."""
        checker = RulesChecker()
        checker._initialize()
        rules = []
        for rule in checker._rules:
            config_key = self._config_key_for_rule(rule.__class__.__name__)
            rule_entry = {
                "id": rule.__class__.__name__.lower(),
                "name": rule.name,
                "description": rule.description,
                "config_key": config_key or rule.__class__.__name__.lower(),
                "thresholds": {},
            }
            # Map rule class to config key
            if config_key and config_key in self._config:
                rule_entry["thresholds"] = self._config[config_key]
            rules.append(rule_entry)
        return rules

    @staticmethod
    def _config_key_for_rule(class_name: str) -> str:
        """Map rule class name to YAML config key."""
        mapping = {
            "SensorFault": "sensor_fault",
            "RevLimit": "rev_limit",
            "FuelTrim": "fuel_trim",
            "LambdaCheck": "lambda_check",
            "ManifoldRatio": "manifold_ratio",
            "RamEffect": "ram_effect",
            "FuelConsumption": "fuel_consumption",
            "TopSpeed": "top_speed",
            "BatteryVoltage": "battery_voltage",
            "AirTemperature": "air_temp",
            "FuelPressure": "fuel_pressure",
        }
        return mapping.get(class_name, class_name.lower())

    def run_checks(self, file_id: int, downsample_factor: int = 10) -> int:
        """Run all rules against a file and persist results. Returns summary_id."""
        # Get file path from DB
        res = db.execute("SELECT file_path FROM race_files WHERE id = %s", (file_id,))
        if not res:
            raise ValueError(f"File {file_id} not found")

        file_path = res[0]["file_path"]

        # Load and preprocess CSV
        metadata = {}
        try:
            df, metadata = load_csv(file_path, downsample=1)
            df = _downsample(df, downsample_factor)
        except Exception:
            # Fallback: use processor's MoTeC parser
            df = self.processor._load_csv(file_path)
            df = _downsample(df, downsample_factor)

        # Run rules
        checker = RulesChecker()
        report = checker.run_all(df, metadata)

        # Collect violations
        violations = []
        rule_summaries = {}
        total_violations = 0
        has_fail = False
        has_warn = False

        for rule_result in report:
            rule_id = rule_result["name"]
            overall = rule_result["overall_status"]
            results = rule_result["results"]
            violation_count = 0

            if overall == Status.FAIL:
                has_fail = True
            elif overall == Status.WARN:
                has_warn = True

            for res_item in results:
                if total_violations >= self.MAX_VIOLATIONS:
                    break
                if res_item.status == Status.PASS:
                    continue
                violation_count += 1
                total_violations += 1
                timestamp = None
                if res_item.time_range:
                    timestamp = res_item.time_range[0]
                context = {
                    "details": res_item.details or "",
                    "time_range": list(res_item.time_range) if res_item.time_range else None,
                }
                violations.append({
                    "rule_id": rule_id,
                    "severity": _severity_from_status(res_item.status),
                    "description": res_item.message,
                    "timestamp": timestamp,
                    "value": res_item.value,
                    "context_json": _sanitize_for_json(context),
                })

            rule_summaries[rule_id] = {
                "name": rule_id,
                "status": overall.value,
                "count": violation_count,
            }

        # Determine overall status
        if total_violations == 0:
            status = "PASSED"
        elif has_fail:
            status = "FAILED"
        else:
            status = "WARNING"

        # Save summary
        summary_json = _sanitize_for_json(rule_summaries)
        summary_res = db.execute(
            "INSERT INTO rule_check_summaries (file_id, total_violations, status, summary_json) VALUES (%s, %s, %s, %s) RETURNING id",
            (file_id, total_violations, status, json.dumps(summary_json)),
        )
        summary_id = summary_res[0]["id"]

        # Save violations
        for v in violations:
            db.execute(
                "INSERT INTO rule_violations (summary_id, file_id, rule_id, severity, description, timestamp, value, context_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (summary_id, file_id, v["rule_id"], v["severity"], v["description"],
                 v["timestamp"], v["value"], json.dumps(v["context_json"])),
            )

        return summary_id
