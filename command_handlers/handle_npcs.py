from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    _add_profile_action(state, "Used /npcs command")

    try:
        # Similar to handle_help, assumes main_utils is accessible.
        from main_utils import format_npcs_list
        all_npcs = session_utils.refresh_known_npcs_list(db, TF) # Get fresh list
        if not all_npcs:
            print(f"{TF.YELLOW}No NPC data could be loaded.{TF.RESET}")
        else:
            print(format_npcs_list(all_npcs))
    except ImportError:
        print(f"{TF.RED}Error: main_utils.format_npcs_list utility missing.{TF.RESET}")
        # Fallback basic list if formatter is missing
        all_npcs_fallback = session_utils.refresh_known_npcs_list(db, TF)
        if all_npcs_fallback:
            print(f"\n{TF.YELLOW}{TF.BOLD}Known NPCs (basic list):{TF.RESET}")
            for npc_info in sorted(all_npcs_fallback, key=lambda x: (x.get('area','').lower(), x.get('name','').lower())):
                print(f" {TF.DIM}- {npc_info.get('name','???')} in {npc_info.get('area','???')} ({npc_info.get('role','???')}){TF.RESET}")
        else:
            print(f"{TF.YELLOW}No NPC data could be loaded (fallback).{TF.RESET}")
    except Exception as e:
        print(f"{TF.RED}Error fetching or displaying NPCs: {e}{TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}