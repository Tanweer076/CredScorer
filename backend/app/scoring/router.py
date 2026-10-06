from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.service import get_application_for_user
from app.applications.status import Status
from app.auth.models import User
from app.auth.security import get_current_user
from app.core.db import get_db
from app.scoring.features import MissingApplicationData
from app.scoring.model import Scorer
from app.scoring.models import CreditScore
from app.scoring.reasons import recommendations, score_band, top_reasons
from app.scoring.schemas import ScenarioOut, ScoreOut, WhatIfIn, WhatIfOut
from app.scoring.service import features_for, score_and_save

router = APIRouter(prefix="/applications/{application_id}", tags=["scoring"])

SCORABLE = {Status.SUBMITTED, Status.DOCS_VERIFIED, Status.SCORED}


def get_scorer(request: Request) -> Scorer:
    scorer = getattr(request.app.state, "scorer", None)
    if scorer is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Scoring model is not loaded. Train it and set MODEL_PATH.")
    return scorer


def _features_or_422(db: Session, application: Application, overrides: dict | None = None) -> dict:
    try:
        return features_for(db, application, overrides)
    except MissingApplicationData as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.post("/score", response_model=ScoreOut)
def score_application(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scorer: Scorer = Depends(get_scorer),
):
    application = get_application_for_user(db, application_id, user)
    if application.status not in SCORABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Application is {application.status}; it can no longer be scored")
    try:
        credit_score, result = score_and_save(db, application, scorer, actor_id=user.id)
    except MissingApplicationData as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    db.commit()
    db.refresh(credit_score)
    return ScoreOut(application_id=application.id, pd=result["pd"], score=result["score"],
                    band=score_band(result["score"]), model_version=scorer.version,
                    reasons=credit_score.shap_reasons[:3],
                    recommendations=recommendations(result["shap"], result["score"]),
                    status=application.status, created_at=credit_score.created_at)


@router.get("/score", response_model=ScoreOut)
def latest_score(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    application = get_application_for_user(db, application_id, user)
    latest = db.scalars(select(CreditScore).where(CreditScore.application_id == application.id)
                        .order_by(CreditScore.id.desc()).limit(1)).first()
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This application has not been scored yet")
    shap_values = {r["feature"]: r["impact"] for r in latest.shap_reasons}
    return ScoreOut(application_id=application.id, pd=latest.pd, score=latest.score, band=score_band(latest.score),
                    model_version=latest.model_version, reasons=latest.shap_reasons[:3],
                    recommendations=recommendations(shap_values, latest.score),
                    status=application.status, created_at=latest.created_at)


def _scenario(scorer: Scorer, row: dict) -> ScenarioOut:
    result = scorer.score(row)
    return ScenarioOut(pd=result["pd"], score=result["score"], band=score_band(result["score"]),
                       monthly_emi=round(row["annuity"], 2), reasons=top_reasons(result["shap"], row))


@router.post("/what-if", response_model=WhatIfOut)
def what_if(
    application_id: int,
    changes: WhatIfIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scorer: Scorer = Depends(get_scorer),
):
    """Re-score with changed inputs. Nothing is saved."""
    application = get_application_for_user(db, application_id, user)
    overrides = changes.model_dump(exclude_none=True)
    if not overrides:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Send at least one value to change")
    current = _scenario(scorer, _features_or_422(db, application))
    scenario = _scenario(scorer, _features_or_422(db, application, overrides))
    return WhatIfOut(application_id=application.id, changes=overrides, current=current, scenario=scenario,
                     score_change=scenario.score - current.score)