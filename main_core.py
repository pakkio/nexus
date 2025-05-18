# Path: main_core.py
# Updated for Credits system and case-insensitive inventory processing
# Further updated for advanced /hint state management
# MODIFIED: Added initial hint to go to Sanctum if starting in Nowhere.

import sys
import traceback
import re
from typing import Dict, List, Any, Optional, Tuple

try:
    from terminal_formatter import TerminalFormatter
    from chat_manager import ChatSession, format_stats
    from db_manager import DbManager
except ImportError as e:
    class TerminalFormatter: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_GREEN = ""; BRIGHT_YELLOW = "";
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import base modules: {e}{TerminalFormatter.RESET}")
    sys.exit(1)

try:
    import command_processor
    import session_utils
    # hint_manager is imported by command_processor
except ImportError as e:
    TF = TerminalFormatter
    print(f"{TF.RED}Fatal Error: Could not import command_processor or session_utils: {e}{TF.RESET}")
    sys.exit(1)


def run_interaction_loop(
        db: DbManager,
        story: str,
        initial_area: Optional[str],
        initial_npc_name: Optional[str],
        model_name: Optional[str],
        use_stream: bool,
        auto_show_stats: bool,
        player_id: str
):
    """Runs the main user interaction loop."""

    initial_player_credits = db.get_player_credits(player_id)

    game_session_state: Dict[str, Any] = {
        'db': db, 'story': story, 'current_area': None, 'current_npc': None,
        'chat_session': None, 'model_name': model_name,
        'use_stream': use_stream, 'auto_show_stats': auto_show_stats,
        'player_id': player_id,
        'player_inventory': db.load_inventory(player_id),
        'player_credits_cache': initial_player_credits,
        'ChatSession': ChatSession, 'TerminalFormatter': TerminalFormatter,
        'format_stats': format_stats,
        'npc_made_new_response_this_turn': False,
        # --- New state variables for Advanced /hint ---
        'in_lyra_hint_mode': False,
        'stashed_chat_session': None, # Will hold a ChatSession object
        'stashed_npc': None,          # Will hold an NPC data dictionary
        'lyra_hint_cache': None,      # Will hold {'key': str, 'lyra_chat_history': List[Dict], 'timestamp': float}
        # --- End new state variables ---
    }

    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)

    if initial_area:
        print(f"{TerminalFormatter.DIM}Validating initial area '{initial_area}'...{TerminalFormatter.RESET}")
        initial_area_prefix = initial_area.lower()
        area_matches = [area for area in known_areas if area.lower().startswith(initial_area_prefix)]
        if len(area_matches) == 1:
            game_session_state['current_area'] = area_matches[0]
            print(f"{TerminalFormatter.GREEN}Initial area: {game_session_state['current_area']}{TerminalFormatter.RESET}")
            if initial_npc_name:
                npc_data, session = session_utils.start_conversation_with_specific_npc(
                    db, player_id, game_session_state['current_area'], initial_npc_name,
                    model_name, story, ChatSession, TerminalFormatter)
                if npc_data and session:
                    game_session_state['current_npc'] = npc_data
                    game_session_state['chat_session'] = session
            else:
                default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
                    db, player_id, game_session_state['current_area'], model_name, story,
                    ChatSession, TerminalFormatter)
                if default_npc_data and default_session:
                    game_session_state['current_npc'] = default_npc_data
                    game_session_state['chat_session'] = default_session
        elif len(area_matches) > 1: print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' ambiguous.{TerminalFormatter.RESET}")
        else: print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' not found.{TerminalFormatter.RESET}")
    elif initial_npc_name and not initial_area: print(f"{TerminalFormatter.YELLOW}Warn: --npc specified without --area.{TerminalFormatter.RESET}")

    if not game_session_state['current_npc'] and not game_session_state['current_area']:
        print(f"\n{TerminalFormatter.YELLOW}No start area or NPC. Use /go to select an area.{TerminalFormatter.RESET}")
        # MODIFICATION: Suggest Sanctum
        print(f"{TerminalFormatter.DIM}Consider starting your journey by visiting Lyra in the 'Sanctum of Whispers'. Try: /go sanctum{TerminalFormatter.RESET}")
    elif not game_session_state['current_npc'] and game_session_state['current_area']:
         print(f"\n{TerminalFormatter.YELLOW}You are in {game_session_state['current_area']}. Use /talk or /who to find someone.{TerminalFormatter.RESET}")


    while True:
        try:
            current_npc_for_prompt = game_session_state.get('current_npc')
            current_area_for_prompt = game_session_state.get('current_area')
            is_in_lyra_hint_mode = game_session_state.get('in_lyra_hint_mode', False)

            prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_MAGENTA}{player_id} (Nowhere) > {TerminalFormatter.RESET}"
            if is_in_lyra_hint_mode and current_npc_for_prompt and current_npc_for_prompt.get('name') == "Lyra": # Check if current NPC is Lyra during hint mode
                 prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_CYAN}{player_id} (Consulting Lyra) > {TerminalFormatter.RESET}"
            elif current_npc_for_prompt and current_npc_for_prompt.get('name'):
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}{player_id} ({current_npc_for_prompt['name']}) > {TerminalFormatter.RESET}"
            elif current_area_for_prompt:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}{player_id} ({current_area_for_prompt}) > {TerminalFormatter.RESET}"

            user_input = input(prompt_prefix).strip()

            game_session_state['npc_made_new_response_this_turn'] = False

            game_session_state = command_processor.process_input_revised(user_input, game_session_state)

            if game_session_state.get('status') == 'exit': break

            # --- Process NPC Giving Items/Credits (Tag-Based) ---
            if game_session_state.get('npc_made_new_response_this_turn') and not game_session_state.get('in_lyra_hint_mode'): # Only for regular NPC turns
                chat_session = game_session_state.get('chat_session')
                current_npc_data = game_session_state.get('current_npc')
                db_instance = game_session_state.get('db')
                player_id_curr = game_session_state.get('player_id')
                TF = game_session_state.get('TerminalFormatter', TerminalFormatter)

                raw_npc_response_text = None
                if chat_session and chat_session.messages and \
                   chat_session.messages[-1].get("role") == "assistant":
                    raw_npc_response_text = chat_session.messages[-1].get("content")

                if raw_npc_response_text and current_npc_data and db_instance and player_id_curr:
                    items_given_by_npc_this_turn_names = []
                    credits_given_by_npc_this_turn = 0
                    dialogue_to_persist = raw_npc_response_text

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
                                potential_items_or_credits = [item.strip() for item in item_list_str.split(',') if item.strip()]
                                for poc_item_str in potential_items_or_credits:
                                    credit_match = re.match(r"(\d+)\s+credits?", poc_item_str, re.IGNORECASE)
                                    if credit_match:
                                        credits_given_by_npc_this_turn += int(credit_match.group(1))
                                    else:
                                        items_given_by_npc_this_turn_names.append(poc_item_str)

                            if items_given_by_npc_this_turn_names or credits_given_by_npc_this_turn > 0:
                                print(f"{TF.DIM}[SYSTEM PARSED GIVEN_ITEMS] NPC offered: Items: {items_given_by_npc_this_turn_names}, Credits: {credits_given_by_npc_this_turn}{TF.RESET}")

                    if items_given_by_npc_this_turn_names:
                        for item_name in items_given_by_npc_this_turn_names:
                            if db_instance.add_item_to_inventory(player_id_curr, item_name, game_session_state):
                                game_session_state['player_inventory'] = db_instance.load_inventory(player_id_curr)

                    if credits_given_by_npc_this_turn > 0:
                        if db_instance.update_player_credits(player_id_curr, credits_given_by_npc_this_turn, game_session_state):
                            game_session_state['player_credits_cache'] = db_instance.get_player_credits(player_id_curr)

            # --- Process Consequences of Player Giving an Item/Credits ---
            item_given_details = game_session_state.pop('item_given_to_npc_this_turn', None)
            if item_given_details and isinstance(item_given_details, dict) and \
               game_session_state.get('current_npc') and \
               game_session_state.get('current_npc').get('code') == item_given_details.get('npc_code') and \
               not game_session_state.get('in_lyra_hint_mode'): # Only for regular NPC turns

                item_player_gave_name = item_given_details['item_name']
                item_type = item_given_details.get('type')
                current_npc_for_consequence = game_session_state['current_npc']
                chat_session_for_consequence = game_session_state.get('chat_session')
                db_for_consequences = game_session_state['db']

                print(f"{TerminalFormatter.DIM}[SYSTEM evaluating consequence of giving '{item_player_gave_name}']...{TerminalFormatter.RESET}")

                if item_type == 'currency':
                    pass
                elif item_type == 'item':
                    npc_needed_object = current_npc_for_consequence.get('needed_object')
                    npc_treasure_reward = current_npc_for_consequence.get('treasure')
                    cleaned_item_player_gave = item_player_gave_name

                    if npc_needed_object and cleaned_item_player_gave == db_for_consequences._clean_item_name(npc_needed_object):
                        print(f"{TerminalFormatter.BRIGHT_YELLOW}[Game System]: {current_npc_for_consequence['name']} received needed '{npc_needed_object}'!{TerminalFormatter.RESET}")
                        if npc_treasure_reward and npc_treasure_reward.lower() != cleaned_item_player_gave.lower():
                            if not db_for_consequences.check_item_in_inventory(player_id, npc_treasure_reward):
                                pass
                            else: print(f"{TerminalFormatter.DIM}{current_npc_for_consequence['name']} would give '{npc_treasure_reward}', but you already have it.{TerminalFormatter.RESET}")
                        if chat_session_for_consequence:
                            new_hint = f"You helped {current_npc_for_consequence['name']} with their goal regarding '{npc_needed_object}'."
                            if npc_treasure_reward:
                                new_hint += f" They might have '{npc_treasure_reward}' for you, or have already given it."
                            chat_session_for_consequence.set_player_hint(new_hint)
        except KeyboardInterrupt:
            print(f"\n{TerminalFormatter.DIM}Interruption. Saving...{TerminalFormatter.RESET}")
            if game_session_state.get('in_lyra_hint_mode'):
                print(f"{TerminalFormatter.DIM}Exiting Lyra hint mode due to interruption.{TerminalFormatter.RESET}")
                game_session_state = command_processor.handle_endhint(game_session_state)
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except EOFError:
            print(f"\n{TerminalFormatter.DIM}EOF. Saving...{TerminalFormatter.RESET}")
            if game_session_state.get('in_lyra_hint_mode'):
                print(f"{TerminalFormatter.DIM}Exiting Lyra hint mode due to EOF.{TerminalFormatter.RESET}")
                game_session_state = command_processor.handle_endhint(game_session_state)
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Main Loop Error: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            print(f"{TerminalFormatter.YELLOW}Attempting to continue...{TerminalFormatter.RESET}")

    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    final_session = game_session_state.get('chat_session'); final_npc = game_session_state.get('current_npc')
    if final_session and final_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Last active interaction was with ({final_npc.get('name','N/A')}):{TerminalFormatter.RESET}\n{final_session.format_session_stats()}")
    else: print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")
