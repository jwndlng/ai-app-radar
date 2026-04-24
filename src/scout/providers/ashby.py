from __future__ import annotations

from .base import BaseProvider

_ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbyProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        slug = self._resolve_slug(company_config)

        response = await self._get(_ASHBY_API.format(slug=slug))
        data = response.json()

        jobs: list[dict] = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            job_url = job.get("jobUrl", "")
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
        if job.get("isRemote"):
            return "Remote"
        address = job.get("address") or {}
        postal = address.get("postalAddress") or {}
        city = postal.get("addressLocality", "")
        country = postal.get("addressCountry", "")
        return ", ".join(filter(None, [city, country])) or job.get("location", "")
