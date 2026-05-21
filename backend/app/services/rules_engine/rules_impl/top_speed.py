"""Rule 8: Top Speed Evaluation.

Track peak GPS Speed per lap and compare lap-to-lap.
Flag if delta between consecutive laps exceeds threshold.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class TopSpeed(Rule):
    @property
    def name(self):
        return "Top Speed (Lap Comparison)"

    @property
    def description(self):
        return "Peak GPS speed per lap should be consistent — flag large lap-to-lap deltas"

    @property
    def supports_multi(self) -> bool:
        return True  # Compare top speeds across cars

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        tc = config.get("top_speed", {})
        delta_mph = tc.get("delta_mph", 5)

        gps_speed = get_channel(df, "GPS Speed")
        lap_number = get_channel(df, "Lap Number")

        if gps_speed is None or lap_number is None:
            return [Result(Status.WARN, "Missing GPS Speed or Lap Number channels")]

        # Filter out invalid speeds
        valid_mask = gps_speed > 0
        speed_series = gps_speed[valid_mask]
        lap_series = lap_number[valid_mask]

        if len(speed_series) == 0:
            return [Result(Status.WARN, "No valid GPS speed data")]

        # Get max speed per lap
        df_lap = pd.DataFrame({"lap": lap_series, "speed": speed_series})
        lap_max = df_lap.groupby("lap")["speed"].max()

        if len(lap_max) < 2:
            return [Result(Status.WARN, "Insufficient lap data for top speed comparison")]

        # Check consecutive lap deltas
        deltas = lap_max.diff().abs()
        outliers = deltas[deltas > delta_mph]

        if len(outliers) > 0:
            max_delta = float(outliers.max())
            details = "\n".join(
                f"  Lap {int(lap)}: delta {delta:.1f} mph (top speed: {lap_max[lap]:.1f} mph)"
                for lap, delta in outliers.items()
            )
            results.append(Result(
                Status.WARN,
                f"{len(outliers)} lap(s) with top speed delta >{delta_mph} mph",
                details=details,
                value=round(max_delta, 1),
                threshold=round(delta_mph, 1),
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Top speed consistent across {len(lap_max)} laps (max delta: {float(deltas.max()):.1f} mph)",
            ))

        return results
