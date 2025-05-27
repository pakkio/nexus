# tests/test_command_processor.py
import pytest
from unittest.mock import Mock, MagicMock, patch
import command_processor
from command_processor import (
    handle_exit, handle_help, handle_who, handle_whereami,
    handle_npcs, handle_areas, handle_profile, handle_stats,
    handle_go, handle_talk, handle_clear, handle_hint, handle_endhint,
    process_input_revised
)

# Test the utility function for adding profile actions
def test_add_profile_action():
    # Create a simple state dictionary
    state = {}

    # Call the internal function to add an action
    command_processor._add_profile_action(state, "Test action")

    # Verify the action was added to the state
    assert 'actions_this_turn_for_profile' in state
    assert state['actions_this_turn_for_profile'] == ["Test action"]

    # Add another action and verify it appends
    command_processor._add_profile_action(state, "Second action")
    assert len(state['actions_this_turn_for_profile']) == 2
    assert "Second action" in state['actions_this_turn_for_profile']

# Test some basic command handlers
def test_handle_exit(mock_terminal_formatter):
    # Setup a minimal state
    state = {
        'TerminalFormatter': mock_terminal_formatter(),
        'player_id': 'test_player',
        'db': MagicMock(),
        'chat_session': None,
        'current_npc': None
    }

    # Call the exit handler
    result = handle_exit(state)

    # Verify it returns the right status
    assert result['status'] == 'exit'
    # Check that the profile action was added
    assert any("exit" in action.lower() for action in result.get('actions_this_turn_for_profile', []))

def test_handle_whereami(mock_terminal_formatter):
    # Setup state with current area
    state = {
        'TerminalFormatter': mock_terminal_formatter(),
        'current_area': 'Test Area',
        'current_npc': None
    }

    # Call the handler
    result = handle_whereami(state)

    # Check status and continue flag
    assert result['status'] == 'ok'
    assert result['continue_loop'] is True
    # Verify profile action was added
    assert any("whereami" in action.lower() for action in result.get('actions_this_turn_for_profile', []))

def test_process_input_revised_command(mock_terminal_formatter):
    # Setup a state dictionary with mocked dependencies
    state = {
        'TerminalFormatter': mock_terminal_formatter(),
        'chat_session': None,
        'current_npc': None,
        'format_stats': lambda x: "Stats formatted",
        'in_lyra_hint_mode': False
    }

    # Mock the handle_help function to verify it's called
    with patch('command_processor.handle_help', return_value={'status': 'ok', 'continue_loop': True}) as mock_help:
        # Process a help command
        result = process_input_revised("/help", state)

        # Verify handle_help was called with the right state
        mock_help.assert_called_once_with(state)

def test_process_input_revised_dialogue(mock_terminal_formatter):
    # Create mocks
    mock_session = MagicMock()
    mock_session.ask.return_value = ("NPC response", {"total_tokens": 10})

    # Setup state with chat session and NPC
    state = {
        'TerminalFormatter': mock_terminal_formatter(),
        'chat_session': mock_session,
        'current_npc': {'name': 'Test NPC'},
        'format_stats': lambda x: "Stats formatted",
        'in_lyra_hint_mode': False,
        'use_stream': True,
        'auto_show_stats': False
    }

    # Process dialogue input
    result = process_input_revised("Hello NPC", state)

    # Verify chat_session.ask was called with the right parameters
    mock_session.ask.assert_called_once_with(
        "Hello NPC",
        "Test NPC",
        True,
        True
    )

    # Check that the state indicates NPC made a response
    assert result['npc_made_new_response_this_turn'] is True

    # Check that dialogue was added to profile actions
    assert any("said to npc" in action.lower() for action in result.get('actions_this_turn_for_profile', []))
