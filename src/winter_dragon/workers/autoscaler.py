"""Auto-scaling service for RQ workers based on queue length.

This service monitors Redis queues and automatically scales the number of
worker processes based on the current workload.
"""

from __future__ import annotations

import asyncio
import logging
import math
import signal
import subprocess
import sys

from herogold.log import LoggerMixin

from winter_dragon.config import Config
from winter_dragon.redis.connection import RedisConnection
from winter_dragon.redis.queue import TaskQueue


class WorkerScalingConfig:
    """Configuration for worker auto-scaling."""

    min_workers = Config(default=1)
    """Minimum number of workers to maintain."""

    max_workers = Config(default=10)
    """Maximum number of workers allowed."""

    scaling_threshold_base = Config(default=10)
    """Base threshold: 10 items = 1 additional worker."""

    check_interval = Config(default=30)
    """How often to check queue length and adjust workers (seconds)."""

    scale_up_cooldown = Config(default=60)
    """Cooldown after scaling up before checking again (seconds)."""

    scale_down_cooldown = Config(default=300)
    """Cooldown after scaling down before checking again (seconds)."""

    grace_period = Config(default=10)
    """Grace period for workers to shut down gracefully (seconds)."""


class WorkerAutoScaler(LoggerMixin):
    """Automatically scales RQ workers based on queue length.

    Scaling formula:
    - 1-9 items: 1 worker
    - 10-99 items: 2 workers
    - 100-999 items: 3 workers
    - etc.
    """

    def __init__(
        self,
        queue_names: list[str] | None = None,
        *,
        worker_command: str = "python -m winter_dragon.workers.worker",
    ) -> None:
        """Initialize the auto-scaler.

        Args:
            queue_names: List of queue names to monitor (None = all queues)
            worker_command: Command to start worker processes

        """
        self.queue_names = queue_names or [TaskQueue.DEFAULT_QUEUE]
        self.worker_command = worker_command
        self.worker_processes: list[subprocess.Popen] = []
        self.target_workers = WorkerScalingConfig.min_workers
        self.last_scale_up = 0.0
        self.last_scale_down = 0.0
        self.is_running = False
        self._last_logged_state = None  # Track last state for spam reduction

        self.logger.info(
            f"Initialized WorkerAutoScaler for queues: {', '.join(self.queue_names)}",
            extra={
                "min_workers": WorkerScalingConfig.min_workers,
                "max_workers": WorkerScalingConfig.max_workers,
                "queues": self.queue_names,
            },
        )

    async def start(self) -> None:
        """Start the auto-scaling service."""
        self.is_running = True
        self.logger.info("Starting worker auto-scaler")

        # Start initial workers
        await self._scale_to(WorkerScalingConfig.min_workers)

        # Main monitoring loop
        try:
            while self.is_running:
                await asyncio.sleep(WorkerScalingConfig.check_interval)
                await self._check_and_scale()
        except asyncio.CancelledError:
            self.logger.info("Auto-scaler cancelled, shutting down")
            await self.stop()
        except Exception:
            self.logger.exception("Auto-scaler error")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the auto-scaling service and all workers."""
        self.is_running = False
        self.logger.info("Stopping auto-scaler and all workers")

        # Terminate all worker processes
        for process in self.worker_processes:
            try:
                self.logger.info(f"Terminating worker process {process.pid}")
                process.terminate()
            except Exception:
                self.logger.exception(f"Error terminating process {process.pid}")

        # Wait for graceful shutdown
        await asyncio.sleep(WorkerScalingConfig.grace_period)

        # Force kill any remaining processes
        for process in self.worker_processes:
            try:
                if process.poll() is None:  # Still running
                    self.logger.warning(f"Force killing worker process {process.pid}")
                    process.kill()
            except Exception:
                self.logger.exception(f"Error killing process {process.pid}")

        self.worker_processes.clear()
        self.logger.info("All workers stopped")

    async def _check_and_scale(self) -> None:
        """Check queue length and scale workers accordingly."""
        try:
            # Get total queue length across all monitored queues
            total_items = 0
            for queue_name in self.queue_names:
                try:
                    length = TaskQueue.get_queue_length(queue_name)
                    total_items += length
                except Exception:
                    self.logger.exception(f"Error getting queue length for {queue_name}")

            # Calculate desired number of workers using logarithmic scaling
            # Formula> workers = ceil(log10(max(items, 1))) + 1
            # 1-9 items = 1 worker, 10-99 = 2, 100-999 = 3, etc.
            if total_items == 0:
                desired_workers = WorkerScalingConfig.min_workers
            else:
                desired_workers = math.ceil(math.log10(total_items)) + 1
                desired_workers = max(WorkerScalingConfig.min_workers, desired_workers)
                desired_workers = min(WorkerScalingConfig.max_workers, desired_workers)

            current_workers = len(self.worker_processes)
            current_state = (total_items, current_workers, desired_workers)

            # Only log if state changed (not same as last check)
            if current_state != self._last_logged_state:
                self.logger.debug(
                    f"Queue check: {total_items} items, {current_workers} workers, target {desired_workers}",
                    extra={
                        "queue_items": total_items,
                        "current_workers": current_workers,
                        "desired_workers": desired_workers,
                    },
                )
                self._last_logged_state = current_state

            # Check cooldown periods
            current_time = asyncio.get_event_loop().time()

            if desired_workers > current_workers:
                # Scale up
                if current_time - self.last_scale_up >= WorkerScalingConfig.scale_up_cooldown:
                    await self._scale_to(desired_workers)
                    self.last_scale_up = current_time
                else:
                    self.logger.debug("Scale up on cooldown, skipping")

            elif desired_workers < current_workers:
                # Scale down
                if current_time - self.last_scale_down >= WorkerScalingConfig.scale_down_cooldown:
                    await self._scale_to(desired_workers)
                    self.last_scale_down = current_time
                else:
                    self.logger.debug("Scale down on cooldown, skipping")

        except Exception:
            self.logger.exception("Error in check_and_scale")

    async def _scale_to(self, target: int) -> None:
        """Scale workers to target count.

        Args:
            target: Desired number of worker processes

        """
        current = len(self.worker_processes)

        if target == current:
            return

        if target > current:
            # Scale up
            to_add = target - current
            self.logger.info(f"Scaling up: adding {to_add} workers ({current} → {target})")

            for i in range(to_add):
                await self._start_worker(current + i)

        elif target < current:
            # Scale down
            to_remove = current - target
            self.logger.info(f"Scaling down: removing {to_remove} workers ({current} → {target})")

            for _ in range(to_remove):
                await self._stop_worker()

        # Clean up dead processes
        self._cleanup_dead_processes()

        self.logger.info(
            f"Scaled to {len(self.worker_processes)} workers",
            extra={"worker_count": len(self.worker_processes), "target": target},
        )

    async def _start_worker(self, worker_id: int) -> None:
        """Start a new worker process.

        Args:
            worker_id: Unique identifier for this worker

        """
        try:
            # Build command with worker name
            worker_name = f"autoscale_worker_{worker_id}"
            queues = ",".join(self.queue_names)

            self.logger.info(f"Starting worker {worker_id} for queues: {queues}")

            # Start process (works in Docker and locally)
            cmd = [
                sys.executable,
                "-m",
                "winter_dragon.workers.worker",
                "--name",
                worker_name,
                "--queues",
                *self.queue_names,
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            self.worker_processes.append(process)

            self.logger.info(
                f"Worker {worker_id} started with PID {process.pid}",
                extra={"worker_id": worker_id, "pid": process.pid},
            )

        except Exception:
            self.logger.exception(f"Failed to start worker {worker_id}")

    async def _stop_worker(self) -> None:
        """Stop the most recently started worker."""
        if not self.worker_processes:
            return

        process = self.worker_processes.pop()

        try:
            self.logger.info(f"Stopping worker with PID {process.pid}")

            # Send SIGTERM for graceful shutdown
            process.terminate()

            # Wait briefly for graceful shutdown
            try:
                process.wait(timeout=WorkerScalingConfig.grace_period)
                self.logger.info(f"Worker {process.pid} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if still running
                self.logger.warning(f"Worker {process.pid} did not stop gracefully, force killing")
                process.kill()
                process.wait()

        except Exception:
            self.logger.exception(f"Error stopping worker {process.pid}")

    def _cleanup_dead_processes(self) -> None:
        """Remove dead processes from the worker list."""
        alive = []
        for process in self.worker_processes:
            if process.poll() is None:  # Still running
                alive.append(process)
            else:
                self.logger.warning(f"Worker process {process.pid} died unexpectedly with code {process.returncode}")

        if len(alive) < len(self.worker_processes):
            self.logger.info(f"Cleaned up {len(self.worker_processes) - len(alive)} dead processes")
            self.worker_processes = alive


async def main() -> None:
    """."""
    import argparse

    parser = argparse.ArgumentParser(description="RQ Worker Auto-Scaler")
    parser.add_argument(
        "--queues",
        "-q",
        nargs="+",
        default=None,
        help="Queue names to monitor (default: steam_scraper, default)",
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
            logging.info("✓ Redis connection successful")
            sys.exit(0)
        else:
            logging.info("✗ Redis connection failed")
            sys.exit(1)

    # Create and start auto-scaler
    scaler = WorkerAutoScaler(queue_names=args.queues)

    # Handle shutdown signals
    def signal_handler(signum: int, frame: object) -> None:
        scaler.logger.info(f"Received signal {signum}, shutting down")
        task = asyncio.create_task(scaler.stop())
        task.add_done_callback(lambda _: None)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await scaler.start()
    except KeyboardInterrupt:
        scaler.logger.info("Keyboard interrupt received")
        await scaler.stop()
    finally:
        RedisConnection.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
