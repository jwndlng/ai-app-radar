from __future__ import annotations

from .base import BaseProvider

_WORKABLE_API = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
_WORKABLE_JOB_URL = "https://apply.workable.com/{slug}/j/{shortcode}"


class WorkableProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        slug = self._resolve_slug(company_config)

        response = await self._post(_WORKABLE_API.format(slug=slug), json={})
        data = response.json()

        jobs: list[dict] = []
        for job in data.get("results", []):
            title = job.get("title", "")
            shortcode = job.get("shortcode", "")
            job_url = _WORKABLE_JOB_URL.format(slug=slug, shortcode=shortcode)
            location = self._extract_location(job)

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

    @staticmethod
    def _extract_location(job: dict) -> str:
        if job.get("remote"):
            return "Remote"
        loc = job.get("location") or {}
        city = loc.get("city", "")
        country = loc.get("country", "")
        return ", ".join(filter(None, [city, country]))
