import json
import traceback
from typing import Dict, Any
import time # Added import for the problematic line, or this line needs fixing.

# Import handlers from the new subdirectory

from .command_handlers import (
    handle_exit, handle_help, handle_go, handle_talk, handle_who, handle_whereami,
    handle_npcs, handle_areas, handle_stats, handle_session_stats, handle_clear,
    handle_hint, handle_endhint, handle_inventory, handle_give,
    handle_profile, handle_profile_for_npc, handle_history
)

# Import shared utilities

from .command_handler_utils import HandlerResult, _add_profile_action

import session_utils # Still needed for get_npc_color etc. in process_input_revised

# The main command map

command_handlers_map: Dict[str, callable] = {
    'exit': handle_exit, 'quit': handle_exit,
    'help': handle_help,
    'go': handle_go,
    'areas': handle_areas,
    'talk': handle_talk,
    'who': handle_who,
    'whereami': handle_whereami,
    'npcs': handle_npcs,
    'hint': handle_hint,
    'endhint': handle_endhint,
    'inventory': handle_inventory, 'inv': handle_inventory,
    'give': handle_give,
    'profile': handle_profile,
    'profile_for_npc': handle_profile_for_npc,
    'stats': handle_stats,
    'session_stats': handle_session_stats,
    'clear': handle_clear,
    'history': handle_history,
}

def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes user input, dispatching to command handlers or LLM.
    This function remains largely the same but calls imported handlers.
    """
    state['npc_made_new_response_this_turn'] = False # Reset flag
    if not user_input.strip(): # Ignore empty input
        return state # No change, continue loop

    TF = state.get('TerminalFormatter') # Get from state
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    fmt_stats_func = state.get('format_stats') # Function from state
    is_in_lyra_hint_mode = state.get('in_lyra_hint_mode', False)
    debug_mode = state.get('debug_mode', False)

    command_processed_this_turn = False

    if user_input.startswith('/'):
        parts = user_input[1:].split(None, 1)
        command = parts[0].lower() if parts else ""
        args_str = parts[1] if len(parts) > 1 else ""

        try:
            if command in command_handlers_map:
                handler_func = command_handlers_map[command]
                # Handlers like 'go', 'talk', 'give' take args_str
                if command in ['go', 'talk', 'give']:
                    state = handler_func(args_str, state)
                else: # Most handlers just take state
                    state = handler_func(state)

                if state.get('status') == 'exit': # Check if handler requested exit
                    return state
                command_processed_this_turn = True
            else:
                print(f"{TF.YELLOW}Unknown command '/{command}'. Try /help.{TF.RESET}")
                command_processed_this_turn = True # Mark as processed to avoid LLM call
        except Exception as e:
            print(f"{TF.RED}Error processing command '/{command}': {type(e).__name__} - {e}{TF.RESET}")
            if debug_mode:
                traceback.print_exc()
            command_processed_this_turn = True # Mark as processed on error too
    else: # Not a command, so it's dialogue for the LLM
        # --- Dialogue processing / NPC turn ---
        # This part triggers if input was not a command OR if a command forces an NPC turn
        # (e.g., after /give, the NPC should react).

        force_npc_turn_after_command = state.get('force_npc_turn_after_command', False)
        if force_npc_turn_after_command:
            state.pop('force_npc_turn_after_command', None) # Consume the flag

        needs_llm_call = False
        prompt_for_llm = user_input # Default to user's text input

        if not command_processed_this_turn: # Was dialogue
            needs_llm_call = True
        elif force_npc_turn_after_command and not is_in_lyra_hint_mode: # Command that needs NPC reaction
            # Special prompt to make NPC react to player's action (e.g., giving an item)
            prompt_for_llm = "[NPC reacts to player's action]"
            needs_llm_call = True

        # If in Lyra hint mode and user typed dialogue (not a command handled above), it's for Lyra

        if is_in_lyra_hint_mode and not command_processed_this_turn:
            needs_llm_call = True

        if needs_llm_call:
            if current_npc and chat_session:
                npc_name_for_prompt = current_npc.get('name', 'NPC')
                if is_in_lyra_hint_mode: # Adjust name if consulting Lyra
                    npc_name_for_prompt = "Lyra (Consultation)"

                npc_color = session_utils.get_npc_color(current_npc.get('name', 'NPC'), TF)
                if is_in_lyra_hint_mode: # Lyra's specific color for consultation
                    npc_color = session_utils.get_npc_color("Lyra", TF)

                # Only print NPC prompt if it's not Lyra being re-prompted by /hint itself
                if not (is_in_lyra_hint_mode and command_processed_this_turn and command == 'hint'):
                    print(f"\n{TF.BOLD}{npc_color}{npc_name_for_prompt} > {TF.RESET}")

                try:
                    _response_text, stats = chat_session.ask(
                        prompt_for_llm, current_npc.get('name', 'NPC'), # Pass original NPC name for placeholder if needed
                        state.get('use_stream', True), True # collect_stats is True
                    )
                    if not _response_text.strip() and not (stats and stats.get("error")):
                        # Handle empty but non-error LLM responses with a placeholder
                        placeholder_msg = f"{TF.DIM}{TF.ITALIC}*{npc_name_for_prompt} seems to ponder for a moment...*{TF.RESET}"
                        if is_in_lyra_hint_mode: # Specific placeholder for Lyra
                            placeholder_msg = f"{TF.DIM}{TF.ITALIC}*Lyra ponders deeply...*{TF.RESET}"
                        print(placeholder_msg)

                    state['npc_made_new_response_this_turn'] = True # Mark that NPC responded
                    if _response_text.strip(): # Only add to profile log if there was actual content
                        _add_profile_action(state, f"NPC Response from {npc_name_for_prompt}: '{_response_text[:50]}{'...' if len(_response_text) > 50 else ''}'")

                    if state.get('auto_show_stats', False) and stats and fmt_stats_func:
                        print(fmt_stats_func(stats)) # Display stats if enabled

                    # If in Lyra hint mode, update the cache with the new interaction
                    if is_in_lyra_hint_mode and state.get('lyra_hint_cache'):
                        state['lyra_hint_cache']['lyra_chat_history'] = chat_session.get_history()
                        # The following line was 'state['command_handler_utils.time'].time()'.
                        # 'command_handler_utils' doesn't expose 'time' this way.
                        # Assuming standard 'time.time()' is intended.
                        state['lyra_hint_cache']['timestamp'] = time.time()

                except Exception as e:
                    state['npc_made_new_response_this_turn'] = False # Mark as no response on error
                    print(f"{TF.RED}LLM Chat Error with {npc_name_for_prompt}: {type(e).__name__} - {e}{TF.RESET}")
                    if debug_mode:
                        traceback.print_exc()
            elif user_input: # User typed something but not in a conversation
                print(f"{TF.YELLOW}You're not talking to anyone. Use /go to move to an area, then /talk <npc_name>.{TF.RESET}")

    return state