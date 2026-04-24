"""TuneJudge — Sonnet-based agent that compares scout results across models."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from core.agent import BaseAgent


class JudgeResult(BaseModel):
    consensus_count: int = Field(
        description="Number of job titles found by 2 or more models (fuzzy match)."
    )
    model_unique: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Jobs found by only one model. Keys are model names, values are title lists.",
    )
    url_missing: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Jobs with no URL per model. Keys are model names, values are title lists. "
            "A high count indicates the model extracted titles without anchoring them to links — "
            "a strong hallucination signal."
        ),
    )
    pagination_analysis: dict[str, int] = Field(
        default_factory=dict,
        description="Pages visited per model. Keys are model names, values are page counts.",
    )
    summary: str = Field(
        description=(
            "2-4 sentence plain-English analysis: which model found the most jobs, "
            "where pagination dropped off, and any suspected hallucinations."
        )
    )


class TuneJudge(BaseAgent[JudgeResult]):
    _JUDGE_MODEL = "claude-sonnet-4-6"

    def __init__(self) -> None:
        super().__init__(output_type=JudgeResult, model_name=self._JUDGE_MODEL)

    @property
    def instructions(self) -> str:
        return (
            "You are a scout tuning judge. You receive job extraction results from multiple LLMs "
            "that all scraped the same careers page. Your job is to compare their outputs.\n\n"
            "Use fuzzy title matching (ignore minor differences in capitalization, punctuation, "
            "or word order) to identify:\n"
            "1. **Consensus jobs** — titles found by 2 or more models. Count them.\n"
            "2. **Model-unique jobs** — titles found by exactly one model. List them per model. "
            "Flag any that look like hallucinations (vague, generic, or improbable titles).\n"
            "3. **URL-missing jobs** — jobs where the `url` field is empty or absent. List them "
            "per model. A title with no URL means the model extracted a name without finding the "
            "link — treat these as likely hallucinations or extraction failures.\n"
            "4. **Pagination accuracy** — record how many pages each model visited. Note where "
            "a model stopped paginating earlier than others and why (missed next-page link, "
            "wrong URL, returned null prematurely).\n\n"
            "Be concise. Your summary should highlight the most actionable finding, "
            "prioritising URL-missing titles as a scout quality signal."
        )

    async def judge(self, results: list[dict]) -> JudgeResult:
        prompt = json.dumps(results, indent=2)
        output = await self.run(prompt)
        return output.output
