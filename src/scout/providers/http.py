from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProvider

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class HttpProvider(BaseProvider):
    """Lightweight provider for server-rendered pages that don't need a browser."""

    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        url = company_config.get("careers_url", "")
        company = company_config.get("name", "")
        card_sel = company_config.get("card_selector", "")
        title_sel = company_config.get("title_selector", "a")
        loc_sel = company_config.get("location_selector", "")

        if not url or not card_sel:
            print(f"  [!] HttpProvider: missing careers_url or card_selector for {company}")
            return []

        resp = await self._get(url, headers=_HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(card_sel)

        if not cards:
            print(f"  [!] HttpProvider: no cards matched '{card_sel}' for {company}")
            return []

        jobs: list[dict] = []
        for card in cards:
            title_el = card.select_one(title_sel)
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or not self.filter_job(title, filters):
                continue

            href = title_el.get("href", "")
            job_url = urljoin(url, href) if href else url

            location = ""
            if loc_sel:
                loc_el = card.select_one(loc_sel)
                if loc_el:
                    location = loc_el.get_text(strip=True)

            jobs.append({"title": title, "url": job_url, "company": company, "location": location})

        print(f"  [+] HttpProvider: {len(jobs)} jobs found for {company}")
        return jobs
