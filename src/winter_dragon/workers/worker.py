"""RQ Worker entry point for distributed task processing.

Run this script to start a worker that processes tasks from Redis queues.

Usage:
    python -m winter_dragon.workers.worker

    # Or with specific queues:
    python -m winter_dragon.workers.worker --queues high_priority

    # With multiple workers:
    python -m winter_dragon.workers.worker --workers 4
"""

from __future__ import annotations

import argparse
import multiprocessing
import sys

from herogold.log import LoggerMixin
from rq import Worker

from winter_dragon.redis.connection import RedisConnection
from winter_dragon.redis.queue import TaskQueue


class RQWorker(LoggerMixin):
    """RQ Worker manager for processing distributed tasks."""

    def __init__(
        self,
        queues: list[str] | None = None,
        *,
        worker_name: str | None = None,
    ) -> None:
        """Initialize the RQ worker.

        Args:
            queues: List of queue names to process (None = all queues)
            worker_name: Custom name for this worker

        """
        self.redis_conn = RedisConnection.get_connection()

        # Default to default queue if none specified
        if queues is None:
            queues = [TaskQueue.DEFAULT_QUEUE]

        self.queue_names = queues
        self.worker_name = worker_name

        self.logger.info(
            f"Initializing RQ worker for queues: {', '.join(self.queue_names)}",
            extra={"queues": self.queue_names, "worker_name": worker_name},
        )

    def start(self) -> None:
        """Start the worker and begin processing tasks."""
        try:
            # Get queue objects
            queues = [TaskQueue.get_queue(name) for name in self.queue_names]

            self.logger.info(f"Starting worker to process {len(queues)} queue(s)")

            # Create and start worker
            worker = Worker(
                queues,
                connection=self.redis_conn,
                name=self.worker_name,
            )

            # Start worker (blocking call)
            worker.work(with_scheduler=True)

        except KeyboardInterrupt:
            self.logger.info("Worker interrupted by user")
            sys.exit(0)
        except Exception:
            self.logger.exception("Worker error")
            sys.exit(1)
        finally:
            RedisConnection.close_connection()


def main() -> None:
    """."""
    parser = argparse.ArgumentParser(
        description="RQ Worker for Winter Dragon Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--queues",
        "-q",
        nargs="+",
        default=None,
        help="Queue names to process (default: steam_scraper, default)",
    )

    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Custom name for this worker",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=1,
        help="Number of worker processes to spawn (default: 1)",
    )

    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test Redis connection and exit",
    )

    args = parser.parse_args()

    # Test connection if requested
    if args.test_connection:
        if RedisConnection.test_connection():
            sys.exit(0)
        else:
            sys.exit(1)

    # Start worker(s)
    if args.workers == 1:
        # Single worker
        worker = RQWorker(queues=args.queues, worker_name=args.name)
        worker.start()
    else:
        # Multiple workers using multiprocessing

        def start_worker(worker_id: int) -> None:
            worker_name = f"{args.name or 'worker'}_{worker_id}"
            worker = RQWorker(queues=args.queues, worker_name=worker_name)
            worker.start()

        processes = []
        for i in range(args.workers):
            p = multiprocessing.Process(target=start_worker, args=(i,))
            p.start()
            processes.append(p)

        # Wait for all processes
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            for p in processes:
                p.terminate()
            for p in processes:
                p.join()


if __name__ == "__main__":
    main()
