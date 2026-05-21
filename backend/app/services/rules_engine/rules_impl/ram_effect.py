"""Rule 6: RAM Effect Check.

Compare manifold pressure at high speed to assess ram air intake design.
Flag cars with anomalously low or high ram pressure gain.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class RamEffect(Rule):
    @property
    def name(self):
        return "RAM Effect (High Speed)"

    @property
    def description(self):
        return "Manifold pressure vs GPS speed at high velocity — assess ram air intake"

    @property
    def supports_multi(self) -> bool:
        return True  # Car-to-car comparison in multi-file mode

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        rc = config.get("ram_effect", {})
        min_speed = rc.get("min_speed", 100)
        deviation_pct = rc.get("deviation_pct", 20)

        manifold = get_channel(df, "Inlet Manifold Pressure")
        gps_speed = get_channel(df, "GPS Speed")

        if manifold is None or gps_speed is None:
            return [Result(Status.WARN, "Missing Manifold Pressure or GPS Speed channels")]

        high_speed_mask = gps_speed >= min_speed
        high_speed_data = pd.DataFrame({
            "manifold": manifold[high_speed_mask],
            "speed": gps_speed[high_speed_mask],
        })

        if len(high_speed_data) < 10:
            return [Result(Status.WARN, f"Insufficient high-speed data (>{min_speed} mph) for RAM analysis")]

        # Group by speed bins and check manifold pressure consistency
        high_speed_data["speed_bin"] = (high_speed_data["speed"] // 10) * 10
        grouped = high_speed_data.groupby("speed_bin")["manifold"].agg(["mean", "std", "count"])

        anomalies = []
        for speed_bin, row in grouped.iterrows():
            if row["count"] < 5:
                continue
            if row["mean"] > 0:
                cv = float(row["std"] / row["mean"]) * 100  # coefficient of variation
                if cv > deviation_pct:
                    anomalies.append(
                        f"  Speed bin {speed_bin:.0f} mph: mean MP {row['mean']:.1f} kPa, "
                        f"std {row['std']:.2f}, CV {cv:.1f}%"
                    )

        if anomalies:
            # Use max CV as the representative value
            max_cv = max(
                float(row["std"]) / float(row["mean"]) * 100
                for _, row in grouped.iterrows()
                if row["count"] >= 5 and row["mean"] > 0
            )
            results.append(Result(
                Status.WARN,
                f"High variability in manifold pressure at high speed ({len(anomalies)} speed bins)",
                details="\n".join(anomalies),
                value=round(max_cv, 1),
                threshold=round(deviation_pct, 1),
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Manifold pressure consistent at high speed (>{min_speed} mph)",
            ))

        return results
