"""Turn SHAP values into plain-English reasons and simple recommendations."""

# feature -> (label shown to the user, how to format its value)
LABELS = {
    "annual_income": ("Monthly income", "money"),
    "credit_amount": ("Loan amount", "money"),
    "annuity": ("Monthly repayment (EMI)", "money"),
    "term_months": ("Loan amount compared with monthly repayment", "times"),
    "credit_to_income": ("Loan size compared with monthly income", "times"),
    "payment_to_income": ("Share of monthly income going to the EMI", "emi_share"),
    "age_years": ("Age", "years"),
    "employment_years": ("Years in current employment", "years"),
    "not_employed": ("Not currently employed", "yesno"),
    "children": ("Number of children", "num"),
    "family_members": ("Household size", "num"),
    "owns_car": ("Owns a car", "yesno"),
    "owns_realty": ("Owns a home", "yesno"),
    "education": ("Education", "text"),
    "income_type": ("Type of income", "text"),
    "family_status": ("Family status", "text"),
    "housing_type": ("Housing", "text"),
    "ext_source_1": ("Credit bureau score 1", "score"),
    "ext_source_2": ("Credit bureau score 2", "score"),
    "ext_source_3": ("Credit bureau score 3", "score"),
    "ext_source_mean": ("Average credit bureau score", "score"),
    "late_payment_ratio": ("Share of past instalments paid late", "pct"),
    "avg_days_late": ("Average days late on past payments", "num"),
    "max_days_late": ("Longest delay on a past payment (days)", "num"),
    "underpaid_ratio": ("Share of past instalments underpaid", "pct"),
    "n_installments": ("Number of past instalments", "num"),
    "active_loans": ("Active loans with other lenders", "num"),
    "total_debt": ("Total outstanding debt", "money"),
    "total_overdue": ("Total overdue amount", "money"),
    "debt_to_income": ("Outstanding debt compared with monthly income", "times"),
    "credit_utilisation": ("Credit card utilisation", "pct"),
    "prev_applications": ("Previous loan applications", "num"),
    "prev_refused": ("Previously refused applications", "num"),
    "prev_refused_ratio": ("Share of previous applications refused", "pct"),
}

# feature -> tip shown when that feature RAISES the applicant's risk
TIPS = {
    "payment_to_income": "Choose a longer term or a smaller amount to lower your monthly repayment.",
    "annuity": "Choose a longer term or a smaller amount to lower your monthly repayment.",
    "term_months": "Try a different loan length; it changes both the EMI and the total cost.",
    "credit_to_income": "Consider applying for a smaller loan amount.",
    "credit_amount": "Consider applying for a smaller loan amount.",
    "credit_utilisation": "Keep credit card usage below 30% of your limit.",
    "late_payment_ratio": "Pay every instalment on time; setting up auto-pay helps.",
    "avg_days_late": "Pay every instalment on time; setting up auto-pay helps.",
    "max_days_late": "Pay every instalment on time; setting up auto-pay helps.",
    "underpaid_ratio": "Always pay the full instalment amount.",
    "total_overdue": "Clear any overdue amounts before applying.",
    "active_loans": "Close or consolidate small active loans before applying.",
    "total_debt": "Pay down existing debt before taking a new loan.",
    "debt_to_income": "Pay down existing debt before taking a new loan.",
    "prev_refused": "Avoid making many loan applications in a short time.",
    "prev_refused_ratio": "Avoid making many loan applications in a short time.",
    "ext_source_1": "Build your credit history by keeping existing accounts in good standing.",
    "ext_source_2": "Build your credit history by keeping existing accounts in good standing.",
    "ext_source_3": "Build your credit history by keeping existing accounts in good standing.",
    "ext_source_mean": "Build your credit history by keeping existing accounts in good standing.",
    "employment_years": "A longer time in stable employment will improve your score.",
    "not_employed": "A regular source of income will improve your score.",
}


def _format(value, kind: str) -> str:
    if value is None:
        return "no record"
    if kind == "money":
        return f"₹{value:,.0f}"
    if kind == "pct":
        return f"{value:.0%}"
    if kind == "emi_share":
        return f"{value / 12:.0%}"  # the feature is EMI / (income / 12); see features.py
    if kind == "times":
        return f"{value:.1f}x"
    if kind == "years":
        return f"{value:.1f} years"
    if kind == "yesno":
        return "yes" if value else "no"
    if kind == "score":
        return f"{value:.2f} (0 to 1)"
    if kind == "num":
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
    return str(value)


def top_reasons(shap_values: dict, row: dict, n: int = 3) -> list[dict]:
    """The n factors that moved this applicant's risk the most, in either direction."""
    ranked = sorted(shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)[:n]
    reasons = []
    for feature, impact in ranked:
        label, kind = LABELS.get(feature, (feature, "text"))
        direction = "raises" if impact > 0 else "lowers"
        reasons.append({
            "feature": feature,
            "impact": round(impact, 4),
            "direction": "increases_risk" if impact > 0 else "decreases_risk",
            "text": f"{label}: {_format(row.get(feature), kind)}. This {direction} your risk.",
        })
    return reasons


def score_band(score: int) -> str:
    if score >= 650:
        return "Excellent"
    if score >= 600:
        return "Good"
    if score >= 550:
        return "Fair"
    if score >= 500:
        return "Below average"
    return "Poor"


def recommendations(shap_values: dict, score: int, n: int = 3) -> list[str]:
    risk_raisers = sorted((kv for kv in shap_values.items() if kv[1] > 0), key=lambda kv: kv[1], reverse=True)
    tips: list[str] = []
    for feature, _ in risk_raisers:
        tip = TIPS.get(feature)
        if tip and tip not in tips:
            tips.append(tip)
        if len(tips) == n:
            break
    if score < 450:
        tips.append("Consider applying with a co-applicant or for a smaller amount.")
    return tips