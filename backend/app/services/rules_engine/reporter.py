"""Generate plain-text compliance report from rule check results."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.services.rules_engine.rules import Status

_COL_WIDTH = 72


class ReportGenerator:
    @staticmethod
    def write(results: list[dict], df, metadata: dict, output_path: str = "rulesCheck.txt") -> None:
        lines: list[str] = []
        lines.append("=" * _COL_WIDTH)
        lines.append("  TRANS AM RACE TELEMETRY — COMPLIANCE & PERFORMANCE REPORT")
        lines.append("=" * _COL_WIDTH)
        lines.append("")
        ReportGenerator._write_header(lines, metadata, df)
        ReportGenerator._write_summary(lines, results)
        ReportGenerator._write_details(lines, results)
        lines.append("")
        lines.append("=" * _COL_WIDTH)
        lines.append(f"  VERDICT: {ReportGenerator._verdict(results)}")
        lines.append("=" * _COL_WIDTH)

        out = Path(output_path)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _write_header(lines: list[str], metadata: dict, df) -> None:
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if metadata:
            for key in ("Log Date", "Venue", "Driver", "Session", "Duration",
                        "Sample Rate", "Vehicle"):
                if key in metadata:
                    lines.append(f"  {key}: {metadata[key]}")
        lines.append(f"  Data rows (after downsample): {len(df)}")
        lines.append(f"  Sensors: {len(df.columns)}")
        lines.append("")

    @staticmethod
    def _write_summary(lines: list[str], results: list[dict]) -> None:
        lines.append("-" * _COL_WIDTH)
        lines.append("  SUMMARY")
        lines.append("-" * _COL_WIDTH)
        lines.append(f"  {'Rule':<38} {'Status':<8} {'Issues':<6}")
        lines.append(f"  {'-' * 38} {'-' * 8} {'-' * 6}")
        fail_count = 0
        warn_count = 0
        for r in results:
            status = r["overall_status"]
            issue_count = sum(1 for res in r["results"] if res.status != Status.PASS)
            lines.append(f"  {r['name']:<38} {status.value:<8} {issue_count:<6}")
            if status == Status.FAIL:
                fail_count += 1
            elif status == Status.WARN:
                warn_count += 1
        lines.append(f"  {'-' * 38} {'-' * 8} {'-' * 6}")
        lines.append(f"  Total: {len(results)} rules | FAIL: {fail_count} | WARN: {warn_count} | PASS: {len(results) - fail_count - warn_count}")
        lines.append("")

    @staticmethod
    def _write_details(lines: list[str], results: list[dict]) -> None:
        lines.append("-" * _COL_WIDTH)
        lines.append("  DETAILS")
        lines.append("-" * _COL_WIDTH)
        for r in results:
            if r["overall_status"] == Status.PASS and not any(
                res.status != Status.PASS for res in r["results"]
            ):
                continue
            lines.append("")
            lines.append(f"  [{r['overall_status'].value}] {r['name']}")
            lines.append(f"  Description: {r['description']}")
            detail_count = 0
            max_details = 50
            for res in r["results"]:
                if res.status == Status.PASS:
                    continue
                if detail_count >= max_details:
                    lines.append(f"    ... (showing {max_details} of {sum(1 for x in r['results'] if x.status != Status.PASS)} issues)")
                    break
                time_info = (f" [{res.time_range[0]:.1f}s - {res.time_range[1]:.1f}s]"
                            if res.time_range else "")
                lines.append(f"    {res.status.value}: {res.message}{time_info}")
                if res.details:
                    lines.append(f"      {res.details}")
                detail_count += 1
        lines.append("")

    @staticmethod
    def _verdict(results: list[dict]) -> str:
        has_fail = any(r["overall_status"] == Status.FAIL for r in results)
        has_warn = any(r["overall_status"] == Status.WARN for r in results)
        if has_fail:
            return "COMPLIANCE ISSUES FOUND — REVIEW REQUIRED"
        if has_warn:
            return "MINOR WARNINGS — MONITOR"
        return "CLEAN — ALL CHECKS PASSED"
