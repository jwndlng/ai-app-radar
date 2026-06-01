"""TelegramNotifier — sends job match/review alerts via Telegram Bot API."""

from __future__ import annotations

import sys

import httpx

from notifications.notifier import Notifier

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 5.0


class TelegramNotifier(Notifier):
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        notify_match: bool = True,
        notify_review: bool = True,
        notify_evaluate_summary: bool = True,
        notify_scout_summary: bool = True,
        notify_enrich_summary: bool = True,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._notify_match = notify_match
        self._notify_review = notify_review
        self._notify_evaluate_summary = notify_evaluate_summary
        self._notify_scout_summary = notify_scout_summary
        self._notify_enrich_summary = notify_enrich_summary
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    async def on_match(self, job: dict, score: float, reasons: list[str]) -> None:
        if not self._notify_match:
            return
        text = self._format_job("✅ Match", job, score, reasons)
        await self._send(text)

    async def on_review(self, job: dict, score: float, reasons: list[str]) -> None:
        if not self._notify_review:
            return
        text = self._format_job("👀 Review", job, score, reasons)
        await self._send(text)

    async def on_run_summary(self, matched: int, reviewed: int) -> None:
        if not self._notify_evaluate_summary:
            return
        text = (
            f"📊 Evaluate complete\n"
            f"{matched} match{'es' if matched != 1 else ''}, "
            f"{reviewed} review{'s' if reviewed != 1 else ''}"
        )
        await self._send(text)

    async def on_scout_summary(self, discovered: int) -> None:
        if not self._notify_scout_summary:
            return
        text = f"🔍 Scout complete\n{discovered} new job{'s' if discovered != 1 else ''} discovered"
        await self._send(text)

    async def on_enrich_summary(self, enriched: int) -> None:
        if not self._notify_enrich_summary:
            return
        text = f"⚙️ Enrich complete\n{enriched} job{'s' if enriched != 1 else ''} enriched"
        await self._send(text)

    @staticmethod
    def _format_job(prefix: str, job: dict, score: float, reasons: list[str]) -> str:
        title = job.get("title", "?")
        company = job.get("company", "?")
        top_reasons = "\n".join(f"→ {r}" for r in reasons[:3])
        lines = [f"{prefix} — {score}/10", f"", f"{title}", f"@ {company}"]
        if top_reasons:
            lines += ["", top_reasons]
        return "\n".join(lines)

    async def _send(self, text: str) -> None:
        try:
            url = _API.format(token=self._token)
            resp = await self._client.post(url, json={"chat_id": self._chat_id, "text": text})
            if not resp.is_success:
                print(f"[telegram] API error {resp.status_code}: {resp.text}", file=sys.stderr)
        except Exception as exc:
            print(f"[telegram] notification failed: {exc}", file=sys.stderr)
