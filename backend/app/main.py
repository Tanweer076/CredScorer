from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="CredScorer")


@app.get("/health")
def health():
    return {"status": "ok", "database": settings.database_url.split("@")[-1]}