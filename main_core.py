# Path: main_core.py
# MODIFIED: To integrate player profile updates using the LLM-based approach.

import sys
import traceback
import re
from typing import Dict, List, Any, Optional, Tuple, Callable
import copy # For deepcopy

try:
    from terminal_formatter import TerminalFormatter
    from chat_manager import ChatSession, format_stats
    from db_manager import DbManager
    from llm_wrapper import llm_wrapper # Ensure llm_wrapper is accessible
except ImportError as e:
    class TerminalFormatter: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_GREEN = ""; BRIGHT_YELLOW = ""; ITALIC = "";
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import base modules in main_core: {e}{TerminalFormatter.RESET}")
    sys.exit(1)

try:
    import command_processor
    import session_utils
    # Use the LLM-based update_player_profile
    from player_profile_manager import update_player_profile, get_default_player_profile
except ImportError as e:
    TF = TerminalFormatter
    print(f"{TF.RED}Fatal Error: Could not import command_processor, session_utils, or player_profile_manager: {e}{TF.RESET}")
    def update_player_profile(previous_profile, interaction_log, player_actions, llm_wrapper_func, model_name, current_npc_name, TF): # Fallback
        print(f"{TF.YELLOW}Warning: player_profile_manager.update_player_profile (LLM-based) not available.{TF.RESET}")
        return previous_profile, ["Profile update function (LLM-based) missing"]
    def get_default_player_profile(): return {}


