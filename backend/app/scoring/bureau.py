"""Simulated credit bureau.

Real lenders call a bureau (CIBIL, Experian...) with the applicant's ID. In this demo we
pick one of the seeded Kaggle profiles deterministically from the applicant's email, so the
same person always gets the same history. About 1 in 10 people get no record at all,
to show how thin-file applicants are scored.
"""
import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.scoring.models import BureauProfile

THIN_FILE_ONE_IN = 10


def get_bureau_record(db: Session, user: User) -> dict | None:
    count = db.scalar(select(func.count()).select_from(BureauProfile)) or 0
    if count == 0:
        return None
    h = int(hashlib.sha256(user.email.lower().encode()).hexdigest(), 16)
    if h % THIN_FILE_ONE_IN == 0:
        return None
    profile = db.scalars(select(BureauProfile).order_by(BureauProfile.id).offset(h % count).limit(1)).first()
    return profile.data if profile else None