"""Load simulated credit bureau records into the database.

Uses the Kaggle application_test rows (never used for training) as a pool of
realistic credit histories. Run once from the backend folder, after prepare_data.py:
    python seed_bureau.py
"""
import math

import pandas as pd
from sqlalchemy import delete

import app.models  # noqa: F401
from app.core.db import SessionLocal
from app.scoring.models import BureauProfile

SOURCE = "../ml/data/processed/test_features.parquet"
BUREAU_COLUMNS = [
    "ext_source_1", "ext_source_2", "ext_source_3", "ext_source_mean",
    "late_payment_ratio", "avg_days_late", "max_days_late", "underpaid_ratio", "n_installments",
    "active_loans", "total_debt", "total_overdue", "credit_utilisation",
    "prev_applications", "prev_refused", "prev_refused_ratio",
]

df = pd.read_parquet(SOURCE, columns=BUREAU_COLUMNS)


def clean(value):
    value = float(value)
    return None if math.isnan(value) else round(value, 6)


rows = [{"source_id": int(source_id), "data": {k: clean(v) for k, v in record.items()}}
        for source_id, record in zip(df.index, df.to_dict(orient="records"))]

with SessionLocal() as db:
    db.execute(delete(BureauProfile))
    for start in range(0, len(rows), 5000):
        db.execute(BureauProfile.__table__.insert(), rows[start:start + 5000])
    db.commit()
print(f"Seeded {len(rows):,} bureau profiles.")