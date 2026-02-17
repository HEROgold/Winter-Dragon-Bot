"""Queue monitoring utilities for Redis queues."""

from __future__ import annotations

import asyncio
from inspect import isawaitable

from herogold.log import LoggerMixin
from herogold.log.logging import getLogger

from winter_dragon.redis.connection import RedisConnection


logger = getLogger("QueueMonitor")


class QueueMonitor(LoggerMixin):
    """Monitor Redis queue statistics."""

    @staticmethod
    def get_queue_length(queue_name: str) -> int:
        """Get the current length of a queue.

        Args:
            queue_name: Name of the queue to check

        Returns:
            Number of jobs in the queue

        """
        try:
            redis_conn = RedisConnection.get_connection()
            # RQ stores queues as lists with key "rq:queue:{name}"
            key = f"rq:queue:{queue_name}"
            length = redis_conn.llen(key)
            if isawaitable(length):
                return asyncio.get_event_loop().run_until_complete(length)
        except Exception:
            logger.exception("Error getting queue length")
            return 0
        else:
            return length

    @staticmethod
    def get_all_queue_lengths() -> dict[str, int]:
        """Get lengths of all RQ queues.

        Returns:
            Dictionary mapping queue names to their lengths

        """
        try:
            redis_conn = RedisConnection.get_connection()
            # Find all RQ queue keys
            queue_keys = redis_conn.keys("rq:queue:*")
            if isawaitable(queue_keys):
                queue_keys = asyncio.get_event_loop().run_until_complete(queue_keys)

            lengths = {}
            for key in queue_keys:
                # Extract queue name from key
                queue_name = key.decode("utf-8").replace("rq:queue:", "")
                length = redis_conn.llen(key)
                lengths[queue_name] = length

        except Exception:
            logger.exception("Error getting all queue lengths")
            return {}
        else:
            return lengths
