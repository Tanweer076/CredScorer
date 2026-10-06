# All-in-one image for the free deploy: the React app and the API in ONE container,
# with uploads processed inside the API (no Redis, no Celery worker).
# Local development keeps using docker-compose.yml and backend/Dockerfile.

# Stage 1: build the React app.
FROM node:24-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: the API, which also serves the built React files.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RUN_TASKS_INLINE=true \
    UPLOAD_DIR=/tmp/uploads

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY ml/artifacts/ /app/ml/artifacts/
COPY --from=frontend /app/dist /app/frontend/dist

RUN useradd --create-home appuser
USER appuser

# Render tells the app which port to use in $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.serve:app --host 0.0.0.0 --port ${PORT:-8000}"]