from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod

import httpx

_TIMEOUT = 30.0
_MAX_RETRIES = 3
_DEFAULT_CONCURRENCY = 10


class BaseProvider(ABC):
    def __init__(self, concurrency: int = _DEFAULT_CONCURRENCY) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)

    @abstractmethod
    async def scout(self, company_config: dict, filters: dict) -> list[dict]: ...

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def _post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", _TIMEOUT)
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0:
                await asyncio.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s
            try:
                async with self._semaphore:
                    async with httpx.AsyncClient() as client:
                        response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.TimeoutException as e:
                last_exc = e
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_exc = e
                else:
                    raise
        assert last_exc is not None
        raise last_exc

    def filter_job(self, title: str, filters: dict) -> bool:
        title_lower = title.lower()

        def _make_pattern(term: str) -> re.Pattern:
            t = term.lower()
            prefix = r"\b" if t[0].isalnum() else r"(?:^|\s|[^\w])"
            suffix = r"\b" if t[-1].isalnum() else r"(?:$|\s|[^\w])"
            return re.compile(prefix + re.escape(t) + suffix)

        positives = [_make_pattern(p) for p in filters.get("positive", []) if p]
        negatives = [_make_pattern(n) for n in filters.get("negative", []) if n]
        # No positive filters configured means "accept everything" — otherwise
        # a missing scout_filters section silently rejects every job.
        return (
            (not positives or any(p.search(title_lower) for p in positives))
            and not any(n.search(title_lower) for n in negatives)
        )
