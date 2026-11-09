from app.workers.celery_app import celery_app

@celery_app.task(name="health_check_task")
def health_check_task():
    return {"status": "success", "message": "Celery worker is operational."}
