# One image for both the API and the Celery worker.
# Built from the project root (see docker-compose.yml), so it can also copy ml/artifacts.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

# Libraries first: Docker reuses this slow step until requirements.txt changes.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# The code, and the trained model in the same layout as on your PC (../ml/artifacts).
COPY backend/ .
COPY ml/artifacts/ /app/ml/artifacts/

# Don't run as root. The uploads folder is the only place the app writes files.
RUN useradd --create-home appuser && mkdir -p /data/uploads && chown appuser /data/uploads
USER appuser

EXPOSE 8000
# Bring the database up to date, then start the API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]