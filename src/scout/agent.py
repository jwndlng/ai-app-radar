"""Scout agent — extracts open job listings from a careers page."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from core.agent import BaseAgent


class JobListing(BaseModel):
    title: str = Field(default="", description="Job title as written on the page")
    url: str = Field(default="", description="Direct link to the job posting; empty if not available")
    location: str = Field(
        default="", description="Location or 'Remote' if remote; empty if not specified"
    )


class AgentReviewResponse(BaseModel):
    jobs: list[JobListing] = Field(
        default_factory=list, description="List of currently open roles"
    )
    next_page_url: str | None = Field(
        default=None,
        description=(
            "Full URL of the NEXT page of job results. "
            "Look in the '--- PAGE LINKS ---' section for links whose text matches (case-insensitive): "
            "'Next', 'Next page', 'next page', '>', '›', '→', 'siguiente', or a page number "
            "higher than the current page (e.g. current is page 1, look for link with text '2'). "
            "For Workday job boards (workdayjobs.com), pagination links often use aria-labels "
            "like 'next page' or numeric page numbers. "
            "Use the full href URL from that link exactly as written. "
            "Return null if no such link exists, if you are already on the last page, "
            "or if pagination only loads more jobs dynamically without a URL change."
        ),
    )


class ScoutAgent(BaseAgent[AgentReviewResponse]):
    def __init__(self, company_name: str, model: str | None = None) -> None:
        super().__init__(
            output_type=AgentReviewResponse,
            model_name=model or os.environ.get("SCOUT_MODEL"),
            agent_name=f"ScoutAgent({company_name})",
            system_prompt=ScoutAgent._build_instructions(company_name),
        )

    @staticmethod
    def _build_instructions(company_name: str) -> str:
        return (
            f"You are a job listing extractor for {company_name}'s careers page. "
            "The user will provide page content followed by a '--- PAGE LINKS ---' section "
            "listing all hyperlinks on the page.\n\n"
            "Your tasks:\n"
            "1. Extract all currently open job roles. Only include roles that are open "
            "(not closed, expired, or 'coming soon'). Return an empty jobs list if none found.\n"
            "2. Detect pagination. After extracting jobs, scan the PAGE LINKS section for a "
            "link to the NEXT page. Pagination links typically have text (case-insensitive) like: "
            "'Next', 'Next page', '>', '›', '→', or a page number greater than the current one. "
            "For Workday job boards, also look for aria-label text containing 'next'. "
            "If found, return its full URL in next_page_url. "
            "If you are on the last page or there is no next-page link, return null. "
            "Do NOT return 'Previous', 'Back', or current-page links."
        )

    @property
    def instructions(self) -> str:
        # Satisfies the BaseAgent ABC. The actual prompt is built via
        # _build_instructions() and injected through the system_prompt= param.
        return ScoutAgent._build_instructions(self.__class__.__name__)

    async def extract_jobs(self, page_content: str) -> AgentReviewResponse:
        result = await self.run(page_content)
        return result.output
