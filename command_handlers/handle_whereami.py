from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    _add_profile_action(state, "Used /whereami command")

    is_hint_mode = state.get('in_lyra_hint_mode', False)
    current_location_area = state.get('current_area', 'Nowhere') # Physical location
    current_talking_to_npc = state.get('current_npc') # Current NPC (could be Lyra in hint mode)
    current_chat_session_obj = state.get('chat_session') # Current chat session

    display_area = current_location_area
    display_npc_name = "Nobody"
    hint_for_display = None

    if is_hint_mode:
        # If in hint mode, 'current_npc' is Lyra. We need the stashed area.
        stashed_npc_data = state.get('stashed_npc')
        stashed_area = stashed_npc_data.get('area', "Unknown (stashed)") if stashed_npc_data else "Unknown (stashed)"
        display_area = f"{stashed_area} (Physically)"
        lyra_name = current_talking_to_npc.get('name', 'Lyra') if current_talking_to_npc else 'Lyra'
        display_npc_name = f"{lyra_name} (In Consultation)"
        # No simple hint display during Lyra consultation
    else: # Not in hint mode
        if current_talking_to_npc:
            display_npc_name = current_talking_to_npc.get('name', 'Unknown NPC')
            if current_chat_session_obj: # Get hint for the actual NPC
                hint_for_display = current_chat_session_obj.get_player_hint()

    loc_msg = f"Location: {TF.BOLD}{display_area}{TF.RESET}"

    if current_talking_to_npc and not is_hint_mode: # Regular NPC conversation
        npc_color = session_utils.get_npc_color(current_talking_to_npc.get('name', 'NPC'), TF)
        talking_msg = f"Talking to: {TF.BOLD}{npc_color}{display_npc_name}{TF.RESET}"
    elif is_hint_mode: # Lyra consultation
        lyra_color = session_utils.get_npc_color("Lyra", TF) # Lyra's specific color
        talking_msg = f"Talking to: {TF.BOLD}{lyra_color}{display_npc_name}{TF.RESET}"
    else: # Not talking to anyone
        talking_msg = f"Talking to: {TF.BOLD}{display_npc_name}{TF.RESET}"

    if hint_for_display and not is_hint_mode: # Only show hint if not in Lyra mode and hint exists
        talking_msg += f"\n {TF.DIM}(Hint for {display_npc_name}: {hint_for_display[:70]}{'...' if len(hint_for_display) > 70 else ''}){TF.RESET}"

    print(f"\n{TF.CYAN}{loc_msg}\n{talking_msg}{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}