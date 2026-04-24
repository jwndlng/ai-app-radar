"""PipelineRuntime — generic asyncio queue/worker loop for any BaseTask."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Callable

from core.task import BaseTask


class PipelineRuntime:
    def __init__(self, task: BaseTask) -> None:
        self._task = task

    async def run(
        self,
        concurrency: int | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        task = self._task
        n = concurrency if concurrency is not None else task.concurrency
        producer = task.producer
        consumer = task.consumer

        items = await producer.produce()
        random.shuffle(items)
        if task.limit is not None:
            items = items[: task.limit]

        total = len(items)
        await consumer.on_start(total)
        if on_progress:
            on_progress(0, total)

        if not items:
            await consumer.finalize()
            return

        queue: asyncio.Queue = asyncio.Queue()
        completed: dict[str, int] = {"count": 0}
        lock = asyncio.Lock()
        last_started: dict[str, Any] = {"t": asyncio.get_event_loop().time() - 50.0}

        workers = [
            asyncio.create_task(
                self._worker(queue, consumer, task, completed, lock, last_started, total, on_progress)
            )
            for _ in range(n)
        ]

        for item in items:
            await queue.put(item)
        for _ in range(n):
            await queue.put(None)

        await queue.join()
        for w in workers:
            w.cancel()

        await consumer.finalize()

    async def _worker(
        self,
        queue: asyncio.Queue,
        consumer: Any,
        task: BaseTask,
        completed: dict[str, int],
        lock: asyncio.Lock,
        last_started: dict[str, Any],
        total: int = 0,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break

            try:
                if task.start_gap is not None:
                    await self._acquire_start_slot(lock, last_started, task.start_gap)
                await consumer.consume(item)
            finally:
                queue.task_done()
                completed["count"] += 1
                if on_progress:
                    on_progress(completed["count"], total)
                if completed["count"] % task.checkpoint_every == 0:
                    await consumer.checkpoint()

    @staticmethod
    async def _acquire_start_slot(
        lock: asyncio.Lock,
        last_started: dict[str, Any],
        start_gap: tuple[float, float],
    ) -> None:
        async with lock:
            now = asyncio.get_event_loop().time()
            gap = random.uniform(start_gap[0], start_gap[1])
            wait = last_started["t"] + gap - now
            if wait > 0:
                await asyncio.sleep(wait)
            last_started["t"] = asyncio.get_event_loop().time()
