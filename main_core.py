# Path: main_core.py

import sys
import traceback 
from typing import Dict, List, Any, Optional, Tuple

try:
    from terminal_formatter import TerminalFormatter
    from chat_manager import ChatSession, format_stats 
    from db_manager import DbManager
    # from main_utils import format_storyboard_for_prompt # No longer directly used here
except ImportError as e:
    class TerminalFormatter: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_GREEN = ""; BRIGHT_YELLOW = "";
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import base modules in main_core.py: {e}{TerminalFormatter.RESET}")
    sys.exit(1)

try:
    import command_processor
    import session_utils 
    # from llm_wrapper import llm_wrapper # Import if needed for summarization state
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
        # llm_wrapper_func_ref: callable # Add if summarization is directly called from here via save_current_conversation
):
    """Runs the main user interaction loop, delegating command processing."""

    # These are the primary mutable state variables for the session
    current_area: Optional[str] = None
    current_npc: Optional[Dict[str, Any]] = None # Holds data of NPC being talked to
    chat_session: Optional[ChatSession] = None # ChatSession INSTANCE

    # Cached lists (can be refreshed by commands if needed)
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    
    # Player inventory can be cached in state for quick checks by some commands,
    # but critical checks (like /give) should always load fresh from DB.
    player_inventory_cache = db.load_inventory(player_id)


    # --- Initial Area and NPC Setup ---
    if initial_area:
        print(f"{TerminalFormatter.DIM}Validating initial area '{initial_area}'...{TerminalFormatter.RESET}")
        initial_area_prefix = initial_area.lower()
        area_matches = [area for area in known_areas if area.lower().startswith(initial_area_prefix)]

        if len(area_matches) == 1:
            current_area = area_matches[0]
            print(f"{TerminalFormatter.GREEN}Initial area set to: {current_area}{TerminalFormatter.RESET}")

            if initial_npc_name: 
                # print(f"{TerminalFormatter.DIM}Attempting to start with specified NPC: '{initial_npc_name}'...{TerminalFormatter.RESET}") # session_utils prints this
                npc_data, session = session_utils.start_conversation_with_specific_npc(
                    db, player_id, current_area, initial_npc_name, model_name, story, ChatSession, TerminalFormatter
                )
                if npc_data and session:
                    current_npc = npc_data
                    chat_session = session
                else: 
                    print(f"{TerminalFormatter.YELLOW}⚠️ Could not start conversation with specified NPC '{initial_npc_name}'. You can use /talk or /who.{TerminalFormatter.RESET}")
            else: 
                default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
                    db, player_id, current_area, model_name, story, ChatSession, TerminalFormatter
                )
                if default_npc_data and default_session:
                    current_npc = default_npc_data
                    chat_session = default_session
        elif len(area_matches) > 1: # Ambiguous area
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area prefix '{initial_area}' is ambiguous. Matches:{TerminalFormatter.RESET}") # ... (rest of message)
            for area_match in sorted(area_matches): print(f"  - {area_match}")
            print(f"{TerminalFormatter.YELLOW}Please restart or use /go.{TerminalFormatter.RESET}")
        else: # Area not found
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' not found.{TerminalFormatter.RESET}") # ... (rest of message)
            if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(known_areas)}{TerminalFormatter.RESET}")


    elif initial_npc_name and not initial_area: 
         print(f"\n{TerminalFormatter.YELLOW}Warning: --npc ('{initial_npc_name}') provided without valid --area. Use /go first.{TerminalFormatter.RESET}")
    
    if not current_area: 
        print(f"\n{TerminalFormatter.YELLOW}No starting area. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.YELLOW} to begin.{TerminalFormatter.RESET}")

    # ===========================
    # --- Main Interaction Loop ---
    # ===========================
    item_given_to_npc_in_last_successful_turn: Optional[Dict[str, Any]] = None

    while True:
        try:
            prompt_prefix = "" # Build prompt based on current state
            if current_npc and current_npc.get('name'):
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}{player_id} ({current_npc['name']}) > {TerminalFormatter.RESET}"
            elif current_area:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}{player_id} ({current_area}) > {TerminalFormatter.RESET}"
            else:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_MAGENTA}{player_id} (Nowhere) > {TerminalFormatter.RESET}"

            user_input = input(prompt_prefix).strip()

            # Prepare the state dictionary for command_processor
            # This dictionary is mutable and command_processor can add to it (e.g. 'item_given_to_npc_this_turn')
            # Or command_processor returns a dict of CHANGES to be applied. The latter is cleaner.
            current_game_state = {
                'db': db, 'story': story,
                'current_area': current_area, 'current_npc': current_npc, # These are the current values
                'chat_session': chat_session, # This is an INSTANCE
                'model_name': model_name,
                'use_stream': use_stream, 'auto_show_stats': auto_show_stats,
                'player_id': player_id,
                'player_inventory': player_inventory_cache, # Pass the cache
                'ChatSession': ChatSession, # Pass the CLASS
                'TerminalFormatter': TerminalFormatter, 
                'format_stats': format_stats,
                # 'llm_wrapper_func': llm_wrapper_func_ref, # For summarization if save needs it
                # 'item_given_to_npc_this_turn': None, # Initialize for command_processor to set
            }
            
            # Store previous NPC code to detect if conversation changed due to /give
            prev_npc_code_before_cmd = current_npc.get('code') if current_npc else None

            # Process input. handler_result now contains the *full updated state*
            # or specific keys that changed.
            # For /give, it's better if 'item_given_to_npc_this_turn' is part of the *returned value*
            # from process_input_revised, not directly mutating current_game_state from within a handler.
            
            # Let's assume process_input_revised returns a dictionary of *changes* or the *new full state*.
            # If it returns changes, we merge. If full state, we replace.
            # The current process_input_revised returns the full state merged with handler output.
            
            returned_state_from_command = command_processor.process_input_revised(user_input, current_game_state)

            if returned_state_from_command.get('status') == 'exit':
                break # Exit command was handled

            # Update main loop variables from the state returned by command_processor
            current_area = returned_state_from_command.get('current_area')
            current_npc = returned_state_from_command.get('current_npc')
            chat_session = returned_state_from_command.get('chat_session')
            player_inventory_cache = returned_state_from_command.get('player_inventory', player_inventory_cache) # Update cache

            # Check for the flag set by handle_give (after NPC has had a chance to react to the "hands over" message)
            # The NPC's reaction to the item being given would have been the last LLM call if /give was used.
            # The 'item_given_to_npc_this_turn' should be set by handle_give and be present in returned_state_from_command
            
            # This needs to be processed *after* the NPC has textually reacted to the item.
            # The `process_input_revised` dialogue block handles the LLM call *if user_input wasn't a command*.
            # If `/give` was the command, the NPC reaction to the "hands over item" needs to be triggered.
            # This is complex. `handle_give` now adds "user: *hands over ITEM*" to history.
            # If the user types something *else* next, that will be the prompt NPC reacts to.
            # The consequence check needs to happen *after* the NPC has reacted to the item.

            # Simpler: After any turn where player spoke (or took action like /give):
            if current_npc and chat_session and chat_session.messages:
                last_player_action_message = None
                # Find the last "user" message which might be the give action.
                for msg in reversed(chat_session.messages):
                    if msg.get("role") == "user":
                        last_player_action_message = msg.get("content","")
                        break
                
                # Check if the last player action was a give, and if current NPC is still the same
                # The 'item_given_to_npc_this_turn' flag would have been set by handle_give in the PREVIOUS turn's state.
                # We need to retrieve it from *this* turn's state as set by the command processor if /give was used.
                
                given_item_details = returned_state_from_command.get('item_given_to_npc_this_turn')
                
                if given_item_details and isinstance(given_item_details, dict) and \
                   current_npc and current_npc.get('code') == given_item_details.get('npc_code'):
                    
                    item_player_gave = given_item_details['item_name']
                    print(f"{TerminalFormatter.DIM}[SYSTEM POST-REACTION CHECK for {current_npc['name']}] Player gave: {item_player_gave}{TerminalFormatter.RESET}")
                    
                    npc_needed_object = current_npc.get('needed_object')
                    npc_treasure = current_npc.get('treasure')

                    if npc_needed_object and item_player_gave.lower() == npc_needed_object.lower():
                        print(f"{TerminalFormatter.BRIGHT_YELLOW}[Game System]: {current_npc['name']} seems to acknowledge the '{npc_needed_object}'!{TerminalFormatter.RESET}")
                        
                        # Logic to give treasure
                        if npc_treasure:
                            if not db.check_item_in_inventory(player_id, npc_treasure):
                                # Pass the most current game state to add_item_to_inventory
                                db.add_item_to_inventory(player_id, npc_treasure, current_game_state) 
                                print(f"{TerminalFormatter.BRIGHT_CYAN}{current_npc['name']} gives you: {npc_treasure}!{TerminalFormatter.RESET}")
                                if chat_session: # Log it to history for NPC awareness
                                    chat_session.add_message("assistant", f"*As a token of gratitude for the {npc_needed_object}, I give you {npc_treasure}.*")
                                player_inventory_cache = db.load_inventory(player_id) # Refresh cache
                            else:
                                print(f"{TerminalFormatter.DIM}{current_npc['name']} would give '{npc_treasure}', but you already possess such an item.{TerminalFormatter.RESET}")
                        
                        # TODO: Update quest state / player profile here
                        # db.add_rumor_to_profile(player_id, f"Helped {current_npc['name']} by providing the {npc_needed_object}.", TerminalFormatter)

                        # Update hint for this NPC as their need is met
                        if chat_session:
                            new_hint = f"You successfully helped {current_npc['name']} with the {npc_needed_object}. They might have new things to discuss or no longer need immediate help with that."
                            chat_session.set_player_hint(new_hint)
                    
                    # Clear the flag from the state so it's not processed again
                    if 'item_given_to_npc_this_turn' in current_game_state: # Check if key exists
                         del current_game_state['item_given_to_npc_this_turn'] # This might not be the right place if state is returned
                    # This flag should be managed carefully to apply only once per give action.
                    # Better if the flag is consumed from the handler_result and not persisted in current_game_state across turns.
                    # The solution for `handle_give` setting state['item_given_to_npc_this_turn'] and then `main_core` using it after the NPC's textual reaction is tricky.
                    # `handle_give` sets this key. `process_input_revised` passes the state through.
                    # `main_core` consumes it.
                    # If `process_input_revised` returns the *new state*, `main_core` should check it there.
                    # The state dict `returned_state_from_command` is what `main_core` should inspect.
                    
                    # Remove the flag from the main loop's perspective of the state for the *next* iteration
                    # This specific logic for clearing the flag from `returned_state_from_command`
                    # means that the main `current_game_state` used to build the prompt for the
                    # *next* turn will not have this flag.
                    if 'item_given_to_npc_this_turn' in returned_state_from_command:
                        del returned_state_from_command['item_given_to_npc_this_turn'] 


        except KeyboardInterrupt: # ... (keep existing KeyboardInterrupt) ...
            print(f"\n{TerminalFormatter.DIM}Interruption detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break
        except EOFError: # ... (keep existing EOFError) ...
            print(f"\n{TerminalFormatter.DIM}EOF detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break

        except Exception as e: # ... (keep existing general Exception) ...
            print(f"\n{TerminalFormatter.RED}❌ Unexpected Error in Main Loop: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            print(f"{TerminalFormatter.YELLOW}An error occurred. Attempting to continue...{TerminalFormatter.RESET}")


    # --- End of Session Cleanup ---
    # ... (keep existing cleanup) ...
    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    if chat_session and current_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Final stats for ({current_npc.get('name', 'N/A')}):{TerminalFormatter.RESET}")
        print(chat_session.format_session_stats())
    else:
        print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")

