from core.celery_app import celery_app


@celery_app.task
def process_test_job(job_id: str):
    print(f"Worker started job: {job_id}")

    # Simulate heavy work
    total = 0

    for i in range(100_000_000):
        total += i

    print(f"Worker finished job: {job_id}")

    return {
        "job_id": job_id,
        "result": total,
    }