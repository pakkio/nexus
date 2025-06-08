from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action
from llm_stats_tracker import get_global_stats_tracker

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /session_stats command")
    TF = state['TerminalFormatter']
    session = state.get('chat_session')
    npc = state.get('current_npc')
    
    # Get global stats tracker
    stats_tracker = get_global_stats_tracker()

    if not session or not npc:
        print(f"{TF.YELLOW}Not in an active chat session.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    npc_name_for_stats = npc.get('name', 'Current NPC')
    if state.get('in_hint_mode') and npc_name_for_stats.lower() == state.get('wise_guide_npc_name', 'lyra').lower():
        npc_name_for_stats = f"{npc_name_for_stats} (Consultation)"

    # Show current dialogue session stats
    print(f"\n{TF.DIM}{'-'*15}Current Session Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
    print(session.format_session_stats())
    
    # Show comprehensive stats for all LLM types
    print(f"\n{TF.DIM}{'-'*15}All LLM Types - Session Overview{'-'*15}{TF.RESET}")
    print(stats_tracker.format_session_stats())

    return {**state, 'status': 'ok', 'continue_loop': True}