# tests/test_main_utils.py
import pytest
from main_utils import (
    format_storyboard_for_prompt,
    format_npcs_list,
    get_help_text
)

def test_format_storyboard_for_prompt():
    # Test normal case
    assert format_storyboard_for_prompt("Test story") == "Test story"
    
    # Test truncation
    long_story = "x" * 400
    result = format_storyboard_for_prompt(long_story, max_length=300)
    assert len(result) == 303
    assert result.endswith("...")
    
    # Test invalid input
    assert format_storyboard_for_prompt(None) == "[No Story]"
    assert format_storyboard_for_prompt(123) == "[No Story]"

def test_format_npcs_list(mock_terminal_formatter):
    # Test empty list
    result = format_npcs_list([])
    assert "No NPCs found" in result
    
    # Test single NPC
    npcs = [{
        "name": "TestNPC",
        "area": "TestArea",
        "role": "TestRole"
    }]
    result = format_npcs_list(npcs)
    assert "TestNPC" in result
    assert "TestArea" in result
    assert "TestRole" in result

def test_get_help_text(mock_terminal_formatter):
    help_text = get_help_text()
    essential_commands = [
        "/exit", "/help", "/go", "/talk",
        "/hint", "/inventory", "/profile"
    ]
    for cmd in essential_commands:
        assert cmd in help_text