"""Turn an application (+ bureau record) into the exact feature row the model was trained on.

The formulas mirror ml/features.py. If you change one, change the other.
"""
import math
from datetime import date

from app.applications.models import Application
from app.core.config import settings

# API values -> the category labels used in the Kaggle data (and in the model).
EDUCATION = {
    "lower_secondary": "Lower secondary",
    "secondary": "Secondary / secondary special",
    "incomplete_higher": "Incomplete higher",
    "higher": "Higher education",
    "academic_degree": "Academic degree",
}
INCOME_TYPE = {
    "salaried": "Working",
    "self_employed": "Commercial associate",
    "unemployed": "Unemployed",
    "student": "Student",
    "retired": "Pensioner",
}
FAMILY_STATUS = {
    "single": "Single / not married",
    "married": "Married",
    "civil_marriage": "Civil marriage",
    "separated": "Separated",
    "widow": "Widow",
}
HOUSING = {
    "owned": "House / apartment",
    "rented": "Rented apartment",
    "with_parents": "With parents",
    "municipal": "Municipal apartment",
    "office": "Office apartment",
    "co_op": "Co-op apartment",
}
REQUIRED_FIELDS = ["date_of_birth", "children", "family_members", "owns_car", "owns_home",
                   "education", "family_status", "housing_type"]


class MissingApplicationData(ValueError):
    pass


def monthly_emi(amount: float, term_months: int, annual_rate: float) -> float:
    """Standard loan EMI formula."""
    r = annual_rate / 12
    if r == 0:
        return amount / term_months
    return amount * r / (1 - (1 + r) ** -term_months)


def _age_years(dob: date, today: date | None = None) -> float:
    today = today or date.today()
    return (today - dob).days / 365.25


def build_feature_row(application: Application, bureau: dict | None, overrides: dict | None = None) -> dict:
    """Return {feature_name: value}. Missing values are None (the model treats them as unknown).

    `overrides` lets the what-if endpoint change inputs without touching the database.
    """
    missing = [f for f in REQUIRED_FIELDS if getattr(application, f) is None]
    if missing:
        raise MissingApplicationData(f"Application is missing fields needed for scoring: {', '.join(missing)}")

    o = overrides or {}
    income = float(o.get("monthly_income", application.declared_monthly_income))
    amount = float(o.get("amount_requested", application.amount_requested))
    term = int(o.get("term_months", application.term_months))
    employment_years = o.get("employment_years", application.employment_years)
    emi = monthly_emi(amount, term, settings.annual_interest_rate)
    not_employed = application.employment_type in ("unemployed", "retired")

    # In the Kaggle data, income and annuity are on the same time scale, so we feed the
    # monthly income and the monthly EMI. Ratios are computed with the SAME formulas as training.
    row = {
        "annual_income": income,
        "credit_amount": amount,
        "annuity": emi,
        "term_months": amount / emi,
        "credit_to_income": amount / income if income > 0 else None,
        "payment_to_income": emi / (income / 12) if income > 0 else None,
        "age_years": _age_years(application.date_of_birth),
        "employment_years": None if not_employed else float(employment_years),
        "not_employed": int(not_employed),
        "children": application.children,
        "family_members": application.family_members,
        "owns_car": int(application.owns_car),
        "owns_realty": int(application.owns_home),
        "education": EDUCATION[application.education],
        "income_type": INCOME_TYPE[application.employment_type],
        "family_status": FAMILY_STATUS[application.family_status],
        "housing_type": HOUSING[application.housing_type],
    }
    bureau = bureau or {}  # no bureau record = thin-file applicant: all history features unknown
    for key in ["ext_source_1", "ext_source_2", "ext_source_3", "ext_source_mean",
                "late_payment_ratio", "avg_days_late", "max_days_late", "underpaid_ratio", "n_installments",
                "active_loans", "total_debt", "total_overdue", "credit_utilisation",
                "prev_applications", "prev_refused", "prev_refused_ratio"]:
        row[key] = bureau.get(key)
    total_debt = row["total_debt"]
    row["debt_to_income"] = total_debt / income if total_debt is not None and income > 0 else None
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}