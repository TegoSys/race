"""Rule 3: Fuel Closed Loop Trim Check.

Ensure Bank 1/2 fuel trims stay within firmware limits (±20).
Flag if sustained above warning threshold for >15 seconds.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class FuelTrim(Rule):
    @property
    def name(self):
        return "Fuel Closed Loop Trim"

    @property
    def description(self):
        return "Fuel trim values should stay within firmware PID limits (±20)"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        fc = config.get("fuel_trim", {})
        warn_limit = fc.get("warn_limit", 15)
        fail_limit = fc.get("fail_limit", 20)
        sustain_seconds = fc.get("sustain_seconds", 15)

        trim1 = get_channel(df, "Fuel Closed Loop Control Bank 1 Trim")
        trim2 = get_channel(df, "Fuel Closed Loop Control Bank 2 Trim")

        if trim1 is None and trim2 is None:
            return [Result(Status.WARN, "Missing Fuel Closed Loop Trim channels")]

        for label, series in [("Bank 1", trim1), ("Bank 2", trim2)]:
            if series is None:
                continue
            abs_trim = series.abs()

            # Check for sustained high trim
            warn_mask = abs_trim > warn_limit
            segments = self._find_segments(warn_mask)
            for start, end in segments:
                duration_samples = end - start + 1
                if duration_samples >= sustain_seconds:
                    peak = float(abs_trim.iloc[start:end + 1].max())
                    status = Status.FAIL if peak >= fail_limit else Status.WARN
                    thresh = fail_limit if status == Status.FAIL else warn_limit
                    results.append(Result(
                        status,
                        f"{label} trim sustained above {warn_limit}: peak {peak:.1f} for {duration_samples} samples",
                        time_range=(float(start / 10), float(end / 10)),
                        value=peak,
                        threshold=thresh,
                    ))

            # Check for any instant failures at firmware limit
            fail_mask = abs_trim >= fail_limit
            instant_fails = int(fail_mask.sum())
            if instant_fails > 0:
                results.append(Result(
                    Status.WARN,
                    f"{label} trim hit firmware limit ({fail_limit}) {instant_fails} times",
                    value=float(abs_trim[abs_trim >= fail_limit].max()),
                    threshold=fail_limit,
                ))

        if not results:
            results.append(Result(Status.PASS, "Fuel trim values within acceptable range"))

        return results

    @staticmethod
    def _find_segments(mask: pd.Series) -> list[tuple[int, int]]:
        segments = []
        start = None
        for i, v in enumerate(mask):
            if v and start is None:
                start = i
            elif not v and start is not None:
                segments.append((start, i - 1))
                start = None
        if start is not None:
            segments.append((start, len(mask) - 1))
        return segments
