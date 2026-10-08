"""The decision rules. Pure Python, no database: easy to read, test and explain."""

DEFAULT_THRESHOLDS = {
    "approve_min_score": 620,  # replaced by your ml/artifacts/thresholds.json or the admin's settings
    "reject_max_score": 450,
    "max_emi_share": 0.5,  # never auto-approve if the EMI takes more than half the monthly income
}


def decide(score: int, emi_share: float | None, thresholds: dict) -> tuple[str, list[str]]:
    """Return (outcome, reasons). Outcome is APPROVED, REJECTED or MANUAL_REVIEW.

    emi_share is None when there is no declared income, so affordability can't be checked.
    """
    approve_min, reject_max = thresholds["approve_min_score"], thresholds["reject_max_score"]
    max_emi_share = thresholds["max_emi_share"]

    if score < reject_max:
        return "REJECTED", [f"Score {score} is below the minimum of {reject_max}."]

    reasons = []
    if emi_share is None:
        reasons.append("No monthly income was declared, so affordability can't be checked.")
    elif emi_share > max_emi_share:
        # Policy rule on top of the model: affordability is checked even when the score is high.
        reasons.append(f"The EMI would take {emi_share:.0%} of monthly income (limit {max_emi_share:.0%}).")
    if score < approve_min:
        reasons.append(f"Score {score} is between {reject_max} and {approve_min}: needs a person to review.")
    if reasons:
        return "MANUAL_REVIEW", reasons
    return "APPROVED", [f"Score {score} is at or above {approve_min}, documents verified and EMI affordable."]