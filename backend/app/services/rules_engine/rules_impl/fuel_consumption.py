"""Rule 7: Fuel Consumption during WOT events.

Compare exhaust mass flow during wide-open throttle segments lap-to-lap.
Flag laps consuming significantly more fuel than the median.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class FuelConsumption(Rule):
    @property
    def name(self):
        return "Fuel Consumption (WOT)"

    @property
    def description(self):
        return "Exhaust mass flow during WOT segments should be consistent lap-to-lap"

    @property
    def supports_multi(self) -> bool:
        return True  # Compare cars in multi-file mode

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        fc = config.get("fuel_consumption", {})
        excess_pct = fc.get("excess_pct", 20)

        # Prefer Exhaust Mass Flow (g/s) as the fuel consumption proxy
        fuel_flow = get_channel(df, "Exhaust Mass Flow")
        throttle = get_channel(df, "Throttle Position")
        lap_number = get_channel(df, "Lap Number")

        if fuel_flow is None or throttle is None or lap_number is None:
            return [Result(Status.WARN, "Missing Exhaust Mass Flow, Throttle Position, or Lap Number channels")]

        # Identify WOT segments and sum fuel flow per lap
        wot_mask = (throttle >= 95) & (lap_number > 0)
        wot_fuel = fuel_flow[wot_mask]
        wot_laps = lap_number[wot_mask]

        if len(wot_fuel) == 0:
            return [Result(Status.WARN, "No WOT data available for fuel consumption analysis")]

        # Calculate total fuel flow per lap during WOT (proxy for fuel used)
        lap_fuel_df = pd.DataFrame({"lap": wot_laps.values, "fuel": wot_fuel.values})
        lap_totals = lap_fuel_df.groupby("lap")["fuel"].sum()

        if len(lap_totals) < 2:
            return [Result(Status.WARN, "Insufficient lap data for fuel comparison (need >=2 laps)")]

        median_fuel = float(lap_totals.median())
        threshold = median_fuel * (1 + excess_pct / 100.0)

        outliers = lap_totals[lap_totals > threshold]
        if len(outliers) > 0:
            max_fuel = float(outliers.max())
            details = "\n".join(
                f"  Lap {int(lap)}: {fuel:.1f} (median: {median_fuel:.1f})"
                for lap, fuel in outliers.items()
            )
            results.append(Result(
                Status.WARN,
                f"{len(outliers)} lap(s) exceeded fuel threshold ({threshold:.1f}, median: {median_fuel:.1f})",
                details=details,
                value=round(max_fuel, 1),
                threshold=round(threshold, 1),
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Fuel consumption consistent across {len(lap_totals)} laps (median: {median_fuel:.1f})",
            ))

        return results

