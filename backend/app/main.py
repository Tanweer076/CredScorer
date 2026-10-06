from fastapi import FastAPI

import app.models  # noqa: F401  (registers every table)
from app.applications.router import router as applications_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.documents.router import router as documents_router

app = FastAPI(title="CredScorer")
app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(documents_router)


@app.get("/health")
def health():
    return {"status": "ok", "database": settings.database_url.split("@")[-1]}