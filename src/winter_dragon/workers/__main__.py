"""Worker entry point for Winter Dragon Bot."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from herogold.log.logging import getLogger
from rq import Worker

from winter_dragon.redis.connection import RedisConnection as RedisConnectionModule
from winter_dragon.redis.queue import TaskQueue


# initialize a logger provided by herogold; it handles configuration
# but ensure we also write an explicit file for worker containers so
# connection errors appear under ./logs in the host.
logger = getLogger(__name__)

# Add a file handler writing to /app/logs/workers.log (host-mounted ./logs)
log_dir = Path(os.getenv("WORKER_LOG_DIR", "/app/logs"))
log_path = log_dir / "workers.log"
file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s > %(name)s [ %(levelname)s ]: %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def main() -> None:
    """Start RQ worker to process jobs from Redis queue."""
    # herogold.logging already configures python's logging system when
    # the first logger is created, so additional configuration here is
    # unnecessary and would interfere with the package's defaults.

    try:
        # Use binary-mode connection required by RQ (pickle data)
        redis_conn = RedisConnectionModule.get_connection(decode_responses=False)
        redis_conn.ping()
        logger.info("Connected to Redis (binary mode)")
    except Exception:
        logger.exception("Failed to connect to Redis")
        sys.exit(1)

    # Determine queues to listen to. Use WORKER_QUEUES env var (comma-separated),
    # otherwise listen to common queues including low_priority where tasks are enqueued.
    queues_env = os.getenv("WORKER_QUEUES")
    if queues_env:
        queues = [q.strip() for q in queues_env.split(",") if q.strip()]
    else:
        queues = [
            TaskQueue.LOW_PRIORITY_QUEUE,
            TaskQueue.DEFAULT_QUEUE,
            TaskQueue.HIGH_PRIORITY_QUEUE,
        ]

    try:
        worker = Worker(queues, connection=redis_conn)
        logger.info(f"Starting RQ worker on queues: {', '.join(queues)}")
        worker.work()
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
        sys.exit(0)
    except Exception:
        logger.exception("Worker error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
