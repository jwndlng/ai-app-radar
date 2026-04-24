"""WorkdayProvider — fetches jobs via Workday's undocumented but stable CXS JSON API."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseProvider

_API_PATH = "/wday/cxs/{tenant}/{board}/jobs"
_LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
_PAGE_SIZE = 20


class WorkdayProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        host, tenant, board = self._parse_url(company_config.get("careers_url", ""))
        if not tenant or not board:
            return []

        api_url = f"https://{host}" + _API_PATH.format(tenant=tenant, board=board)
        job_base = f"https://{host}"
        jobs: list[dict] = []
        offset = 0

        total = 0

        while True:
            response = await self._post(
                api_url,
                json={"appliedFacets": {}, "limit": _PAGE_SIZE, "offset": offset, "searchText": ""},
                headers={"Content-Type": "application/json"},
            )
            data = response.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break

            # Workday only returns total on the first page; preserve it across pages
            if data.get("total"):
                total = data["total"]

            for posting in postings:
                title = posting.get("title", "")
                external_path = posting.get("externalPath", "")
                location = posting.get("locationsText", "")
                job_url = f"{job_base}/{board}{external_path}"

                if self.filter_job(title, filters):
                    jobs.append({
                        "title": title,
                        "url": job_url,
                        "company": company_name,
                        "location": location,
                    })

            offset += len(postings)
            if offset >= total:
                break

        return jobs

    @staticmethod
    def _parse_url(careers_url: str) -> tuple[str, str, str]:
        """Extract (host, tenant, board) from https://{tenant}.wd*.myworkdayjobs.com/{board}."""
        try:
            parsed = urlparse(careers_url)
            host = parsed.hostname
            tenant = host.split(".")[0]
            segments = [s for s in parsed.path.strip("/").split("/") if s]
            board = next((s for s in segments if not _LOCALE_RE.match(s)), segments[0] if segments else "")
            return host, tenant, board
        except Exception:
            return "", "", ""
