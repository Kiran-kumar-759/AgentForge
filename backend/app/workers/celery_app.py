from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "orca_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.health", "app.workers.tasks.ingestion", "app.workers.tasks.execution", "app.workers.tasks.report", "app.workers.tasks.vessel_ingestion"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
