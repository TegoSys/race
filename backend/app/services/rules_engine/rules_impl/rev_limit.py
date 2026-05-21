"""Rule 2: Engine Rev Limit (TA2: 6800 RPM).

Ensure engine speed does not exceed 6800 RPM for more than 0.25s.
Check that no performance advantage was gained (speed didn't increase >5.5 mph).
Exclude traction events where inertia causes overshoot.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class RevLimit(Rule):
    @property
    def name(self):
        return "Rev Limit (TA2 6800 RPM)"

    @property
    def description(self):
        return "Engine speed must not exceed 6800 RPM for >0.25s with performance advantage"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        rc = config.get("rev_limit", {})
        max_rpm = rc.get("max_rpm", 6800)
        max_samples = rc.get("max_duration_samples", 3)
        speed_limit = rc.get("speed_advantage_mph", 5.5)

        engine_speed = get_channel(df, "Engine Speed Reference Engine Speed")
        gps_speed = get_channel(df, "GPS Speed")
        brake_state = get_channel(df, "Brake State")

        if engine_speed is None:
            return [Result(Status.WARN, "Missing 'Engine Speed Reference Engine Speed' channel")]

        # Find all segments where RPM exceeds limit
        over_mask = engine_speed > max_rpm
        segments = self._find_segments(over_mask)

        violations = []
        for start, end in segments:
            if (end - start + 1) < max_samples:
                continue  # Too brief to matter
            # Check for traction event: brake off and speed decreasing
            is_traction = False
            if gps_speed is not None and brake_state is not None:
                speed_delta = gps_speed.iloc[end] - gps_speed.iloc[start]
                if speed_delta <= 0:
                    is_traction = True
            # Check for advantage: speed increased more than threshold
            has_advantage = False
            if gps_speed is not None:
                speed_delta = gps_speed.iloc[end] - gps_speed.iloc[start]
                if speed_delta > speed_limit:
                    has_advantage = True

            if has_advantage and not is_traction:
                peak_rpm = float(engine_speed.iloc[start:end + 1].max())
                violations.append(Result(
                    Status.FAIL,
                    f"Rev limit exceeded: peak {peak_rpm:.0f} RPM for {end - start + 1} samples with advantage",
                    time_range=(float(start / 10), float(end / 10)),
                    value=peak_rpm,
                    threshold=max_rpm,
                ))
            elif not is_traction:
                peak_rpm = float(engine_speed.iloc[start:end + 1].max())
                violations.append(Result(
                    Status.WARN,
                    f"Rev limit exceeded: peak {peak_rpm:.0f} RPM for {end - start + 1} samples (no speed advantage)",
                    time_range=(float(start / 10), float(end / 10)),
                    value=peak_rpm,
                    threshold=max_rpm,
                ))
            else:
                violations.append(Result(
                    Status.PASS,
                    f"Rev overshoot at traction event (inertia): {end - start + 1} samples — exempted",
                    time_range=(float(start / 10), float(end / 10)),
                ))

        if not violations:
            results.append(Result(Status.PASS, f"No significant rev limit violations (>{max_rpm} RPM)"))
        else:
            results.extend(violations)

        return results

    @staticmethod
    def _find_segments(mask: pd.Series) -> list[tuple[int, int]]:
        """Return list of (start_idx, end_idx) for contiguous True segments."""
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
