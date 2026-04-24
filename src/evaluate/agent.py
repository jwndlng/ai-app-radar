"""Evaluate agent — scores candidate fit against an enriched job record."""

from __future__ import annotations

import json
import os

from pydantic import BaseModel, Field

from core.agent import BaseAgent


class FitResult(BaseModel):
    score: float = Field(
        description=(
            "Candidate fit score on a 0.1–10.0 scale. "
            "10 = perfect match, 1 = no meaningful overlap."
        )
    )
    archetype: str = Field(
        default="",
        description="Concise role archetype label derived from the job's actual domain and level.",
    )
    location_score: float = Field(
        description=(
            "How feasible is it for the candidate to work this role? "
            "Cross-reference BOTH `remote_policy` AND `location` against the candidate's "
            "`location_preferences.accepted` list from the CANDIDATE PROFILE. "
            "remote_policy alone is never sufficient — always check location too. "
            "Apply these rules strictly:\n"
            "9–10: on-site in an accepted location, OR remote explicitly covering the "
            "candidate's accepted regions with no country restriction.\n"
            "7–8: fully remote with no geo qualifier, and location shows no offices "
            "outside accepted locations.\n"
            "5–6: remote claimed but location shows offices only outside accepted "
            "locations — may impose residency or timezone constraints.\n"
            "4–6: hybrid AND at least one office is in an accepted location.\n"
            "MAXIMUM 2: hybrid or on-site with offices ONLY outside accepted locations "
            "(candidate cannot commute), or remote explicitly restricted to regions "
            "that exclude the candidate's accepted locations. "
            "This ceiling is STRICT — do NOT exceed 2 for this case, regardless of other factors."
        )
    )
    location_reason: str = Field(
        default="",
        description=(
            "One sentence: which rule you applied and what signal drove it. "
            "Name the specific location/policy found and how it compares to the "
            "candidate's accepted locations."
        ),
    )
    seniority_score: float = Field(
        description=(
            "How well does the role's seniority match the candidate's target level "
            "from the CANDIDATE PROFILE? Score 0.1–10.0. "
            "9–10 = exact match to the candidate's target seniority. "
            "5–7 = neutral title with no explicit level, or one level adjacent. "
            "1–4 = clear mismatch (too junior, graduate role, or far above experience)."
        )
    )
    seniority_reason: str = Field(
        default="",
        description="One sentence explaining the seniority_score.",
    )
    compensation_score: float = Field(
        description=(
            "How well does salary_range match the candidate's compensation targets? "
            "Score 0.1–10.0. "
            "9–10 = meets or exceeds target_range. "
            "6–8 = meets minimum but below target. "
            "3–5 = below minimum or not stated. "
            "1–2 = clearly below minimum."
        )
    )
    compensation_reason: str = Field(
        default="",
        description="One sentence explaining the compensation_score.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description=(
            "3–5 concise bullet points explaining the fit score. "
            "Reference specific skills, domains, or signals that drove the result. "
            "Include both positive matches and notable gaps."
        ),
    )


class FitScoringAgent(BaseAgent[FitResult]):
    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            output_type=FitResult,
            model_name=model or os.environ.get("EVALUATE_MODEL"),
        )

    @property
    def instructions(self) -> str:
        return (
            "You are a Senior Technical Recruiter scoring candidate-job fit. "
            "Given the candidate profile and enriched job data provided by the user, "
            "produce a fit score and brief explanation.\n\n"
            "Scoring guidance (0.1–10.0 scale):\n"
            "- PRIMARY (`score`): Overlap between the job's `tech_stack` and the candidate's "
            "`super_power` or `strong` skills. Strong overlap raises the score significantly.\n"
            "- SECONDARY (`score`): Overlap between the job's `domains` and the candidate's "
            "high-weight `mission_domains`.\n"
            "- MINOR NEGATIVE (`score`): seniority mismatch (e.g. junior or IC1 role title).\n"
            "- NEUTRAL (`score`): `low` tier skills matching is not a boost.\n"
            "- `location_score` — check BOTH `remote_policy` AND `location` fields together. "
            "Derive accepted locations from `location_preferences.accepted` in the CANDIDATE PROFILE:\n"
            "  • Remote explicitly covering the candidate's accepted regions (no country list) → 9.\n"
            "  • Fully remote, no qualifier, no offices outside accepted locations → 8.\n"
            "  • Remote but location shows offices only outside accepted locations → 5–6 "
            "(residency/timezone risk).\n"
            "  • Remote + specific countries listed: 8 if an accepted location is in the list, 2 if not.\n"
            "  • Hybrid AND at least one office in an accepted location → 4–6.\n"
            "  • Hybrid or on-site with offices ONLY outside accepted locations → MUST be 1–2.\n"
            "  • On-site in an accepted location → 9–10; outside accepted locations → MUST be 1–2.\n"
            "  Always write `location_reason` naming the specific policy/location found.\n"
            "- `seniority_score`: compare role title/level to the candidate's target seniority "
            "from the profile. Write `seniority_reason`.\n"
            "- `compensation_score`: compare `salary_range` to the candidate's "
            "`compensation.minimum` / `target_range` from the profile. Score 5 if not stated. "
            "Write `compensation_reason`.\n"
            "- Be precise and factual. Do not invent information — only score what is "
            "explicitly in the job data."
        )

    async def score(self, job: dict, profile_input: dict) -> FitResult:
        profile_str = json.dumps(profile_input, indent=2)
        job_fields = [
            "title", "company", "location", "remote_policy", "salary_range",
            "description", "focus_areas", "key_responsibilities",
            "required_qualifications", "tech_stack", "domains",
        ]
        job_str = json.dumps(
            {k: job.get(k) for k in job_fields},
            indent=2,
        )
        prompt = f"CANDIDATE PROFILE:\n{profile_str}\n\nJOB DATA:\n{job_str}"
        result = await self.run(prompt)
        return result.output
