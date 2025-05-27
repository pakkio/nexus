# chat_manager_tests.py
import pytest
from chat_manager import ChatSession, format_stats

def test_chat_session_initialization(mock_terminal_formatter):
    # Initialize ChatSession with only model_name
    session = ChatSession(model_name="test-model")
    # Set system prompt after initialization
    session.set_system_prompt("Test prompt")

    assert session.get_system_prompt() == "Test prompt"
    assert session.get_model_name() == "test-model"
    assert len(session.messages) == 0
def test_add_message(mock_terminal_formatter):
    # Initialize ChatSession without system_prompt
    session = ChatSession(model_name="test-model")
    # Set system prompt after initialization
    session.set_system_prompt("Test")

    # Test user message
    session.add_message("user", "Hello")
    assert len(session.messages) == 1
    assert session.messages[0]["role"] == "user"
    assert session.messages[0]["content"] == "Hello"

    # Test assistant message without stats
    session.add_message("assistant", "Hi")
    assert len(session.messages) == 2
    assert session.messages[1]["role"] == "assistant"
    assert session.messages[1]["content"] == "Hi"

    # Optionally set last_stats manually if needed to test that functionality
    session.last_stats = {"total_tokens": 10}
    assert session.last_stats == {"total_tokens": 10}


def test_clear_memory(mock_terminal_formatter):
    # Initialize ChatSession without system_prompt
    session = ChatSession(model_name="test-model")
    # Set system prompt after initialization
    session.set_system_prompt("Test")
    session.add_message("user", "Test message")
    session.clear_memory()
    assert len(session.messages) == 0

def test_format_stats():
    stats = {
        "total_tokens": 100,
        "completion_tokens": 50,
        "prompt_tokens": 50,
        "total_time": 1.5
    }
    formatted = format_stats(stats)

    # Just check for the presence of the "100" value
    assert "100" in formatted
    # Check for time value
    assert "1.5" in formatted or "1.50" in formatted
