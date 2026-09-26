from redis import Redis
from rq import Queue, Worker

from app.core.config import get_settings


def queue() -> Queue:
    return Queue("documents", connection=Redis.from_url(get_settings().redis_url), default_timeout=600)


def enqueue_document(document_id: str):
    return queue().enqueue("app.services.document_processor.process_document", document_id, job_timeout=600, result_ttl=3600, failure_ttl=86400)


if __name__ == "__main__":
    Worker([queue()], connection=Redis.from_url(get_settings().redis_url)).work()
