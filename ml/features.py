"""Feature engineering for CredScorer.

One place that turns raw Home Credit tables into model features, so the
notebook, train.py and (later) the API all build features the same way.
"""
from pathlib import Path

import numpy as np
import pandas as pd

# Fixed category lists. The API must use exactly the same ones at serving time,
# so they live in code, not learned from the data. Unknown values become NaN.
CATEGORIES = {
    "education": ["Secondary / secondary special", "Higher education", "Incomplete higher",
                  "Lower secondary", "Academic degree"],
    "income_type": ["Working", "Commercial associate", "Pensioner", "State servant",
                    "Unemployed", "Student", "Businessman", "Maternity leave"],
    "family_status": ["Married", "Single / not married", "Civil marriage", "Separated",
                      "Widow", "Unknown"],
    "housing_type": ["House / apartment", "With parents", "Municipal apartment",
                     "Rented apartment", "Office apartment", "Co-op apartment"],
}

# What a real applicant can give us on the form (or we derive from it).
FORM_FEATURES = [
    "annual_income", "credit_amount", "annuity", "term_months",
    "credit_to_income", "payment_to_income", "age_years", "employment_years",
    "not_employed", "children", "family_members", "owns_car", "owns_realty",
    *CATEGORIES,
]
# What a credit bureau would tell us. Missing for thin-file applicants (NaN is fine for XGBoost).
BUREAU_FEATURES = [
    "ext_source_1", "ext_source_2", "ext_source_3", "ext_source_mean",
    "late_payment_ratio", "avg_days_late", "max_days_late", "underpaid_ratio", "n_installments",
    "active_loans", "total_debt", "total_overdue", "debt_to_income",
    "credit_utilisation", "prev_applications", "prev_refused", "prev_refused_ratio",
]
FEATURES = FORM_FEATURES + BUREAU_FEATURES

APP_COLUMNS = [
    "SK_ID_CURR", "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "DAYS_BIRTH", "DAYS_EMPLOYED",
    "CNT_CHILDREN", "CNT_FAM_MEMBERS", "FLAG_OWN_CAR", "FLAG_OWN_REALTY",
    "NAME_EDUCATION_TYPE", "NAME_INCOME_TYPE", "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE",
    "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
]


