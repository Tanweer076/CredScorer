from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.auth.models import User


def get_application_for_user(db: Session, application_id: int, user: User) -> Application:
    """Return the application if this user may see it.

    Applicants only see their own. For anyone else's we return 404, not 403,
    so applicants can't discover which application ids exist.
    """
    application = db.get(Application, application_id)
    if application is None or (user.role == "applicant" and application.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


def snapshot(application: Application) -> dict:
    """JSON-safe copy of the editable fields, for the audit log."""
    return {
        "amount_requested": str(application.amount_requested),
        "term_months": application.term_months,
        "purpose": application.purpose,
        "declared_monthly_income": str(application.declared_monthly_income),
        "employment_type": application.employment_type,
        "employment_years": application.employment_years,
        "status": application.status,
    }