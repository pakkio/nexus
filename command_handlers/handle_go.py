# command_handlers/handle_go.py
from typing import Dict, Any
import session_utils # Assuming session_utils is in the python path or same directory level
from command_handler_utils import _add_profile_action # For logging player actions

def handle_go(args_str: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles the /go command to move the player to a new area.
    Optionally, can attempt to start a conversation with a specific NPC in the new area
    if provided as /go <area_name_fragment> <npc_name_fragment>.
    """
    db = state['db']
    player_id = state['player_id']
    TF = state['TerminalFormatter'] # Get TerminalFormatter from state

    if not args_str.strip():
        print(f"{TF.YELLOW}Where do you want to go? Usage: /go <area_name_fragment> [npc_name_fragment]{TF.RESET}")
        state['status'] = 'ok' # Command was recognized, but invalid args
        state['continue_loop'] = True
        return state

    parts = args_str.split(None, 1)
    area_arg_fragment = parts[0].lower()
    npc_arg_fragment = parts[1].lower() if len(parts) > 1 else None

    all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
    available_areas = session_utils.get_known_areas_from_list(all_known_npcs)

    if not available_areas:
        print(f"{TF.RED}Error: No areas available in the game world.{TF.RESET}")
        return state # No change

    # Find matching area
    area_matches = [area for area in available_areas if area_arg_fragment in area.lower()]

    new_area_name = None
    if len(area_matches) == 1:
        new_area_name = area_matches[0]
    elif len(area_matches) > 1:
        # Try for an exact match first if multiple partial matches
        exact_matches = [area for area in area_matches if area_arg_fragment == area.lower()]
        if len(exact_matches) == 1:
            new_area_name = exact_matches[0]
        else:
            print(f"{TF.YELLOW}Ambiguous area '{area_arg_fragment}'. Matches: {', '.join(area_matches)}. Please be more specific.{TF.RESET}")
            return state
    else:
        print(f"{TF.YELLOW}Area '{area_arg_fragment}' not found. Try /areas to see available locations.{TF.RESET}")
        return state

    # If successfully found a new area:
    print(f"{TF.GREEN}Moving to {new_area_name}...{TF.RESET}")
    _add_profile_action(state, f"Moved to area: '{new_area_name}'")

    # Save previous conversation if any
    if state.get('current_npc') and state.get('chat_session'):
        print(f"{TF.DIM}Saving previous conversation with {state['current_npc'].get('name', 'NPC')}...{TF.RESET}")
        # Corrected call to save_current_conversation
        session_utils.save_current_conversation(
            db,
            player_id,
            state['current_npc'],
            state['chat_session'],
            TF,
            state  # Pass the full game_session_state
        )

    state['current_area'] = new_area_name
    state['current_npc'] = None # Clear current NPC when moving to a new area
    state['chat_session'] = None # Clear current chat session

    # Attempt to start conversation with specified NPC in the new area
    if npc_arg_fragment:
        print(f"{TF.DIM}Looking for '{npc_arg_fragment}' in {new_area_name}...{TF.RESET}")
        # Corrected call to start_conversation_with_specific_npc
        npc_data, new_session = session_utils.start_conversation_with_specific_npc(
            db,
            player_id,
            new_area_name,
            npc_arg_fragment, # Pass the fragment, start_conversation should handle matching
            state['model_name'],
            state['story'],
            state['ChatSession'],
            TF,
            state, # Pass the full game_session_state
            conversation_summary_for_guide_context=None, # Not a hint context
            llm_wrapper_for_profile_distillation=state.get('llm_wrapper_func')
        )
        if npc_data and new_session:
            state['current_npc'] = npc_data
            state['chat_session'] = new_session
            _add_profile_action(state, f"Started talking to '{npc_data.get('name')}' in '{new_area_name}' after /go.")
        else:
            print(f"{TF.YELLOW}NPC '{npc_arg_fragment}' not found in {new_area_name}, or conversation could not be started.{TF.RESET}")
            # Fall through to try default NPC for the area
            npc_arg_fragment = None # Clear it so we attempt default below

    # If no specific NPC was targeted by args, or if finding the specific NPC failed,
    # try to auto-start with a default NPC in the new area.
    if not state.get('current_npc'): # Only if we haven't started a convo with a specific NPC
        print(f"{TF.DIM}Attempting to find a default NPC in {new_area_name}...{TF.RESET}")
        # Corrected call to auto_start_default_npc_conversation
        default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
            db,
            player_id,
            new_area_name,
            state['model_name'],
            state['story'],
            state['ChatSession'],
            TF,
            state,  # Pass the full game_session_state
            llm_wrapper_for_profile_distillation=state.get('llm_wrapper_func')
        )
        if default_npc_data and default_session:
            state['current_npc'] = default_npc_data
            state['chat_session'] = default_session
            _add_profile_action(state, f"Automatically started talking to default NPC '{default_npc_data.get('name')}' in '{new_area_name}'.")
        else:
            print(f"{TF.YELLOW}No default NPC found or conversation could not be started in {new_area_name}.{TF.RESET}")
            print(f"{TF.YELLOW}You are now in {new_area_name}. Use /talk <npc_name> or /who to find someone.{TF.RESET}")
            state['current_npc'] = None
            state['chat_session'] = None

    state['status'] = 'ok'
    state['continue_loop'] = True
    return state