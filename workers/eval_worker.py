"""Celery app for the LLM Red-Team Platform evaluation workers."""

from celery import Celery

app = Celery("llm_redteam")
app.config_from_object("workers.celeryconfig")
app.autodiscover_tasks(["workers.tasks"])
