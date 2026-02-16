"""Celery application for inference workers."""

from celery import Celery
from app.config import settings

celery = Celery(
    "inference",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
