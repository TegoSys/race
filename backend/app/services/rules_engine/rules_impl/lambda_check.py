"""Rule 4: Exhaust Lambda Check during WOT.

During Wide Open Throttle, Exhaust Lambda Bank 1/2 should be 0.88-0.89.
WARN if outside 0.85-0.92, FAIL if outside 0.80-0.95.
"""
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class LambdaCheck(Rule):
    @property
    def name(self):
        return "Exhaust Lambda (WOT)"

    @property
    def description(self):
        return "Lambda banks should be 0.88-0.89 during wide open throttle"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []
        lc = config.get("lambda_check", {})
        target_low = lc.get("target_low", 0.88)
        target_high = lc.get("target_high", 0.89)
        warn_low = lc.get("warn_low", 0.85)
        warn_high = lc.get("warn_high", 0.92)
        fail_low = lc.get("fail_low", 0.80)
        fail_high = lc.get("fail_high", 0.95)

        lambda1 = get_channel(df, "Exhaust Lambda Bank 1 Normalised")
        lambda2 = get_channel(df, "Exhaust Lambda Bank 2 Normalised")
        throttle = get_channel(df, "Throttle Position")

        if lambda1 is None and lambda2 is None:
            return [Result(Status.WARN, "Missing Exhaust Lambda channels")]
        if throttle is None:
            return [Result(Status.WARN, "Missing Throttle Position channel")]

        wot_mask = throttle >= 95  # WOT threshold

        for label, series in [("Bank 1", lambda1), ("Bank 2", lambda2)]:
            if series is None:
                continue
            wot_values = series[wot_mask]
            if len(wot_values) == 0:
                continue

            mean_val = float(wot_values.mean())
            min_val = float(wot_values.min())
            max_val = float(wot_values.max())

            if min_val < fail_low or max_val > fail_high:
                out_val = min_val if min_val < fail_low else max_val
                out_thresh = fail_low if min_val < fail_low else fail_high
                results.append(Result(
                    Status.FAIL,
                    f"{label} lambda out of safe range during WOT: range [{min_val:.3f}, {max_val:.3f}], mean {mean_val:.3f}",
                    details=f"Safe range: [{fail_low}-{fail_high}], Target: [{target_low}-{target_high}]",
                    value=out_val,
                    threshold=out_thresh,
                ))
            elif min_val < warn_low or max_val > warn_high:
                out_val = min_val if min_val < warn_low else max_val
                out_thresh = warn_low if min_val < warn_low else warn_high
                results.append(Result(
                    Status.WARN,
                    f"{label} lambda outside warning range during WOT: range [{min_val:.3f}, {max_val:.3f}], mean {mean_val:.3f}",
                    details=f"Warning range: [{warn_low}-{warn_high}], Target: [{target_low}-{target_high}]",
                    value=out_val,
                    threshold=out_thresh,
                ))
            else:
                results.append(Result(
                    Status.PASS,
                    f"{label} lambda within target during WOT: range [{min_val:.3f}, {max_val:.3f}], mean {mean_val:.3f}",
                ))

        if not results:
            results.append(Result(Status.PASS, "Lambda values within acceptable range during WOT"))

        return results
