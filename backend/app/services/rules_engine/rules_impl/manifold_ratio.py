"""Rule 5: Manifold Pressure Ratio Check.

Calculate ambient-to-manifold pressure ratio during WOT.
Most cars should form a consistent valley at full power.
Flag if ratio deviates >15% from the session median.
"""
import numpy as np
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class ManifoldRatio(Rule):
    @property
    def name(self):
        return "Manifold Pressure Ratio"

    @property
    def description(self):
        return "Ambient/Manifold pressure ratio during WOT should be consistent"

    @property
    def supports_multi(self) -> bool:
        return True  # Can compare car-to-car in multi-file mode

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        mc = config.get("manifold_ratio", {})
        deviation_pct = mc.get("deviation_pct", 15)

        ambient = get_channel(df, "Ambient Pressure")
        manifold = get_channel(df, "Inlet Manifold Pressure")
        throttle = get_channel(df, "Throttle Position")

        if ambient is None or manifold is None or throttle is None:
            return [Result(Status.WARN, "Missing Ambient Pressure, Manifold Pressure, or Throttle Position channels")]

        wot_mask = throttle >= 95
        wot_ambient = ambient[wot_mask]
        wot_manifold = manifold[wot_mask]

        if len(wot_ambient) == 0 or wot_manifold.sum() == 0:
            return [Result(Status.WARN, "No WOT data available for manifold ratio analysis")]

        # Calculate ratio: ambient / manifold (should be ~1.08-1.1 with restrictor)
        ratio = wot_ambient / wot_manifold.replace(0, np.nan).dropna()
        if len(ratio) == 0:
            return [Result(Status.WARN, "Unable to calculate manifold ratio (zero manifold pressure)")]

        median_ratio = float(ratio.median())
        threshold = deviation_pct / 100.0
        deviation_mask = (ratio.abs() - median_ratio).abs() / median_ratio > threshold
        outlier_count = int(deviation_mask.sum())
        total = len(ratio)

        if outlier_count > total * 0.1:  # More than 10% of WOT samples are outliers
            results.append(Result(
                Status.FAIL,
                f"Manifold ratio highly inconsistent: {outlier_count}/{total} WOT samples deviate >{deviation_pct}% from median ({median_ratio:.3f})",
                details="May indicate intake system inconsistency or sensor issue. Compare car-to-car in multi-file mode.",
                value=round(median_ratio, 3),
                threshold=round(deviation_pct, 1),
            ))
        elif outlier_count > 0:
            results.append(Result(
                Status.WARN,
                f"{outlier_count}/{total} WOT samples deviate >{deviation_pct}% from median ratio ({median_ratio:.3f})",
                details=f"Ratio range: [{ratio.min():.3f}, {ratio.max():.3f}]",
                value=round(median_ratio, 3),
                threshold=round(deviation_pct, 1),
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Manifold ratio consistent during WOT: median {median_ratio:.3f}, range [{ratio.min():.3f}, {ratio.max():.3f}]",
            ))

        return results
