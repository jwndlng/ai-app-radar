from __future__ import annotations

import asyncio
import random
from urllib.parse import urljoin

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

from .base import BaseProvider

_USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
]

_COOKIE_SELECTORS = [
    "button:has-text('Accept')",
    "button:has-text('Agree')",
    "button:has-text('Allow')",
    "#onetrust-accept-btn-handler",
    ".css-1nlu34x",
    "[data-automation-id='legalNoticeBlocker'] button",
]

_WORKDAY_WAIT_SELECTORS = [
    "[data-automation-id='searchResultsListItem']",
    "li[data-automation-id='jobResultItem']",
    "section ul li",
]


class ScraperProvider(BaseProvider):
    async def scout(self, company_config: dict, filters: dict) -> list[dict]:
        company_name = company_config.get("name")
        url = company_config.get("careers_url")
        card_selector = company_config.get("card_selector")
        title_selector = company_config.get("title_selector", "a")
        location_selector = company_config.get("location_selector")
        company_selector = company_config.get("company_selector")
        wait_for = company_config.get("wait_for")

        if not url:
            return []

        jobs: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random.choice(_USER_AGENTS))
            page = await context.new_page()

            try:
                print(f"  [Scraping] {company_name}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                await self._dismiss_cookie_banners(page)

                if "workdayjobs.com" in url:
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(5)
                    await page.mouse.wheel(0, -500)
                    await asyncio.sleep(random.uniform(5, 10))

                if wait_for:
                    if "swissdevjobs" in url.lower():
                        await asyncio.sleep(8)
                    await self._wait_for_content(page, wait_for, company_name)

                await asyncio.sleep(3)

                if not card_selector:
                    jobs = await self._extract_by_links(page, url, company_name, filters)
                else:
                    jobs = await self._extract_by_cards(
                        page, url, company_name, card_selector,
                        title_selector, location_selector, company_selector, filters,
                    )

                if not jobs and "workdayjobs.com" in url:
                    jobs = await self._extract_workday_fallback(page, url, company_name, filters)

                if not jobs and "swissdevjobs.ch" in url.lower():
                    jobs = await self._extract_swissdevjobs_fallback(
                        page, url, company_name, filters
                    )

                if not jobs:
                    jobs = await self._extract_by_links(page, url, company_name, filters)

            except Exception as e:
                print(f"  [!] Scraper error for {company_name}: {e}")
            finally:
                await browser.close()

        return jobs

    @staticmethod
    async def _dismiss_cookie_banners(page: Page) -> None:
        for selector in _COOKIE_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                    break
            except PlaywrightError:
                pass

    @staticmethod
    async def _wait_for_content(page: Page, wait_for: str, company_name: str) -> None:
        selectors = [wait_for] + _WORKDAY_WAIT_SELECTORS
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=30_000)
                return
            except PlaywrightError:
                continue
        print(f"  [!] Content wait failed for {company_name} — attempting extraction anyway.")

    async def _extract_by_cards(
        self,
        page: Page,
        base_url: str,
        company_name: str,
        card_selector: str,
        title_selector: str,
        location_selector: str | None,
        company_selector: str | None,
        filters: dict,
    ) -> list[dict]:
        cards = await page.query_selector_all(card_selector)
        jobs: list[dict] = []

        for card in cards:
            title_el = await card.query_selector(title_selector)
            if not title_el:
                continue

            title_text = await title_el.inner_text()
            href = await title_el.get_attribute("href")
            if not title_text or not href:
                continue

            job_company = company_name
            if company_selector:
                comp_el = await card.query_selector(company_selector)
                if comp_el:
                    comp_text = await comp_el.inner_text()
                    if comp_text:
                        job_company = comp_text.strip().split("\n")[0]

            loc_text = "See URL"
            if location_selector:
                loc_el = await card.query_selector(location_selector)
                if loc_el:
                    loc_text = await loc_el.inner_text()

            title_text = title_text.strip().split("\n")[0]
            loc_text = loc_text.strip().replace("\n", ", ")

            if self.filter_job(title_text, filters):
                jobs.append({
                    "title": title_text,
                    "url": urljoin(base_url, href),
                    "company": job_company,
                    "location": loc_text,
                })

        return jobs

    async def _extract_workday_fallback(
        self, page: Page, base_url: str, company_name: str, filters: dict
    ) -> list[dict]:
        print(f"  [!] Primary selectors failed for Workday — attempting deep discovery fallback...")
        jobs: list[dict] = []
        links = await page.get_by_role("link").all()
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if text and href and "/job/" in href and self.filter_job(text, filters):
                jobs.append({
                    "title": text.strip().split("\n")[0],
                    "url": urljoin(base_url, href),
                    "company": company_name,
                    "location": "See URL",
                })
        return jobs

    async def _extract_swissdevjobs_fallback(
        self, page: Page, base_url: str, company_name: str, filters: dict
    ) -> list[dict]:
        print(f"  [!] Card extraction failed — using URL-based parsing for SwissDevJobs...")
        jobs: list[dict] = []
        links = await page.query_selector_all("a[href*='/jobs/']")
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if not text or not href:
                continue
            abs_url = urljoin(base_url, href)
            slug = href.split("/jobs/")[-1].split("?")[0]
            job_company = slug.split("-")[0].replace("+", " ").strip()
            if job_company.lower() in ("security", "senior", "lead"):
                job_company = company_name
            if self.filter_job(text, filters):
                jobs.append({
                    "title": text.strip().split("\n")[0],
                    "url": abs_url,
                    "company": job_company,
                    "location": "Switzerland",
                })
        return jobs

    async def _extract_by_links(
        self, page: Page, base_url: str, company_name: str, filters: dict
    ) -> list[dict]:
        jobs: list[dict] = []
        elements = await page.query_selector_all("a")
        for el in elements:
            title_text = await el.inner_text()
            href = await el.get_attribute("href")
            if title_text and href and self.filter_job(title_text, filters):
                jobs.append({
                    "title": title_text.strip().split("\n")[0],
                    "url": urljoin(base_url, href),
                    "company": company_name,
                    "location": "See URL",
                })
        return jobs