def run_interaction_loop(
        db: DbManager,
        story: str,
        initial_area: Optional[str],
        initial_npc_name: Optional[str],
        model_name: Optional[str], # This is the primary model for NPC dialogue
        profile_analysis_model_name: Optional[str], # NEW: Model for profile analysis (can be same or different)
        use_stream: bool,
        auto_show_stats: bool,
        player_id: str
):
    initial_player_credits = db.get_player_credits(player_id)
    player_profile_data = db.load_player_profile(player_id)

    game_session_state: Dict[str, Any] = {
        'db': db, 'story': story, 'current_area': None, 'current_npc': None,
        'chat_session': None,
        'model_name': model_name, # For NPC dialogue
        'profile_analysis_model_name': profile_analysis_model_name or model_name, # Use specific or fallback to main model
        'use_stream': use_stream, 'auto_show_stats': auto_show_stats,
        'player_id': player_id,
        'player_inventory': db.load_inventory(player_id),
        'player_credits_cache': initial_player_credits,
        'player_profile_cache': player_profile_data,
        'ChatSession': ChatSession, 'TerminalFormatter': TerminalFormatter,
        'format_stats': format_stats,
        'llm_wrapper_func': llm_wrapper, # Make the actual llm_wrapper function available
        'npc_made_new_response_this_turn': False,
        'actions_this_turn_for_profile': [],
        'in_lyra_hint_mode': False, 'stashed_chat_session': None, 'stashed_npc': None,
        'lyra_hint_cache': None,
    }

    # ... (Initial Area/NPC Setup logic remains largely the same, ensuring llm_wrapper_func is passed if needed by session_utils) ...
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    llm_wrapper_for_setup = game_session_state['llm_wrapper_func']

    if initial_area:
        initial_area_prefix = initial_area.lower()
        area_matches = [area for area in known_areas if area.lower().startswith(initial_area_prefix)]
        if len(area_matches) == 1:
            game_session_state['current_area'] = area_matches[0]
            if initial_npc_name:
                npc_data, session = session_utils.start_conversation_with_specific_npc(
                    db, player_id, game_session_state['current_area'], initial_npc_name,
                    model_name, story, ChatSession, TerminalFormatter,
                    llm_wrapper_for_profile_distillation=llm_wrapper_for_setup
                )
                if npc_data and session: game_session_state['current_npc'], game_session_state['chat_session'] = npc_data, session
            else:
                default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
                    db, player_id, game_session_state['current_area'], model_name, story,
                    ChatSession, TerminalFormatter, llm_wrapper_for_profile_distillation=llm_wrapper_for_setup
                )
                if default_npc_data and default_session: game_session_state['current_npc'], game_session_state['chat_session'] = default_npc_data, default_session
        elif len(area_matches) > 1: print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' ambiguous.{TerminalFormatter.RESET}")
        else: print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' not found.{TerminalFormatter.RESET}")
    elif initial_npc_name and not initial_area: print(f"{TerminalFormatter.YELLOW}Warn: --npc specified without --area.{TerminalFormatter.RESET}")

    if not game_session_state['current_npc'] and not game_session_state['current_area']:
        print(f"\n{TerminalFormatter.YELLOW}No start area or NPC. Use /go to select an area.{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}Consider starting your journey by visiting Lyra in the 'Sanctum of Whispers'. Try: /go sanctum{TerminalFormatter.RESET}")
    elif not game_session_state['current_npc'] and game_session_state['current_area']:
         print(f"\n{TerminalFormatter.YELLOW}You are in {game_session_state['current_area']}. Use /talk or /who to find someone.{TerminalFormatter.RESET}")


    while True:
        try:
            # ... (Prompt display prefix logic remains the same) ...
            current_npc_for_prompt = game_session_state.get('current_npc')
            current_area_for_prompt = game_session_state.get('current_area')
            is_in_lyra_hint_mode = game_session_state.get('in_lyra_hint_mode', False)
            game_session_state['actions_this_turn_for_profile'] = [] # Reset for the turn

            prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_MAGENTA}{player_id} (Nowhere) > {TerminalFormatter.RESET}"
            if is_in_lyra_hint_mode and current_npc_for_prompt and current_npc_for_prompt.get('name') == "Lyra":
                 prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_CYAN}{player_id} (Consulting Lyra) > {TerminalFormatter.RESET}"
            elif current_npc_for_prompt and current_npc_for_prompt.get('name'):
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}{player_id} ({current_npc_for_prompt['name']}) > {TerminalFormatter.RESET}"
            elif current_area_for_prompt:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}{player_id} ({current_area_for_prompt}) > {TerminalFormatter.RESET}"

            user_input = input(prompt_prefix).strip()
            game_session_state['npc_made_new_response_this_turn'] = False
            previous_profile_for_comparison = copy.deepcopy(game_session_state.get('player_profile_cache', get_default_player_profile()))

            game_session_state = command_processor.process_input_revised(user_input, game_session_state)

            if game_session_state.get('status') == 'exit': break

            # --- Process NPC Giving Items/Credits ---
            # This logic remains largely the same, but ensures actions_this_turn_for_profile is populated
            if game_session_state.get('npc_made_new_response_this_turn') and not game_session_state.get('in_lyra_hint_mode'):
                # ... (existing GIVEN_ITEMS parsing logic) ...
                # Ensure to add to game_session_state['actions_this_turn_for_profile']
                # e.g., if item_name is received:
                # game_session_state['actions_this_turn_for_profile'].append(f"Received '{item_name}' from {current_npc_data.get('name', 'NPC')}")
                chat_session = game_session_state.get('chat_session')
                current_npc_data = game_session_state.get('current_npc')
                db_instance = game_session_state.get('db')
                player_id_curr = game_session_state.get('player_id')
                TF_curr = game_session_state.get('TerminalFormatter', TerminalFormatter)
                raw_npc_response_text = None
                if chat_session and chat_session.messages and chat_session.messages[-1].get("role") == "assistant":
                    raw_npc_response_text = chat_session.messages[-1].get("content")

                if raw_npc_response_text and current_npc_data and db_instance and player_id_curr:
                    items_given_names = []
                    credits_given = 0
                    tag_marker_start = "[GIVEN_ITEMS:"
                    tag_marker_end = "]"
                    tag_start_idx = raw_npc_response_text.rfind(tag_marker_start)
                    if tag_start_idx != -1:
                        content_start_idx = tag_start_idx + len(tag_marker_start)
                        tag_end_idx = raw_npc_response_text.find(tag_marker_end, content_start_idx)
                        if tag_end_idx != -1:
                            item_list_str = raw_npc_response_text[content_start_idx:tag_end_idx].strip()
                            dialogue_to_persist = raw_npc_response_text[:tag_start_idx].strip()
                            if chat_session.messages and chat_session.messages[-1].get("role") == "assistant":
                                chat_session.messages[-1]["content"] = dialogue_to_persist
                            if item_list_str:
                                potential_items = [item.strip() for item in item_list_str.split(',') if item.strip()]
                                for item_str in potential_items:
                                    credit_match = re.match(r"(\d+)\s+credits?", item_str, re.IGNORECASE)
                                    if credit_match: credits_given += int(credit_match.group(1))
                                    else: items_given_names.append(item_str)
                            if items_given_names or credits_given > 0:
                                print(f"{TF_curr.DIM}[SYSTEM PARSED GIVEN_ITEMS] NPC offered: Items: {items_given_names}, Credits: {credits_given}{TF_curr.RESET}")
                    if items_given_names:
                        for item_name in items_given_names:
                            if db_instance.add_item_to_inventory(player_id_curr, item_name, game_session_state):
                                game_session_state['actions_this_turn_for_profile'].append(f"Received '{item_name}' from {current_npc_data.get('name', 'NPC')}")
                    if credits_given > 0:
                        if db_instance.update_player_credits(player_id_curr, credits_given, game_session_state):
                            game_session_state['actions_this_turn_for_profile'].append(f"Received {credits_given} Credits from {current_npc_data.get('name', 'NPC')}")


            # --- Process Consequences of Player Giving an Item/Credits ---
            # This logic also remains, actions are added by command_processor
            item_given_details = game_session_state.pop('item_given_to_npc_this_turn', None)
            if item_given_details and isinstance(item_given_details, dict) and \
               game_session_state.get('current_npc') and \
               game_session_state.get('current_npc').get('code') == item_given_details.get('npc_code') and \
               not game_session_state.get('in_lyra_hint_mode'):
                item_player_gave_name = item_given_details['item_name']
                item_type = item_given_details.get('type')
                current_npc_for_consequence = game_session_state['current_npc']
                db_for_consequences = game_session_state['db']
                print(f"{TerminalFormatter.DIM}[SYSTEM evaluating consequence of giving '{item_player_gave_name}']...{TerminalFormatter.RESET}")
                if item_type == 'item': # Already logged by /give
                    npc_needed_object = current_npc_for_consequence.get('needed_object')
                    if npc_needed_object and item_player_gave_name == db_for_consequences._clean_item_name(npc_needed_object):
                        print(f"{TerminalFormatter.BRIGHT_YELLOW}[Game System]: {current_npc_for_consequence['name']} received needed '{npc_needed_object}'!{TerminalFormatter.RESET}")
                        game_session_state['actions_this_turn_for_profile'].append(f"Fulfilled quest objective for {current_npc_for_consequence.get('name', 'NPC')} by giving '{npc_needed_object}'")
                        # ... (hint update logic from before) ...

            # --- Player Profile Update Logic (using LLM-based approach) ---
            if (game_session_state.get('npc_made_new_response_this_turn') or item_given_details or user_input.startswith('/')) and \
               not game_session_state.get('in_lyra_hint_mode') and \
               game_session_state.get('actions_this_turn_for_profile'): # Only update if actions were logged

                current_profile_cache = game_session_state.get('player_profile_cache', get_default_player_profile())
                interaction_log_for_profile = []
                if game_session_state.get('chat_session') and game_session_state['chat_session'].messages:
                    # Get last few messages for context (e.g., user input and NPC response of the turn)
                    # Max 2 messages (last user, last npc) if they exist
                    interaction_log_for_profile = game_session_state['chat_session'].messages[-2:]


                npc_name_for_profile_update = game_session_state.get('current_npc',{}).get('name')

                # Call the LLM-based update_player_profile
                updated_profile, profile_changes_detected = update_player_profile(
                    previous_profile=current_profile_cache,
                    interaction_log=interaction_log_for_profile,
                    player_actions_summary=game_session_state['actions_this_turn_for_profile'],
                    llm_wrapper_func=game_session_state['llm_wrapper_func'],
                    model_name=game_session_state['profile_analysis_model_name'], # Use specific model for analysis
                    current_npc_name=npc_name_for_profile_update,
                    TF=game_session_state['TerminalFormatter']
                )

                if updated_profile != previous_profile_for_comparison:
                    game_session_state['player_profile_cache'] = updated_profile
                    db.save_player_profile(game_session_state['player_id'], updated_profile)
                    print(f"{TerminalFormatter.DIM}[Profile Updated in DB (LLM-based analysis)] {TerminalFormatter.RESET}")
                    if profile_changes_detected:
                        print(f"{TerminalFormatter.DIM}  Detected changes this turn:{TerminalFormatter.RESET}")
                        for change_desc in profile_changes_detected:
                            print(f"{TerminalFormatter.DIM}    - {change_desc}{TerminalFormatter.RESET}")
                    else:
                         print(f"{TerminalFormatter.DIM}  Profile object changed, but no specific descriptions were logged by LLM (check LLM response).{TerminalFormatter.RESET}")
                # else:
                    # print(f"{TerminalFormatter.DIM}[Profile Unchanged This Turn (LLM-based analysis)] {TerminalFormatter.RESET}")


        except KeyboardInterrupt:
            print(f"\n{TerminalFormatter.DIM}Interruption. Saving...{TerminalFormatter.RESET}")
            if game_session_state.get('in_lyra_hint_mode'):
                game_session_state = command_processor.handle_endhint(game_session_state)
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            db.save_player_state(player_id, game_session_state)
            if game_session_state.get('player_profile_cache'):
                 db.save_player_profile(player_id, game_session_state['player_profile_cache'])
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except EOFError:
            print(f"\n{TerminalFormatter.DIM}EOF. Saving...{TerminalFormatter.RESET}")
            if game_session_state.get('in_lyra_hint_mode'):
                game_session_state = command_processor.handle_endhint(game_session_state)
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            db.save_player_state(player_id, game_session_state)
            if game_session_state.get('player_profile_cache'):
                 db.save_player_profile(player_id, game_session_state['player_profile_cache'])
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Main Loop Error: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            print(f"{TerminalFormatter.YELLOW}Attempting to continue...{TerminalFormatter.RESET}")

    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    db.save_player_state(player_id, game_session_state)
    if game_session_state.get('player_profile_cache'):
        db.save_player_profile(player_id, game_session_state['player_profile_cache'])

    final_session = game_session_state.get('chat_session'); final_npc = game_session_state.get('current_npc')
    if final_session and final_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Last active interaction was with ({final_npc.get('name','N/A')}):{TerminalFormatter.RESET}\n{final_session.format_session_stats()}")
    else: print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")

