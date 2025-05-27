# tests/test_chat_manager.py
import pytest
from chat_manager import ChatSession, format_stats

def test_chat_session_initialization(mock_terminal_formatter):
    session = ChatSession(
        system_prompt="Test prompt",
        model_name="test-model"
    )
    assert session.get_system_prompt() == "Test prompt"
    assert session.get_model_name() == "test-model"
    assert len(session.messages) == 0

def test_add_message(mock_terminal_formatter):
    session = ChatSession(system_prompt="Test", model_name="test-model")
    
    # Test user message
    session.add_message("user", "Hello")
    assert len(session.messages) == 1
    assert session.messages[0]["role"] == "user"
    assert session.messages[0]["content"] == "Hello"
    
    # Test assistant message with stats
    session.add_message("assistant", "Hi", {"total_tokens": 10})
    assert len(session.messages) == 2
    assert session.messages[1]["role"] == "assistant"
    assert session.messages[1]["content"] == "Hi"
    assert session.last_stats == {"total_tokens": 10}

def test_clear_memory(mock_terminal_formatter):
    session = ChatSession(system_prompt="Test", model_name="test-model")
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
    assert "100 tokens" in formatted
    assert "1.5" in formatted