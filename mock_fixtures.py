# tests/conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from terminal_formatter import MockTerminalFormatter as MockTF

@pytest.fixture
def mock_terminal_formatter():
    return MockTF

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_storyboard.return_value = {"description": "Test Story"}
    db.load_player_profile.return_value = {
        "core_traits": {"Curiosity": 7, "Empathy": 6},
        "decision_patterns": ["Seeks knowledge"],
        "key_experiences_tags": ["Met Lyra"],
        "interaction_style_summary": "Friendly and inquisitive"
    }
    db.load_inventory.return_value = [{"name": "Test Item", "quantity": 1}]
    db.get_player_credits.return_value = 100
    return db

@pytest.fixture
def mock_llm_wrapper():
    def mock_llm(messages, model_name, stream=False, collect_stats=True):
        return "Test response", {"total_tokens": 10, "completion_tokens": 5}
    return mock_llm