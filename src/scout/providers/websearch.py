from __future__ import annotations

import asyncio
import urllib.robotparser
from urllib.parse import urlparse

import httpx

from .base import BaseProvider
from scout.agent import ScoutAgent

# Body text and the appended links block are capped separately: a single
# trailing truncation would cut off the links section entirely on large
# pages, leaving the agent without URLs or pagination targets.
_MAX_BODY_CHARS = 30_000
_MAX_LINKS_CHARS = 10_000

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class WebsearchProvider(BaseProvider):
    def __init__(
        self,
        model: str | None = None,
        max_pages: int = 10,
        respect_robots: bool = True,
    ) -> None:
        super().__init__()
        self._model = model
        self._max_pages = max_pages
        self._respect_robots = respect_robots
        self._last_page_count: int = 0

    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name", "?")
        careers_url = company_config.get("careers_url", "")
        content_selector = company_config.get("content_selector")

        if not careers_url:
            print(f"  [!] {company_name}: no careers_url configured")
            return []

        agent = ScoutAgent(company_name, model=self._model)
        current_url = company_config.get("scan_method_config", {}).get("search_url") or careers_url

        # Check the URL the crawl actually starts from, not just careers_url.
        if self._respect_robots and not await self._robots_allows(current_url):
            print(f"  [robots] {company_name}: blocked by robots.txt")
            return []
        visited: set[str] = set()
        jobs: list[dict] = []

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                for page_num in range(1, self._max_pages + 1):
                    if current_url in visited:
                        break
                    visited.add(current_url)

                    content = await self._fetch_page(company_name, current_url, content_selector, browser)
                    if not content or not content.strip():
                        break

                    response = await agent.extract_jobs(content)

                    for job in response.jobs:
                        if job.title and self.filter_job(job.title, filters):
                            jobs.append({
                                "title": job.title,
                                "url": job.url,
                                "company": company_name,
                                "location": job.location,
                            })

                    if not response.jobs:
                        print(f"  [~] {company_name}: no jobs on page {page_num}, stopping")
                        break

                    if not response.next_page_url:
                        break

                    print(f"  [>] {company_name}: following page {page_num + 1}")
                    await asyncio.sleep(0.25)
                    current_url = response.next_page_url
            finally:
                await browser.close()

        self._last_page_count = len(visited)
        return jobs

    @staticmethod
    async def _robots_allows(url: str) -> bool:
        # Fetch robots.txt with a browser UA: RobotFileParser.read() uses the
        # default Python-urllib UA, which bot protection commonly 403s, and it
        # then treats the site as fully disallowed. Any non-200 (no robots.txt,
        # blocked fetch) is treated as allow.
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": _BROWSER_UA}) as client:
                resp = await client.get(robots_url)
            if resp.status_code != 200:
                return True
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            return rp.can_fetch("*", url)
        except Exception:
            return True

    @staticmethod
    async def _fetch_page(
        company_name: str,
        careers_url: str,
        content_selector: str | None,
        browser: object,
    ) -> str | None:
        try:
            from playwright.async_api import Error as PlaywrightError

            _is_workday = "workdayjobs.com" in careers_url

            page = await browser.new_page()  # type: ignore[attr-defined]
            try:
                try:
                    wait_event = "domcontentloaded" if _is_workday else "networkidle"
                    await page.goto(careers_url, wait_until=wait_event, timeout=30_000)
                except PlaywrightError:
                    # Heavy SPAs (Microsoft, Oracle, …) never reach networkidle.
                    # Proceed with whatever the page has loaded so far.
                    pass

                if _is_workday:
                    # Workday SPAs need scroll stimulus to trigger job result rendering.
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(4)
                    await page.mouse.wheel(0, -500)
                    await asyncio.sleep(3)

                target = page.locator(content_selector) if content_selector else None
                if target:
                    count = await target.count()
                    if count == 0:
                        print(f"  [~] {company_name}: selector {content_selector!r} matched nothing, falling back to body")
                        target = page.locator("body").first
                    else:
                        # .first avoids a strict-mode violation when the
                        # selector matches more than one element.
                        target = target.first
                else:
                    target = page.locator("body").first

                body_text = await target.inner_text()

                links = await page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => ({"
                    "  text: (e.getAttribute('aria-label') || e.innerText || e.getAttribute('title') || '').trim(),"
                    "  href: e.href"
                    "})).filter(l => l.text)",
                )
                links_block = "\n".join(f"[{l['text']}] {l['href']}" for l in links) if links else ""

                content = body_text[:_MAX_BODY_CHARS]
                if links_block:
                    content += f"\n\n--- PAGE LINKS ---\n{links_block[:_MAX_LINKS_CHARS]}"

                return content
            finally:
                await page.close()

        except Exception as e:
            print(f"  [!] {company_name}: Playwright error: {e}")
            return None
