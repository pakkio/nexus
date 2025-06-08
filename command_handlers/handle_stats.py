from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action
from llm_stats_tracker import get_global_stats_tracker

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /stats command")
    TF = state['TerminalFormatter']
    session = state.get('chat_session')
    npc = state.get('current_npc')
    fmt_stats = state['format_stats']
    
    # Get global stats tracker
    stats_tracker = get_global_stats_tracker()

    if not session or not npc:
        print(f"{TF.YELLOW}Not in an active chat session to show stats for.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    npc_name_for_stats = npc.get('name', 'Current NPC')
    
    # Handle hint mode naming
    if state.get('in_hint_mode') and npc_name_for_stats.lower() == state.get('wise_guide_npc_name', 'lyra').lower():
        npc_name_for_stats = f"{npc_name_for_stats} (Consultation)"

    # Show dialogue stats (current session)
    ls = session.get_last_stats()
    if ls:
        print(f"\n{TF.DIM}{'-'*15}Last Turn Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
        print(fmt_stats(ls, "dialogue"))
    else:
        print(f"{TF.YELLOW}No last turn stats available for {npc_name_for_stats}.{TF.RESET}")
    
    # Show status indicators for all LLM types
    print(f"\n{TF.DIM}{'-'*15}LLM Status Overview{'-'*15}{TF.RESET}")
    print(f"{TF.BOLD}Status:{TF.RESET} {stats_tracker.get_status_indicators()}")

    return {**state, 'status': 'ok', 'continue_loop': True}