from typing import Dict, Any
from ..command_handler_utils import HandlerResult, _add_profile_action

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /stats command")
    TF = state['TerminalFormatter']
    session = state.get('chat_session')
    npc = state.get('current_npc') # Corrected: current_npc, was curre_npc
    fmt_stats = state['format_stats'] # Get the formatting function from state

    if not session or not npc: # Check both npc and session exist
        print(f"{TF.YELLOW}Not in an active chat session to show stats for.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    ls = session.get_last_stats()
    npc_name_for_stats = npc.get('name', 'Current NPC')

    # Handle Lyra consultation mode naming

    if state.get('in_lyra_hint_mode') and npc_name_for_stats.lower() == 'lyra': # Ensure Lyra's name is checked case-insensitively
        npc_name_for_stats = "Lyra (Consultation)"

    if ls:
        print(f"\n{TF.DIM}{'-'*15}Last Turn Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
        print(fmt_stats(ls)) # Use the passed formatting function
    else:
        print(f"{TF.YELLOW}No last turn stats available for {npc_name_for_stats}.{TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}