from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /session_stats command")
    TF = state['TerminalFormatter']
    session = state.get('chat_session')
    npc = state.get('current_npc') # Corrected: current_npc

    if not session or not npc: # Check both session and npc
        print(f"{TF.YELLOW}Not in an active chat session.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    npc_name_for_stats = npc.get('name', 'Current NPC')
    if state.get('in_lyra_hint_mode') and npc_name_for_stats.lower() == 'lyra': # Ensure Lyra's name is checked case-insensitively
        npc_name_for_stats = "Lyra (Consultation)"

    print(f"\n{TF.DIM}{'-'*15}Session Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
    print(session.format_session_stats()) # Assumes chat_session has this method

    return {**state, 'status': 'ok', 'continue_loop': True}