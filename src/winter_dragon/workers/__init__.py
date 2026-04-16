"""Redis Queue worker module for Winter Dragon Bot."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from redis import Redis
from rq import Queue

from winter_dragon.config import Config


if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = ["enqueue_task", "get_queue"]


class RedisConnection:
    """Static class to manage Redis connection."""

    _redis_connection: Redis | None = None
    HOST = Config("REDIS_HOST")
    PORT = Config(6379)
    DB = Config(0)

    @staticmethod
    def get_redis_connection() -> Redis:
        """Get or create Redis connection."""
        if RedisConnection._redis_connection is None:
            # Prefer environment variables (Docker) and fall back to Config
            redis_host = os.getenv("REDIS_HOST") or RedisConnection.HOST
            redis_port = int(os.getenv("REDIS_PORT") or RedisConnection.PORT)
            redis_db = int(os.getenv("REDIS_DB") or RedisConnection.DB)

            RedisConnection._redis_connection = Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
            )
        return RedisConnection._redis_connection

    @staticmethod
    def get_queue(name: str = "default") -> Queue:
        """Get a Redis queue by name.

        Args:
            name: Queue name (default: "default")

        Returns:
            Queue instance
        """
        return Queue(name, connection=RedisConnection.get_redis_connection())

    @staticmethod
    def enqueue_task[**P](
        func: Callable[P, Any],
        queue_name: str = "default",
        job_id: str | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> str:
        """Enqueue a function to be executed by a worker.

        Args:
            func: Callable function to enqueue
            queue_name: Name of the queue (default: "default")
            job_id: Optional job ID (default: auto-generated)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Job ID of the enqueued task
        """
        queue = RedisConnection.get_queue(queue_name)
        job = queue.enqueue(func, *args, job_id=job_id, **kwargs)
        return job.id


enqueue_task = RedisConnection.enqueue_task
get_queue = RedisConnection.get_queue
