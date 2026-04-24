from __future__ import annotations

from .base import BaseProvider


class GreenhouseProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        api_url = company_config.get("scan_method_config", {}).get("api_base")
        if not api_url:
            return []

        response = await self._get(api_url)
        data = response.json()

        careers_url = company_config.get("careers_url", "").rstrip("/")
        jobs: list[dict] = []
        for job in data.get("jobs", []):
            title = job.get("title")
            job_id = job.get("id")
            url = self._build_job_url(careers_url, job_id) or job.get("absolute_url")
            location = job.get("location", {}).get("name", "Remote/Global")

            if self.filter_job(title, filters):
                jobs.append({
                    "title": title,
                    "url": url,
                    "company": company_name,
                    "location": location,
                })
        return jobs

    @staticmethod
    def _build_job_url(careers_url: str, job_id: int | str | None) -> str | None:
        if careers_url and job_id:
            return f"{careers_url}/jobs/{job_id}"
        return None
