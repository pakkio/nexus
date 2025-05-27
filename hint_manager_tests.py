# tests/test_hint_manager.py
import pytest
from hint_manager import (
    generate_cache_key,
    summarize_conversation_for_lyra,
    build_initial_lyra_prompt
)

def test_generate_cache_key():
    state = {
        'player_id': 'test_player',
        'current_npc': {'code': 'TestNPC'},
        'chat_session': None,
        'db': None
    }
    key = generate_cache_key(state)
    assert isinstance(key, str)
    assert len(key) == 32  # MD5 hash length

def test_summarize_conversation_for_lyra(mock_llm_wrapper, mock_terminal_formatter):
    chat_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    
    summary = summarize_conversation_for_lyra(
        chat_history=chat_history,
        llm_wrapper_func=mock_llm_wrapper,
        model_name="test-model",
        TF=mock_terminal_formatter
    )
    
    assert isinstance(summary, str)
    assert summary == "Test response"

def test_build_initial_lyra_prompt(mock_terminal_formatter):
    summary = "Test conversation summary"
    player_data = {
        "player_id": "TestPlayer",
        "current_area": "TestArea"
    }
    player_profile = {
        "core_traits": {"Curiosity": 7},
        "decision_patterns": ["Seeks knowledge"],
        "key_experiences_tags": ["Met Lyra"],
        "interaction_style_summary": "Friendly"
    }
    stashed_npc_data = {
        "name": "TestNPC",
        "area": "TestArea",
        "role": "Guide"
    }
    story_context = "The Shattered Veil"
    
    prompt = build_initial_lyra_prompt(
        summary=summary,
        player_data=player_data,
        player_profile=player_profile,
        stashed_npc_data=stashed_npc_data,
        TF=mock_terminal_formatter,
        story_context=story_context
    )
    
    assert isinstance(prompt, str)
    assert "TestPlayer" in prompt
    assert "TestArea" in prompt
    assert "TestNPC" in prompt
    assert "The Shattered Veil" in prompt