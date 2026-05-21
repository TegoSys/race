"""Rule 11: Fuel Pressure vs Engine Speed.

Fuel pressure should remain roughly constant across the engine speed range.
Flag if variation exceeds 15% — could indicate failing fuel pump or clogged filter.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class FuelPressure(Rule):
    @property
    def name(self):
        return "Fuel Pressure vs RPM"

    @property
    def description(self):
        return "Fuel pressure should stay constant across engine speed range"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        fc = config.get("fuel_pressure", {})
        max_variation = fc.get("max_variation_pct", 15)

        fuel_pressure = get_channel(df, "Fuel Pressure")
        engine_speed = get_channel(df, "Engine Speed Reference Engine Speed")

        if fuel_pressure is None or engine_speed is None:
            return [Result(Status.WARN, "Missing Fuel Pressure or Engine Speed channels")]

        # Only analyze when engine is running (RPM > 0) and fuel pressure is valid
        valid_mask = (engine_speed > 0) & (fuel_pressure > 0)
        fp = fuel_pressure[valid_mask]
        rpm = engine_speed[valid_mask]

        if len(fp) == 0:
            return [Result(Status.WARN, "No valid fuel pressure data while engine running")]

        # Group by RPM bins and check pressure consistency
        rpm_bins = pd.cut(rpm, bins=[0, 2000, 4000, 6000, 8000, 10000])
        grouped = fp.groupby(rpm_bins).agg(["mean", "std", "min", "max", "count"])

        overall_mean = float(fp.mean())
        overall_min = float(fp.min())
        overall_max = float(fp.max())

        if overall_mean > 0:
            variation_pct = ((overall_max - overall_min) / overall_mean) * 100
        else:
            variation_pct = 0

        if variation_pct > max_variation:
            details_parts = []
            for rpm_bin, row in grouped.iterrows():
                if row["count"] > 5:
                    details_parts.append(
                        f"  RPM {rpm_bin}: mean {row['mean']:.2f} psi (n={int(row['count'])})"
                    )
            details = "Pressure by RPM bin:\n" + "\n".join(details_parts)
            results.append(Result(
                Status.WARN,
                f"Fuel pressure variation {variation_pct:.1f}% across RPM range (threshold: {max_variation}%)",
                details=details,
                value=round(variation_pct, 1),
                threshold=round(max_variation, 1),
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Fuel pressure stable: {variation_pct:.1f}% variation (range [{overall_min:.1f}, {overall_max:.1f}] psi, mean {overall_mean:.1f} psi)",
            ))

        return results
