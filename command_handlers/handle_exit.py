from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action
from .handle_endhint import handle_endhint # For internal call

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    player_id = state['player_id']

    if state.get('in_lyra_hint_mode'):
        print(f"\n{TF.DIM}Exiting Lyra consultation mode before quitting...{TF.RESET}")
        state = handle_endhint(state) # Call handle_endhint directly

    print(f"\n{TF.DIM}Saving last active conversation (if any)...{TF.RESET}")
    session_utils.save_current_conversation(
        state['db'], player_id, state.get('current_npc'), state.get('chat_session'), TF
    )

    # Player state and profile are saved in the main loop's finally block or after exit status.
    # No need to explicitly save them here again unless it's a hard crash scenario.

    print(f"{TF.YELLOW}Arrivederci! Leaving Eldoria... for now.{TF.RESET}")
    _add_profile_action(state, "Used /exit command")
    return {**state, 'status': 'exit'}