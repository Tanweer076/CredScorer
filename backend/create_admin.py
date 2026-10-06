"""Create the first admin account. Run from the backend folder: python create_admin.py"""
from getpass import getpass

from sqlalchemy import select

import app.models  # noqa: F401
from app.auth.models import User
from app.auth.security import hash_password
from app.core.db import SessionLocal

email = input("Admin email: ").strip().lower()
full_name = input("Full name: ").strip()
password = getpass("Password (min 8 chars, hidden while typing): ")
if len(password) < 8:
    raise SystemExit("Password too short.")

with SessionLocal() as db:
    if db.scalar(select(User).where(User.email == email)):
        raise SystemExit("That email already exists.")
    db.add(User(email=email, full_name=full_name, password_hash=hash_password(password), role="admin"))
    db.commit()
print(f"Admin {email} created.")