def application_features(app: pd.DataFrame) -> pd.DataFrame:
    """Per-applicant features from application_train/test.csv."""
    out = pd.DataFrame(index=app["SK_ID_CURR"].values)
    out.index.name = "SK_ID_CURR"
    v = lambda col: app[col].to_numpy()  # noqa: E731

    days_employed = np.where(v("DAYS_EMPLOYED") == 365243, np.nan, v("DAYS_EMPLOYED"))  # 365243 = not employed
    out["annual_income"] = v("AMT_INCOME_TOTAL")
    out["credit_amount"] = v("AMT_CREDIT")
    out["annuity"] = v("AMT_ANNUITY")
    out["term_months"] = v("AMT_CREDIT") / v("AMT_ANNUITY")
    out["credit_to_income"] = v("AMT_CREDIT") / v("AMT_INCOME_TOTAL")
    out["payment_to_income"] = v("AMT_ANNUITY") / (v("AMT_INCOME_TOTAL") / 12)
    out["age_years"] = -v("DAYS_BIRTH") / 365.25
    out["employment_years"] = -days_employed / 365.25
    out["not_employed"] = np.isnan(days_employed).astype(int)
    out["children"] = v("CNT_CHILDREN")
    out["family_members"] = v("CNT_FAM_MEMBERS")
    out["owns_car"] = (v("FLAG_OWN_CAR") == "Y").astype(int)
    out["owns_realty"] = (v("FLAG_OWN_REALTY") == "Y").astype(int)
    for name, col in [("education", "NAME_EDUCATION_TYPE"), ("income_type", "NAME_INCOME_TYPE"),
                      ("family_status", "NAME_FAMILY_STATUS"), ("housing_type", "NAME_HOUSING_TYPE")]:
        out[name] = pd.Categorical(v(col), categories=CATEGORIES[name])
    ext = app[["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]].to_numpy()
    out["ext_source_1"], out["ext_source_2"], out["ext_source_3"] = ext[:, 0], ext[:, 1], ext[:, 2]
    out["ext_source_mean"] = np.nanmean(np.where(np.isnan(ext).all(axis=1, keepdims=True), 0, ext), axis=1)
    out.loc[np.isnan(ext).all(axis=1), "ext_source_mean"] = np.nan
    return out


def installment_features(raw_dir: Path) -> pd.DataFrame:
    """Payment history: how often and how late past instalments were paid."""
    ins = pd.read_csv(raw_dir / "installments_payments.csv", dtype="float32",
                      usecols=["SK_ID_CURR", "DAYS_INSTALMENT", "DAYS_ENTRY_PAYMENT",
                               "AMT_INSTALMENT", "AMT_PAYMENT"])
    days_late = (ins["DAYS_ENTRY_PAYMENT"] - ins["DAYS_INSTALMENT"]).clip(lower=0)
    ins = ins.assign(days_late=days_late, late=(days_late > 0).astype("float32"),
                     underpaid=(ins["AMT_PAYMENT"] < ins["AMT_INSTALMENT"] - 1).astype("float32"))
    g = ins.groupby(ins["SK_ID_CURR"].astype("int64"))
    out = pd.DataFrame({
        "late_payment_ratio": g["late"].mean(),
        "avg_days_late": g["days_late"].mean(),
        "max_days_late": g["days_late"].max(),
        "underpaid_ratio": g["underpaid"].mean(),
        "n_installments": g.size(),
    })
    out.index.name = "SK_ID_CURR"
    return out


def bureau_features(raw_dir: Path) -> pd.DataFrame:
    """Loans at other lenders."""
    b = pd.read_csv(raw_dir / "bureau.csv",
                    usecols=["SK_ID_CURR", "CREDIT_ACTIVE", "AMT_CREDIT_SUM_DEBT", "AMT_CREDIT_SUM_OVERDUE"])
    b["active"] = (b["CREDIT_ACTIVE"] == "Active").astype(int)
    g = b.groupby("SK_ID_CURR")
    return pd.DataFrame({
        "active_loans": g["active"].sum(),
        "total_debt": g["AMT_CREDIT_SUM_DEBT"].sum(),
        "total_overdue": g["AMT_CREDIT_SUM_OVERDUE"].sum(),
    })


def card_features(raw_dir: Path) -> pd.DataFrame:
    """Average credit card utilisation (balance / limit)."""
    cc = pd.read_csv(raw_dir / "credit_card_balance.csv", dtype="float32",
                     usecols=["SK_ID_CURR", "AMT_BALANCE", "AMT_CREDIT_LIMIT_ACTUAL"])
    limit = cc["AMT_CREDIT_LIMIT_ACTUAL"].where(cc["AMT_CREDIT_LIMIT_ACTUAL"] > 0)
    cc["util"] = (cc["AMT_BALANCE"] / limit).clip(0, 2)
    out = cc.groupby(cc["SK_ID_CURR"].astype("int64"))["util"].mean().to_frame("credit_utilisation")
    out.index.name = "SK_ID_CURR"
    return out


def previous_application_features(raw_dir: Path) -> pd.DataFrame:
    """Earlier applications at Home Credit and how many were refused."""
    p = pd.read_csv(raw_dir / "previous_application.csv", usecols=["SK_ID_CURR", "NAME_CONTRACT_STATUS"])
    p["refused"] = (p["NAME_CONTRACT_STATUS"] == "Refused").astype(int)
    g = p.groupby("SK_ID_CURR")
    out = pd.DataFrame({"prev_applications": g.size(), "prev_refused": g["refused"].sum()})
    out["prev_refused_ratio"] = out["prev_refused"] / out["prev_applications"]
    return out


def build_features(raw_dir: Path, application_file: str) -> pd.DataFrame:
    """Full feature table for application_train.csv or application_test.csv.

    Includes TARGET when the file has it.
    """
    raw_dir = Path(raw_dir)
    header = pd.read_csv(raw_dir / application_file, nrows=0).columns
    usecols = APP_COLUMNS + (["TARGET"] if "TARGET" in header else [])
    app = pd.read_csv(raw_dir / application_file, usecols=usecols)

    X = application_features(app)
    for extra in (installment_features(raw_dir), bureau_features(raw_dir),
                  card_features(raw_dir), previous_application_features(raw_dir)):
        X = X.join(extra, how="left")
    X["debt_to_income"] = X["total_debt"] / X["annual_income"]
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X[FEATURES]
    if "TARGET" in app:
        X["TARGET"] = app["TARGET"].to_numpy()
    return X