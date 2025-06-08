from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action
from llm_stats_tracker import get_global_stats_tracker

def handle_all_stats(state: Dict[str, Any]) -> HandlerResult:
    """Show comprehensive statistics for all LLM types"""
    _add_profile_action(state, "Used /all_stats command")
    TF = state['TerminalFormatter']
    
    stats_tracker = get_global_stats_tracker()
    
    print(f"\n{TF.BOLD}{TF.CYAN}📊 Comprehensive LLM Statistics{TF.RESET}")
    print(f"{TF.CYAN}{'='*50}{TF.RESET}")
    
    # Overall status indicators
    print(f"\n{TF.BOLD}🔍 LLM Status Overview:{TF.RESET}")
    print(f"{stats_tracker.get_status_indicators()}")
    
    # Overall session stats
    print(f"\n{TF.BOLD}📈 Overall Session Statistics:{TF.RESET}")
    print(stats_tracker.format_session_stats())
    
    # Individual LLM type breakdowns
    for model_type in ['dialogue', 'profile', 'guide_selection', 'command_interpretation']:
        if model_type in stats_tracker.type_stats:
            type_stats = stats_tracker.type_stats[model_type]
            if type_stats.total_calls > 0:
                emoji = stats_tracker._get_type_emoji(model_type)
                print(f"\n{TF.BOLD}{emoji} {model_type.title()} LLM Details:{TF.RESET}")
                print(stats_tracker.format_session_stats(model_type))
                
                # Show last call stats if available
                last_stats = stats_tracker.get_last_stats_by_type(model_type)
                if last_stats:
                    print(f"\n{TF.DIM}Last {model_type.title()} Call:{TF.RESET}")
                    print(stats_tracker.format_last_stats(model_type))
    
    return {**state, 'status': 'ok', 'continue_loop': True}