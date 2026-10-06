from fastapi import FastAPI

import app.models  # noqa: F401  (registers every table)
from app.auth.router import router as auth_router
from app.core.config import settings

app = FastAPI(title="CredScorer")
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok", "database": settings.database_url.split("@")[-1]}