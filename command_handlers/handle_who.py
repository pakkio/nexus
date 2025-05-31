from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_who(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    _add_profile_action(state, "Used /who command")

    current_display_area = state.get('current_area') # Default to physical area

    if state.get('in_lyra_hint_mode'):
        stashed_npc_data = state.get('stashed_npc', {}) # Get stashed NPC data
        stashed_area = stashed_npc_data.get('area', state.get('current_area', 'Unknown Area')) # Fallback to current_area if stashed_npc has no area
        print(f"{TF.YELLOW}Currently consulting Lyra. Your physical location is {stashed_area}. NPCs there:{TF.RESET}")
        current_display_area = stashed_area # Override area to display NPCs from physical location
    elif not current_display_area: # Not in Lyra mode, but no current area set
        print(f"{TF.YELLOW}Not in an area. Use /go.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    all_npcs = session_utils.refresh_known_npcs_list(db, TF)

    # Filter NPCs for the area to be displayed (either current physical or stashed physical)

    npcs_here = [n for n in all_npcs if n.get('area','').lower() == current_display_area.lower()]

    if not npcs_here:
        print(f"\n{TF.YELLOW}No NPCs in {current_display_area}.{TF.RESET}")
    else:
        if not state.get('in_lyra_hint_mode'): # Only print this header if not in Lyra mode (where a similar header is already printed)
            print(f"\n{TF.YELLOW}NPCs in '{current_display_area}':{TF.RESET}")
        for n in sorted(npcs_here, key=lambda x: x.get('name','').lower()): # Sort by name
            npc_color = session_utils.get_npc_color(n.get('name', 'NPC'), TF)
            print(f" {TF.DIM}- {npc_color}{n.get('name','???')}{TF.RESET} {TF.DIM}({n.get('role','???')}){TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}