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
