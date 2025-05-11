# Path: main_core.py
# Updated for robust NPC item giving via [GIVEN_ITEMS:] tag parsing

import sys
import traceback 
import re # For parsing the new tag
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
    game_session_state: Dict[str, Any] = {
        'db': db, 'story': story, 'current_area': None, 'current_npc': None, 
        'chat_session': None, 'model_name': model_name,
        'use_stream': use_stream, 'auto_show_stats': auto_show_stats,
        'player_id': player_id, 'player_inventory': db.load_inventory(player_id),
        'ChatSession': ChatSession, 'TerminalFormatter': TerminalFormatter, 
        'format_stats': format_stats, 'npc_made_new_response_this_turn': False,
    }

    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    
    # --- Initial Area and NPC Setup ---
    if initial_area:
        # ... (Keep your existing initial area/NPC setup logic from previous correct version) ...
        # This logic correctly calls session_utils.start_conversation_with_specific_npc
        # or session_utils.auto_start_default_npc_conversation.
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
    if not game_session_state['current_area']: print(f"\n{TerminalFormatter.YELLOW}No start area. Use /go.{TerminalFormatter.RESET}")

    while True:
        try:
            # --- Build Prompt for Player Input ---
            current_npc_for_prompt = game_session_state.get('current_npc')
            current_area_for_prompt = game_session_state.get('current_area')
            prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_MAGENTA}{player_id} (Nowhere) > {TerminalFormatter.RESET}"
            if current_npc_for_prompt and current_npc_for_prompt.get('name'):
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}{player_id} ({current_npc_for_prompt['name']}) > {TerminalFormatter.RESET}"
            elif current_area_for_prompt:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}{player_id} ({current_area_for_prompt}) > {TerminalFormatter.RESET}"
            user_input = input(prompt_prefix).strip()
            
            game_session_state['npc_made_new_response_this_turn'] = False # Reset for this turn
            
            # --- Process Player Input (Commands or Dialogue) ---
            game_session_state = command_processor.process_input_revised(user_input, game_session_state)

            if game_session_state.get('status') == 'exit': break 

            # --- Process NPC Giving Items (Tag-Based) ---
            if game_session_state.get('npc_made_new_response_this_turn'):
                chat_session = game_session_state.get('chat_session')
                current_npc_data = game_session_state.get('current_npc') # Renamed for clarity
                
                raw_npc_response_text = None
                if chat_session and chat_session.messages and \
                   chat_session.messages[-1].get("role") == "assistant":
                    raw_npc_response_text = chat_session.messages[-1].get("content")

                if raw_npc_response_text and current_npc_data:
                    items_to_add_to_inventory = []
                    dialogue_to_persist = raw_npc_response_text 
                    
                    tag_marker_start = "[GIVEN_ITEMS:"
                    tag_marker_end = "]"
                    
                    tag_start_idx = raw_npc_response_text.rfind(tag_marker_start)
                    
                    if tag_start_idx != -1:
                        content_start_idx = tag_start_idx + len(tag_marker_start)
                        tag_end_idx = raw_npc_response_text.find(tag_marker_end, content_start_idx)
                        
                        if tag_end_idx != -1:
                            item_list_str = raw_npc_response_text[content_start_idx:tag_end_idx].strip()
                            if item_list_str:
                                items_to_add_to_inventory = [item.strip() for item in item_list_str.split(',') if item.strip()]
                            
                            # Clean the dialogue to be stored in history and potentially re-displayed if needed
                            # This assumes tag is at the end. A more robust removal might be needed if tag can be mid-dialogue.
                            dialogue_to_persist = raw_npc_response_text[:tag_start_idx].strip()
                            
                            # Update the last message in chat history with the cleaned dialogue
                            if chat_session.messages and chat_session.messages[-1].get("role") == "assistant":
                                chat_session.messages[-1]["content"] = dialogue_to_persist
                            
                            print(f"{TerminalFormatter.DIM}[SYSTEM PARSED] NPC intends to give: {', '.join(items_to_add_to_inventory)}{TerminalFormatter.RESET}")
                    
                    if items_to_add_to_inventory:
                        for item_name in items_to_add_to_inventory:
                            if db.add_item_to_inventory(player_id, item_name, game_session_state):
                                game_session_state['player_inventory'] = db.load_inventory(player_id) # Refresh cache
                            # add_item_to_inventory prints its own messages

            # --- Process Consequences of Player Giving an Item ---
            item_given_details = game_session_state.pop('item_given_to_npc_this_turn', None)
            if item_given_details and isinstance(item_given_details, dict) and \
               game_session_state.get('current_npc') and \
               game_session_state.get('current_npc').get('code') == item_given_details.get('npc_code'):
                
                item_player_gave = item_given_details['item_name']
                current_npc_for_consequence = game_session_state['current_npc']
                chat_session_for_consequence = game_session_state.get('chat_session')
                db_for_consequences = game_session_state['db'] # Use db from current state
                
                print(f"{TerminalFormatter.DIM}[SYSTEM evaluating consequence of giving '{item_player_gave}']...{TerminalFormatter.RESET}")
                
                npc_needed_object = current_npc_for_consequence.get('needed_object')
                npc_treasure_reward = current_npc_for_consequence.get('treasure') 

                if npc_needed_object and item_player_gave.lower() == npc_needed_object.lower():
                    print(f"{TerminalFormatter.BRIGHT_YELLOW}[Game System]: {current_npc_for_consequence['name']} received '{npc_needed_object}'!{TerminalFormatter.RESET}")
                    if npc_treasure_reward and npc_treasure_reward.lower() != item_player_gave.lower(): 
                        if not db_for_consequences.check_item_in_inventory(player_id, npc_treasure_reward):
                            db_for_consequences.add_item_to_inventory(player_id, npc_treasure_reward, game_session_state)
                            game_session_state['player_inventory'] = db_for_consequences.load_inventory(player_id)
                            print(f"{TerminalFormatter.BRIGHT_CYAN}{current_npc_for_consequence['name']} gives you: {npc_treasure_reward}!{TerminalFormatter.RESET}")
                            if chat_session_for_consequence: # Add to history for NPC context
                                chat_session_for_consequence.add_message("assistant", f"*For the {npc_needed_object}, please accept this {npc_treasure_reward}. It is now yours.* [GIVEN_ITEMS: {npc_treasure_reward}]")
                                # The above line manually adds GIVEN_ITEMS tag for consistency if NPC gives treasure this way
                                # And then main_core loop for NPC giving would re-process it. This can be refined.
                                # Better: LLM generates the [GIVEN_ITEMS] tag itself when it decides to give the treasure.
                                # For now, let's assume add_item_to_inventory is sufficient player feedback.
                        else:
                            print(f"{TerminalFormatter.DIM}{current_npc_for_consequence['name']} would give '{npc_treasure_reward}', but you already have it.{TerminalFormatter.RESET}")
                    if chat_session_for_consequence and hasattr(chat_session_for_consequence, 'set_player_hint'):
                        new_hint = f"You helped {current_npc_for_consequence['name']} with the {npc_needed_object}."
                        chat_session_for_consequence.set_player_hint(new_hint)

        except KeyboardInterrupt: 
            print(f"\n{TerminalFormatter.DIM}Interruption. Saving...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except EOFError: 
            print(f"\n{TerminalFormatter.DIM}EOF. Saving...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, game_session_state.get('current_npc'), game_session_state.get('chat_session'), TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}"); break
        except Exception as e: 
            print(f"\n{TerminalFormatter.RED}❌ Main Loop Error: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            print(f"{TerminalFormatter.YELLOW}Attempting to continue...{TerminalFormatter.RESET}")

    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    final_session = game_session_state.get('chat_session')
    final_npc = game_session_state.get('current_npc')
    if final_session and final_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Stats ({final_npc.get('name', 'N/A')}):{TerminalFormatter.RESET}")
        print(final_session.format_session_stats())
    else: print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")

