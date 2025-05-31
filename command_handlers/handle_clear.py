from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /clear command")
    TF = state['TerminalFormatter']
    session = state.get('chat_session')
    if not session:
        print(f"{TF.YELLOW}Not in an active chat to clear.{TF.RESET}")
    else:
        session.clear_memory()
        npc_name = state.get('current_npc', {}).get('name', 'current')
        mode_info = "(Lyra Consultation)" if state.get('in_lyra_hint_mode') else ""
        print(f"{TF.YELLOW}Conversation memory with {npc_name} {mode_info} has been cleared (in this session only).{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}