"""Rule 10: Inlet Air Temperature Stability.

Flag wild fluctuations in inlet air temperature (>10C change in <5s).
Fluctuations directly affect fueling to the engine.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class AirTemperature(Rule):
    @property
    def name(self):
        return "Inlet Air Temperature"

    @property
    def description(self):
        return "Inlet air temperature should not have wild fluctuations"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        ac = config.get("air_temp", {})
        max_change = ac.get("max_change_c", 10)
        window_seconds = ac.get("window_seconds", 5)

        air_temp = get_channel(df, "Inlet Air Temperature")
        engine_speed = get_channel(df, "Engine Speed Reference Engine Speed")
        if air_temp is None:
            return [Result(Status.WARN, "Missing Inlet Air Temperature channel")]

        # Only check when we have valid temperature readings and engine is running
        valid_mask = air_temp > 0
        if engine_speed is not None:
            valid_mask = valid_mask & (engine_speed > 500)
        valid = air_temp[valid_mask]

        if len(valid) == 0:
            return [Result(Status.WARN, "No valid air temperature data while engine running")]

        # At 100Hz downsampled 10x = 10Hz, so window_seconds * 10 samples
        window_size = window_seconds * 10

        # Use rolling window to detect rapid changes (only on valid data)
        temp_diff = valid.diff().abs()
        rolling_max = temp_diff.rolling(window=window_size, min_periods=1).max()

        spike_mask = rolling_max > max_change
        spikes = int(spike_mask.sum())

        if spikes > 0:
            spike_indices = spike_mask[spike_mask].index
            if len(spike_indices) > 0:
                peak_change = float(rolling_max.max())
                results.append(Result(
                    Status.WARN,
                    f"{spikes} sample(s) with air temperature change >{max_change}C within {window_seconds}s window",
                    details=f"First spike at index {spike_indices[0]}. "
                            f"Temp range while running: [{float(valid.min()):.1f}C, {float(valid.max()):.1f}C]",
                    value=round(peak_change, 1),
                    threshold=round(max_change, 1),
                ))
        else:
            mean_temp = float(valid.mean())
            results.append(Result(
                Status.PASS,
                f"Air temperature stable while running: mean {mean_temp:.1f}C, max delta <{max_change}C per {window_seconds}s",
            ))

        return results
