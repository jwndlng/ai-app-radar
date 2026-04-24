from __future__ import annotations

from .base import BaseProvider

_API_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
_JOB_URL = "https://jobs.smartrecruiters.com/{slug}/{job_id}"
_PAGE_SIZE = 100


class SmartRecruitersProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        slug = company_config.get("scan_method_config", {}).get("slug")
        if not slug:
            print(f"  [!] {company_name}: missing slug in scan_method_config")
            return []

        jobs: list[dict] = []
        offset = 0

        while True:
            response = await self._get(
                _API_URL.format(slug=slug),
                params={"limit": _PAGE_SIZE, "offset": offset},
            )
            data = response.json()

            for job in data.get("content", []):
                title = job.get("name", "")
                job_id = job.get("id")
                location = self._extract_location(job)

                if self.filter_job(title, filters):
                    jobs.append({
                        "title": title,
                        "url": _JOB_URL.format(slug=slug, job_id=job_id),
                        "company": company_name,
                        "location": location,
                    })

            total = data.get("totalFound", 0)
            offset += len(data.get("content", []))
            if offset >= total:
                break

        return jobs

    @staticmethod
    def _extract_location(job: dict) -> str:
        loc = job.get("location", {})
        if loc.get("remote"):
            return "Remote"
        if loc.get("hybrid"):
            full = loc.get("fullLocation", "")
            return f"Hybrid — {full}" if full else "Hybrid"
        return loc.get("fullLocation", "")
