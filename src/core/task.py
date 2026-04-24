"""Abstract base classes for the pipeline task/runtime framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseProducer(ABC, Generic[T]):
    @abstractmethod
    async def produce(self) -> list[T]: ...


class BaseConsumer(ABC, Generic[T]):
    @abstractmethod
    async def consume(self, item: T) -> None: ...

    async def on_start(self, total: int) -> None:
        pass

    async def checkpoint(self) -> None:
        pass

    async def finalize(self) -> None:
        pass


class BaseTask(ABC, Generic[T]):
    concurrency: int = 5
    checkpoint_every: int = 5
    start_gap: tuple[float, float] | None = (0.25, 1.0)
    limit: int | None = None

    @property
    @abstractmethod
    def producer(self) -> BaseProducer[T]: ...

    @property
    @abstractmethod
    def consumer(self) -> BaseConsumer[T]: ...
