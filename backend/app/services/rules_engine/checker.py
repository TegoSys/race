"""Rules orchestrator — loads all rules and runs them against telemetry data."""
from __future__ import annotations

import pandas as pd
from app.services.rules_engine.rules import (
    Rule, Status, Result, get_registry, load_all_rules, load_config,
)


class RulesChecker:
    def __init__(self, wot_threshold: int = 95):
        self.wot_threshold = wot_threshold
        self._rules: list[Rule] = []
        self._config = {}

    def _initialize(self):
        if not self._rules:
            load_all_rules()
            self._config = load_config()
            self._rules = list(self._config.values()) if False else \
                [cls() for cls in sorted(get_registry().values(),
                                         key=lambda c: c.__name__)]

    def run_all(self, df: pd.DataFrame, metadata: dict) -> list[dict]:
        """Run every registered rule and collect structured results.

        Returns list of dicts: {name, description, results, overall_status}
        """
        self._initialize()
        report = []
        for rule in self._rules:
            try:
                results = rule.check(df, self._config)
            except Exception as exc:
                results = [Result(Status.FAIL, f"Rule error: {exc}")]
            overall = self._worst_status(results)
            report.append({
                "name": rule.name,
                "description": rule.description,
                "results": results,
                "overall_status": overall,
            })
        return report

    @staticmethod
    def _worst_status(results: list[Result]) -> Status:
        if not results:
            return Status.PASS
        if any(r.status == Status.FAIL for r in results):
            return Status.FAIL
        if any(r.status == Status.WARN for r in results):
            return Status.WARN
        return Status.PASS
