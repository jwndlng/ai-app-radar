import pytest
from pathlib import Path
import yaml

@pytest.fixture
def mock_filters():
    return {
        "positive": ["Security", "Python"],
        "negative": ["Junior", ".NET"]
    }

@pytest.fixture
def temp_workspace(tmp_path):
    # Create applications directory
    app_dir = tmp_path / "applications"
    app_dir.mkdir()
    
    # Create scout history path
    history_dir = tmp_path / "flows" / "scout"
    history_dir.mkdir(parents=True)
    
    return tmp_path
