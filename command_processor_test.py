import pytest
from unittest.mock import Mock, MagicMock, patch

# Import from the new locations

from command_handler_utils import HandlerResult, _add_profile_action # Assuming this is directly in the root or PYTHONPATH
from command_handlers.handle_exit import handle_exit
from command_handlers.handle_whereami import handle_whereami
# process_input_revised is still the main entry point for commands from user input
from command_processor import process_input_revised

# Mock fixtures (can be moved to a conftest.py later if many test files need them)

@pytest.fixture
def mock_terminal_formatter_fixt(): # Renamed to avoid conflict if already defined elsewhere
    class MockTF:
        RED = YELLOW = GREEN = RESET = BOLD = DIM = ITALIC = ""
        MAGENTA = CYAN = BRIGHT_CYAN = BG_BLUE = ""
        BRIGHT_WHITE = BG_GREEN = BLACK = ""
        @staticmethod
        def format_terminal_text(text, width=80): return text
        @staticmethod
        def get_terminal_width(): return 80 # Added for handle_profile_for_npc
    return MockTF() # Return instance

def test_add_profile_action_util(): # Test the utility function directly
    state = {}
    _add_profile_action(state, "Test action") # Call the imported function
    assert 'actions_this_turn_for_profile' in state
    assert state['actions_this_turn_for_profile'] == ["Test action"]
    _add_profile_action(state, "Second action")
    assert len(state['actions_this_turn_for_profile']) == 2
    assert "Second action" in state['actions_this_turn_for_profile']

def test_handle_exit_handler(mock_terminal_formatter_fixt): # Test the specific handler
    state = {
        'TerminalFormatter': mock_terminal_formatter_fixt,
        'player_id': 'test_player',
        'db': MagicMock(),
        'chat_session': None,
        'current_npc': None,
        'in_lyra_hint_mode': False # Added for completeness
    }

    # Patch handle_endhint if it's complex or makes external calls you don't want in this unit test
    # The target for patch should be where handle_exit looks for handle_endhint.
    # Since handle_exit.py does "from .handle_endhint import handle_endhint",
    # the path is 'command_handlers.handle_exit.handle_endhint'
    with patch('command_handlers.handle_exit.handle_endhint', return_value=state) as mock_endhint:
        result = handle_exit(state) # Call the imported handler
        assert result['status'] == 'exit'
        # _add_profile_action is called inside handle_exit
        assert any("exit" in action.lower() for action in result.get('actions_this_turn_for_profile', []))
        if state.get('in_lyra_hint_mode'): # Test conditional call
            mock_endhint.assert_called_once_with(state)
        else:
            mock_endhint.assert_not_called()


def test_handle_whereami_handler(mock_terminal_formatter_fixt): # Test specific handler
    # Mock session_utils.get_npc_color as it might be called by whereami
    with patch('command_handlers.handle_whereami.session_utils.get_npc_color', return_value="COLOR_CODE"):
        state = {
            'TerminalFormatter': mock_terminal_formatter_fixt,
            'current_area': 'Test Area',
            'current_npc': None,
            'chat_session': None, # Added for completeness for hint logic
            'in_lyra_hint_mode': False,
            'player_id': 'test_player' # Added as _add_profile_action might be called
        }
        result = handle_whereami(state) # Call the imported handler
        assert result['status'] == 'ok'
        assert result['continue_loop'] is True
        assert any("whereami" in action.lower() for action in result.get('actions_this_turn_for_profile', []))

def test_process_input_revised_command_dispatch(mock_terminal_formatter_fixt):
    # This test verifies that process_input_revised correctly dispatches to a handler
    state = {
        'TerminalFormatter': mock_terminal_formatter_fixt,
        'chat_session': None, 'current_npc': None,
        'format_stats': lambda x: "Stats formatted",
        'in_lyra_hint_mode': False,
        'debug_mode': False,
        'player_id': 'test_player',
        'db': MagicMock(),
        'story': "Test story"
        # ... other necessary state keys for help handler ...
    }

    # The patch target should be where process_input_revised looks for it in its command_handlers_map
    # If command_processor.py does from .command_handlers import handle_help
    # and map is {'help': handle_help}, then patch 'command_processor.handle_help'
    # (assuming command_processor.py is in the same directory as command_processor_test.py or in PYTHONPATH)
    with patch('command_processor.handle_help', return_value={'status': 'ok', 'continue_loop': True, 'actions_this_turn_for_profile':[]}) as mock_help_handler:
        result_state = process_input_revised("/help", state)
        mock_help_handler.assert_called_once()
        # The state passed to the handler should be the one from process_input_revised
        # We can't easily assert the exact state object due to mocks, but ensure it was called with a state-like object.
        passed_state_to_handler = mock_help_handler.call_args[0][0]
        assert 'TerminalFormatter' in passed_state_to_handler
        assert 'player_id' in passed_state_to_handler

def test_process_input_revised_dialogue_to_llm(mock_terminal_formatter_fixt):
    # This tests the LLM call path
    mock_session_instance = MagicMock()
    mock_session_instance.ask.return_value = ("NPC response", {"total_tokens": 10})
    mock_session_instance.get_history.return_value = [{"role": "user", "content": "Hello NPC"}, {"role": "assistant", "content": "NPC response"}]

    # Note: ChatSession is not directly patched here as it's assumed to be part of `state['chat_session']`
    state = {
        'TerminalFormatter': mock_terminal_formatter_fixt,
        'chat_session': mock_session_instance, # Use the instance here
        'current_npc': {'name': 'Test NPC', 'code': 'test_npc'}, # Ensure NPC has a code
        'format_stats': lambda x: "Stats formatted",
        'in_lyra_hint_mode': False,
        'debug_mode': False,
        'use_stream': True,
        'auto_show_stats': False,
        'player_id': 'test_player',
        'db': MagicMock(),
        'story': "Test Story",
        'llm_wrapper_func': MagicMock(),
        # For the problematic time.time() call in command_processor for Lyra cache update
        'lyra_hint_cache': None # Set to None for non-Lyra case, or mock if testing Lyra path
    }
    # Patch get_npc_color where it's used by process_input_revised (via session_utils)
    with patch('command_processor.session_utils.get_npc_color', return_value=mock_terminal_formatter_fixt.GREEN):
        # Also patch time.time() if that problematic line is hit
        with patch('command_processor.time.time', return_value=1234567890.0):
            result_state = process_input_revised("Hello NPC", state)

    mock_session_instance.ask.assert_called_once_with(
        "Hello NPC",
        "Test NPC", # Name for placeholder
        True, # stream
        True # collect_stats
    )
    assert result_state['npc_made_new_response_this_turn'] is True
    # _add_profile_action is called twice for dialogue: once for user input, once for NPC response
    profile_actions = result_state.get('actions_this_turn_for_profile', [])
    assert len(profile_actions) > 0 # Check that actions were added
    assert any("npc response from test npc" in action.lower() for action in profile_actions)