"""Notifier abstraction — decouple notification delivery from pipeline consumers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    async def on_match(self, job: dict, score: float, reasons: list[str]) -> None: ...

    @abstractmethod
    async def on_review(self, job: dict, score: float, reasons: list[str]) -> None: ...

    @abstractmethod
    async def on_run_summary(self, matched: int, reviewed: int) -> None: ...

    @abstractmethod
    async def on_scout_summary(self, discovered: int) -> None: ...

    @abstractmethod
    async def on_enrich_summary(self, enriched: int) -> None: ...


class NullNotifier(Notifier):
    async def on_match(self, job: dict, score: float, reasons: list[str]) -> None:
        pass

    async def on_review(self, job: dict, score: float, reasons: list[str]) -> None:
        pass

    async def on_run_summary(self, matched: int, reviewed: int) -> None:
        pass

    async def on_scout_summary(self, discovered: int) -> None:
        pass

    async def on_enrich_summary(self, enriched: int) -> None:
        pass
