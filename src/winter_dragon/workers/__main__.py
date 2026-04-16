"""Worker entry point for Winter Dragon Bot."""

import sys

# use centralized logging from the herogold package instead of the
# stdlib 'logging' module directly
from herogold.log.logging import getLogger
from rq import Worker

from . import RedisConnection


# initialize a logger provided by herogold; it handles configuration
# (handlers, formatting, levels) globally so we don't call basicConfig.
logger = getLogger(__name__)


def main() -> None:
    """Start RQ worker to process jobs from Redis queue."""
    # herogold.logging already configures python's logging system when
    # the first logger is created, so additional configuration here is
    # unnecessary and would interfere with the package's defaults.

    try:
        redis_conn = RedisConnection.get_redis_connection()
        redis_conn.ping()
        logger.info("Connected to Redis")
    except Exception:
        logger.exception("Failed to connect to Redis")
        sys.exit(1)

    try:
        worker = Worker(["default"], connection=redis_conn)
        logger.info("Starting RQ worker on queue: default")
        worker.work()
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
        sys.exit(0)
    except Exception:
        logger.exception("Worker error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
