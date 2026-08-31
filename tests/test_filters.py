import pytest
from scout.providers.base import BaseProvider

class MockProvider(BaseProvider):
    def scout(self, company_config, filters):
        return []

@pytest.fixture
def provider():
    return MockProvider()

def test_filter_job_positive_match(provider, mock_filters):
    # Should match "Security"
    assert provider.filter_job("Security Engineer", mock_filters) is True
    # Should match "Python"
    assert provider.filter_job("Python Backend Developer", mock_filters) is True

def test_filter_job_negative_exclusion(provider, mock_filters):
    # Should exclude "Junior"
    assert provider.filter_job("Junior Security Engineer", mock_filters) is False
    # Should exclude ".NET"
    assert provider.filter_job("Security Engineer (.NET)", mock_filters) is False

def test_filter_job_no_match(provider, mock_filters):
    assert provider.filter_job("Frontend Developer", mock_filters) is False

def test_filter_job_case_insensitivity(provider, mock_filters):
    assert provider.filter_job("security engineer", mock_filters) is True


def test_filter_job_empty_positive_accepts_all(provider):
    # No positive filters configured means "accept everything"; a missing
    # scout_filters section must not silently reject every job.
    assert provider.filter_job("Frontend Developer", {}) is True
    assert provider.filter_job("Anything At All", {"positive": []}) is True


def test_filter_job_empty_positive_still_applies_negatives(provider):
    filters = {"positive": [], "negative": ["Junior"]}
    assert provider.filter_job("Junior Engineer", filters) is False
    assert provider.filter_job("Staff Engineer", filters) is True


def test_filter_job_ignores_empty_terms(provider):
    filters = {"positive": ["Security", ""], "negative": [""]}
    assert provider.filter_job("Security Engineer", filters) is True
