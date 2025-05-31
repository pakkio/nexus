from typing import Dict, Any
import session_utils
from ..command_handler_utils import HandlerResult, _add_profile_action

def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    _add_profile_action(state, f"Used /go command with args: '{args}'")

    if state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}You cannot use /go while consulting Lyra. Use /endhint first.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    current_npc_old = state.get('current_npc')
    chat_session_old = state.get('chat_session')

    if not args:
        print(f"{TF.YELLOW}Usage: /go <area_name_fragment>{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    target_terms = args.lower().split() # Split args into terms for more flexible matching
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TF) # Get up-to-date list
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)

    matches = []
    if target_terms: # Ensure there are terms to match
        matches = [
            area_name_full for area_name_full in known_areas
            if all(term in area_name_full.lower() for term in target_terms)
        ]

    new_state_part: Dict[str, Any] = {} # To collect changes to state

    if len(matches) == 1:
        area = matches[0]
        current_area_from_state = state.get('current_area')
        if current_area_from_state is not None and current_area_from_state.lower() == area.lower():
            print(f"{TF.DIM}You are already in {area}.{TF.RESET}")
            return {**state, 'status': 'ok', 'continue_loop': True}

        print(f"{TF.DIM}Area match: {area}{TF.RESET}") # Informative
        # Save current conversation before moving
        if chat_session_old: # Check if there was an active session
            print(f"{TF.DIM}Saving previous conversation with {current_npc_old.get('name', 'NPC')}...{TF.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TF)

        print(f"{TF.CYAN}Moving to: {area}...{TF.RESET}...")
        new_state_part.update({'current_area': area, 'current_npc': None, 'chat_session': None})

        # Try to auto-start conversation with default NPC in new area
        llm_wrapper_for_npc_setup = state.get('llm_wrapper_func')
        npc_data, session = session_utils.auto_start_default_npc_conversation(
            db, player_id, area, state['model_name'], state['story'], state['ChatSession'], TF,
            llm_wrapper_for_profile_distillation=llm_wrapper_for_npc_setup
        )
        if npc_data and session:
            new_state_part['current_npc'] = npc_data
            new_state_part['chat_session'] = session
        # else: auto_start failed or no default NPC, player arrives in area silently.

    elif len(matches) > 1:
        print(f"{TF.YELLOW}⚠️ Ambiguous area '{args}'. Matches: {', '.join(sorted(matches))}{TF.RESET}")
    else: # No matches
        print(f"{TF.YELLOW}⚠️ Area '{args}' not found. Known areas can be listed with /areas.{TF.RESET}")

    state.update(new_state_part)
    return {**state, 'status': 'ok', 'continue_loop': True}