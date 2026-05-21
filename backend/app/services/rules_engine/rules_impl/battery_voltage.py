"""Rule 9: ECU Battery Voltage Check.

Battery voltage should be stable at 13.4-13.8V.
Flag if drops below 11V or exceeds 13.8V sustained.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class BatteryVoltage(Rule):
    @property
    def name(self):
        return "ECU Battery Voltage"

    @property
    def description(self):
        return "ECU battery voltage should stay within 13.4-13.8V range"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        bc = config.get("battery_voltage", {})
        target_low = bc.get("target_low", 13.4)
        target_high = bc.get("target_high", 13.8)
        fail_low = bc.get("fail_low", 11.0)
        sustain = bc.get("sustain_samples", 5)

        battery = get_channel(df, "ECU Battery Voltage")
        engine_speed = get_channel(df, "Engine Speed Reference Engine Speed")
        if battery is None:
            return [Result(Status.WARN, "Missing ECU Battery Voltage channel")]

        valid = battery[battery > 0]
        if len(valid) == 0:
            return [Result(Status.WARN, "No valid battery voltage data")]

        # Only check target range when engine is running
        if engine_speed is not None:
            engine_running = engine_speed > 500
            valid = battery[engine_running & (battery > 0)]

        if len(valid) == 0:
            return [Result(Status.WARN, "No valid battery voltage data while engine running")]

        mean_v = float(valid.mean())
        min_v = float(valid.min())
        max_v = float(valid.max())

        # Check for critical drops (always check, even engine off)
        low_mask = battery < fail_low
        segments = self._find_segments(low_mask)
        for start, end in segments:
            if end - start + 1 >= sustain:
                min_seg = float(battery.iloc[start:end + 1].min())
                results.append(Result(
                    Status.FAIL,
                    f"Critical: battery voltage dropped below {fail_low}V for {end - start + 1} samples",
                    time_range=(float(start / 10), float(end / 10)),
                    value=round(min_seg, 2),
                    threshold=round(fail_low, 2),
                ))

        # Only check target range when engine is running
        if engine_speed is not None:
            engine_running = engine_speed > 500

            # Check for sustained high voltage while running
            high_mask = engine_running & (battery > target_high)
            segments = self._find_segments(high_mask)
            for start, end in segments:
                if end - start + 1 >= sustain:
                    max_seg = float(battery.iloc[start:end + 1].max())
                    results.append(Result(
                        Status.WARN,
                        f"Battery voltage above {target_high}V sustained for {end - start + 1} samples",
                        time_range=(float(start / 10), float(end / 10)),
                        value=round(max_seg, 2),
                        threshold=round(target_high, 2),
                    ))

            # Check for sustained low voltage while running
            target_low_mask = engine_running & (battery >= fail_low) & (battery < target_low)
            segments = self._find_segments(target_low_mask)
            for start, end in segments:
                if end - start + 1 >= sustain:
                    min_seg = float(battery.iloc[start:end + 1].min())
                    results.append(Result(
                        Status.WARN,
                        f"Battery voltage below {target_low}V while engine running for {end - start + 1} samples",
                        time_range=(float(start / 10), float(end / 10)),
                        value=round(min_seg, 2),
                        threshold=round(target_low, 2),
                    ))

        if not results:
            results.append(Result(
                Status.PASS,
                f"ECU battery voltage stable while running: mean {mean_v:.2f}V, range [{min_v:.2f}, {max_v:.2f}]",
            ))

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
