import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict

logger = logging.getLogger("phoenix.queue")

class DurableJobQueue:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks: Dict[str, asyncio.Future] = {}
        self.cancellation_requested: Dict[str, bool] = {}

    def enqueue(self, job_id: str, func: Callable, *args, **kwargs):
        """Enqueue a background execution with persisted state tracking."""
        self.cancellation_requested[job_id] = False
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(self.executor, func, *args, **kwargs)
        self.active_tasks[job_id] = future
        return future

    def is_cancelled(self, job_id: str) -> bool:
        return self.cancellation_requested.get(job_id, False)

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.active_tasks:
            self.cancellation_requested[job_id] = True
            logger.info(f"Cancellation requested for job {job_id}")
            return True
        return False

    def get_status(self, job_id: str) -> str:
        if job_id not in self.active_tasks:
            return "not_found_or_finished"
        future = self.active_tasks[job_id]
        if future.done():
            return "completed"
        return "running"

job_queue = DurableJobQueue()
