from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_areas(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    _add_profile_action(state, "Used /areas command")
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    if not known_areas:
        print(f"{TF.YELLOW}No known areas found.{TF.RESET}")
    else:
        print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Available Areas to /go to:{TF.RESET}")
        for area_name in known_areas:
            print(f" {TF.CYAN}➢ {area_name}{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}