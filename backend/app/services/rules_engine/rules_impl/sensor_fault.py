"""Rule 1: Sensor Fault Detection.

Flag columns where values hit extreme sentinel values for many consecutive samples,
indicating a sensor malfunction rather than a true reading.
"""
import numpy as np
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class SensorFault(Rule):
    @property
    def name(self):
        return "Sensor Fault Detection"

    @property
    def description(self):
        return "Detect sensors stuck at max/min sentinel values indicating faults"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        threshold = config.get("sensor_fault", {}).get("consecutive_samples", 10)
        faulty_channels = []

        for col in df.columns:
            series = df[col]
            if series.nunique(dropna=True) <= 1:
                continue  # constant column, skip
            col_min = series.min()
            col_max = series.max()
            # Check if max value is stuck at a round sentinel number
            for sentinel in [col_max, col_min]:
                if sentinel == 0:
                    continue
                mask = (series == sentinel)
                run_lengths = self._max_consecutive(mask)
                if run_lengths >= threshold:
                    faulty_channels.append(
                        f"  {col}: stuck at {sentinel} for {run_lengths} consecutive samples"
                    )

        if faulty_channels:
            results.append(Result(
                Status.WARN,
                f"Potential sensor faults detected in {len(faulty_channels)} channel(s)",
                details="\n".join(faulty_channels[:10]),  # limit output
                value=float(len(faulty_channels)),
                threshold=float(threshold),
            ))
        else:
            results.append(Result(Status.PASS, "No sensor faults detected"))

        return results

    @staticmethod
    def _max_consecutive(mask: pd.Series) -> int:
        if not mask.any():
            return 0
        groups = mask.astype(int).groupby((~mask).cumsum()).sum()
        return int(groups.max()) if len(groups) > 0 else 0
