from __future__ import annotations

from .base import BaseProvider

_LEVER_API = "https://api.lever.co/v0/postings/{slug}"


class LeverProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(concurrency=3)

    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        slug = self._resolve_slug(company_config)

        response = await self._get(_LEVER_API.format(slug=slug), params={"mode": "json"})
        data = response.json()

        jobs: list[dict] = []
        for job in data:
            title = job.get("text", "")
            job_url = job.get("hostedUrl", "")
            location = (job.get("categories") or {}).get("location", "")

            if self.filter_job(title, filters):
                jobs.append({
                    "title": title,
                    "url": job_url,
                    "company": company_name,
                    "location": location,
                })
        return jobs

    @staticmethod
    def _resolve_slug(company_config: dict) -> str:
        slug = company_config.get("scan_method_config", {}).get("slug")
        if slug:
            return slug
        return company_config.get("careers_url", "").rstrip("/").split("/")[-1]
