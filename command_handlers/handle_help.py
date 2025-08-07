from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_help(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    try:
        # Assuming main_utils is in a place accessible by Python's import system
        # If main_utils is at the same level as command_processor.py, and command_handlers is a subdir,
        # then relative import from command_handlers might be tricky without __init__.py structure and package setup.
        # For now, direct import is assumed to work if main_utils is in PYTHONPATH or same top-level dir.
        from main_utils import get_help_text # This might need adjustment based on project structure
        print(get_help_text())
    except ImportError:
        print(f"{TF.RED}Error: Help utility (main_utils.get_help_text) not found.{TF.RESET}")
        print("Basic commands: /exit, /go, /areas, /describe, /talk, /who, /whereami, /npcs, /hint, /endhint, /inventory, /give, /stats, /clear, /history, /profile, /profile_for_npc")
    _add_profile_action(state, "Used /help command")
    return {**state, 'status': 'ok', 'continue_loop': True}