from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from scout.providers.greenhouse import GreenhouseProvider


def _fake_response(jobs: list[dict]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"jobs": jobs}
    return response


@pytest.mark.asyncio
async def test_uses_absolute_url_when_careers_url_is_a_proxy_front_end() -> None:
    """Domino's careers_url (domino.ai/careers) is a CareerPuck-skinned marketing page,
    not the Greenhouse-hosted board itself — constructing a URL from it produces a dead
    link. Greenhouse's absolute_url is always authoritative and must take priority."""
    provider = GreenhouseProvider()
    provider._get = AsyncMock(return_value=_fake_response([
        {
            "title": "AI/ML Platform Engineer",
            "id": 7774037,
            "absolute_url": "https://app.careerpuck.com/job-board/domino-data-lab/job/7774037?gh_jid=7774037",
            "location": {"name": "Remote"},
        }
    ]))

    company_config = {
        "name": "Domino",
        "careers_url": "https://domino.ai/careers",
        "scan_method_config": {"api_base": "https://boards-api.greenhouse.io/v1/boards/dominodatalab/jobs"},
    }
    jobs = await provider.scout(company_config, filters={"positive": ["Engineer"], "negative": []})

    assert len(jobs) == 1
    assert jobs[0]["url"] == "https://app.careerpuck.com/job-board/domino-data-lab/job/7774037?gh_jid=7774037"


@pytest.mark.asyncio
async def test_falls_back_to_constructed_url_when_absolute_url_missing() -> None:
    provider = GreenhouseProvider()
    provider._get = AsyncMock(return_value=_fake_response([
        {"title": "Backend Engineer", "id": 123, "location": {"name": "Remote"}}
    ]))

    company_config = {
        "name": "Acme",
        "careers_url": "https://job-boards.greenhouse.io/acme",
        "scan_method_config": {"api_base": "https://boards-api.greenhouse.io/v1/boards/acme/jobs"},
    }
    jobs = await provider.scout(company_config, filters={"positive": ["Engineer"], "negative": []})

    assert jobs[0]["url"] == "https://job-boards.greenhouse.io/acme/jobs/123"
