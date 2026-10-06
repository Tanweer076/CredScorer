from celery import Celery

from app.core.config import settings

celery = Celery("credscorer", broker=settings.redis_url, backend=settings.redis_url,
                include=["app.documents.tasks"])
celery.conf.update(
    task_acks_late=True,  # if the worker crashes mid-task, the task is redelivered
    worker_prefetch_multiplier=1,  # LLM calls are slow: take one task at a time
    broker_connection_retry_on_startup=True,
)