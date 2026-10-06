from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  (registers every table)
from app.applications.router import router as applications_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.documents.router import router as documents_router
from app.scoring.model import Scorer
from app.scoring.router import router as scoring_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model ONCE when the server starts, not on every request.
    app.state.scorer = Scorer.load(settings.model_path)
    yield


app = FastAPI(title="CredScorer", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(scoring_router)


@app.get("/health")
def health():
    scorer = getattr(app.state, "scorer", None)
    return {
        "status": "ok",
        "database": settings.database_url.split("@")[-1],
        "model_version": scorer.version if scorer else None,
    }