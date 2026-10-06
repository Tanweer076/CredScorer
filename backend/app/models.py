# Imports every model so Alembic can see all tables.
from app.applications.models import Application  # noqa: F401
from app.auth.models import User  # noqa: F401
from app.decisions.models import AuditLog, Decision, Setting  # noqa: F401
from app.documents.models import Document, ExtractedData  # noqa: F401
from app.scoring.models import CreditScore  # noqa: F401