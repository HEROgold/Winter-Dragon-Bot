"""RQ (Redis Queue) configuration and task queue management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from herogold.log import LoggerMixin
from herogold.log.logging import getLogger
from rq import Queue
from rq.job import Job

from winter_dragon.redis.connection import RedisConnection


if TYPE_CHECKING:
    from collections.abc import Callable

logger = getLogger("TaskQueue")


class TaskQueue(LoggerMixin):
    """RQ task queue manager for distributed job processing."""

    # Queue names
    HIGH_PRIORITY_QUEUE = "high_priority"
    DEFAULT_QUEUE = "default"
    LOW_PRIORITY_QUEUE = "low_priority"

    _queues: ClassVar[dict[str, Queue]] = {}

    @classmethod
    def get_queue(cls, name: str = DEFAULT_QUEUE, *, is_async: bool = False) -> Queue:
        """Get or create a task queue.

        Args:
            name: Queue name
            is_async: Whether to use async connection

        Returns:
            Queue: RQ Queue instance

        """
        if name not in cls._queues:
            # RQ requires decode_responses=False to handle pickled data
            redis_conn = RedisConnection.get_connection(decode_responses=False)
            cls._queues[name] = Queue(name, connection=redis_conn, is_async=is_async)
            logger.info(f"Created queue: {name} (async={is_async})")

        return cls._queues[name]

    @classmethod
    def enqueue_task(  # noqa: PLR0913
        cls,
        func: Callable,
        *args: Any,  # noqa: ANN401
        queue_name: str = DEFAULT_QUEUE,
        job_timeout: int | None = None,
        result_ttl: int = 500,
        failure_ttl: int = 86400,
        job_id: str | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> Job:
        """Enqueue a task for processing by workers.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            queue_name: Name of the queue to use
            job_timeout: Maximum execution time in seconds (None = no limit)
            result_ttl: Time to keep successful job results (seconds)
            failure_ttl: Time to keep failed job info (seconds)
            job_id: Optional custom job ID
            **kwargs: Keyword arguments for the function

        Returns:
            Job: RQ Job instance

        """
        queue = cls.get_queue(queue_name, is_async=True)

        job = queue.enqueue(
            func,
            *args,
            job_timeout=job_timeout,
            result_ttl=result_ttl,
            failure_ttl=failure_ttl,
            job_id=job_id,
            **kwargs,
        )

        logger.info(
            f"Enqueued task {func.__name__} to queue '{queue_name}' with job_id={job.id}",  # ty:ignore[unresolved-attribute]
            extra={
                "job_id": job.id,
                "queue": queue_name,
                "function": func.__name__,  # ty:ignore[unresolved-attribute]
                "timeout": job_timeout,
            },
        )

        return job

    @classmethod
    def get_job(cls, job_id: str) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job | None: Job instance or None if not found

        """
        try:
            # RQ requires decode_responses=False to handle pickled data
            redis_conn = RedisConnection.get_connection(decode_responses=False)
            return Job.fetch(job_id, connection=redis_conn)
        except Exception:
            logger.exception(f"Failed to fetch job {job_id}")
            return None

    @classmethod
    def get_queue_length(cls, queue_name: str = DEFAULT_QUEUE) -> int:
        """Get number of jobs in queue.

        Args:
            queue_name: Queue name

        Returns:
            int: Number of jobs in queue

        """
        # Use binary connection to match queue creation
        redis_conn = RedisConnection.get_connection(decode_responses=False)
        # RQ stores queues as lists with key "rq:queue:{name}"
        key = f"rq:queue:{queue_name}"
        return redis_conn.llen(key)

    @classmethod
    def get_queue_stats(cls, queue_name: str = DEFAULT_QUEUE) -> dict[str, int]:
        """Get queue statistics.

        Args:
            queue_name: Queue name

        Returns:
            dict: Queue statistics

        """
        queue = cls.get_queue(queue_name)

        return {
            "queued": len(queue),
            "started": queue.started_job_registry.count,
            "finished": queue.finished_job_registry.count,
            "failed": queue.failed_job_registry.count,
            "deferred": queue.deferred_job_registry.count,
            "scheduled": queue.scheduled_job_registry.count,
        }

    @classmethod
    def clear_queue(cls, queue_name: str = DEFAULT_QUEUE) -> int:
        """Clear all jobs from a queue.

        Args:
            queue_name: Queue name

        Returns:
            int: Number of jobs removed

        """
        queue = cls.get_queue(queue_name)
        count = len(queue)
        queue.empty()
        logger.warning(f"Cleared {count} jobs from queue '{queue_name}'")
        return count
