# Path: command_processor.py

import json
import random
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Import utilities from the new module
import session_utils

# Assume necessary classes/functions are passed or imported globally
# from terminal_formatter import TerminalFormatter
# from chat_manager import ChatSession, format_stats
# from db_manager import DbManager
# from main_utils import get_help_text, format_npcs_list

# Define constants
RANDOM_TALK_SYNTAX = '.' # source [48]
# Return type hints for state updates can be more specific if using TypedDict or a State class
HandlerResult = Dict[str, Any] # Example: {'status': 'ok', 'new_area': 'Tavern', ... 'exit': False}

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /exit command."""
    TerminalFormatter = state['TerminalFormatter']
    player_id = state['player_id'] # Get player_id
    print(f"\n{TerminalFormatter.DIM}Saving last conversation (if active)...{TerminalFormatter.RESET}")
    session_utils.save_current_conversation(
        state['db'], player_id, state['current_npc'], state['chat_session'], TerminalFormatter # MODIFIED
    )
    print(f"{TerminalFormatter.YELLOW}Arrivederci! Leaving Eldoria... for now.{TerminalFormatter.RESET}")
    return {'status': 'exit'} # Signal to main loop to exit

def handle_help(state: Dict[str, Any]) -> HandlerResult: # source [49]
    """Handles the /help command."""
    from main_utils import get_help_text # Import here or pass if preferred
    print(get_help_text())
    return {'status': 'ok', 'continue_loop': True} # Continue loop normally

def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    """Handles the /go command with partial matching."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id'] # Get player_id
    current_npc = state['current_npc']
    chat_session = state['chat_session']

    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True} # source [50]

    target_area_prefix = args.lower()
    # Refresh NPC list to get current areas
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [area for area in known_areas if area.lower().startswith(target_area_prefix)]

    new_state = {'status': 'ok', 'continue_loop': True} # Default return

    if len(matches) == 1:
        matched_area = matches[0]
        print(f"{TerminalFormatter.DIM}Unique match found: {matched_area}{TerminalFormatter.RESET}")
        print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}") # source [51]
        session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter) # MODIFIED
        print(f"{TerminalFormatter.CYAN}Moving to area: {matched_area}...{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}You are now in {matched_area}. Use {TerminalFormatter.BOLD}/talk <npc_name_or_prefix|.>{TerminalFormatter.YELLOW} or {TerminalFormatter.BOLD}/who{TerminalFormatter.YELLOW}.") # source [52]
        # Update state to be returned
        new_state.update({
            'current_area': matched_area,
            'current_npc': None,
            'chat_session': None
        })
    elif len(matches) > 1:
        print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area prefix '{args}'. Matches:{TerminalFormatter.RESET}")
        for area_match in sorted(matches): # source [53]
            print(f"  {TerminalFormatter.DIM}- {area_match}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}Please be more specific using /go <full_area_name>.{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.YELLOW}⚠️ Area starting with '{args}' not found or has no known NPCs.{TerminalFormatter.RESET}")
        if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(sorted(known_areas))}{TerminalFormatter.RESET}")

    return new_state

def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    """Handles the /talk command with partial matching and random selection."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db'] # source [54]
    player_id = state['player_id'] # Get player_id
    current_area = state['current_area']
    current_npc = state['current_npc']
    chat_session = state['chat_session']
    model_name = state['model_name']
    story = state['story']
    ChatSession = state['ChatSession'] # Pass class reference

    if not current_area:
        print(f"{TerminalFormatter.YELLOW}You need to be in an area first. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.RESET}") # source [55]
        return {'status': 'ok', 'continue_loop': True}
    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /talk <npc_name_or_prefix | . > ({TerminalFormatter.BOLD}.{TerminalFormatter.YELLOW} for random){TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    target_npc_info = None
    initiate_talk = False
    new_state = {'status': 'ok', 'continue_loop': True} # Default updates

    # Refresh NPC list for current operations
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_current_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()] # source [56]

    if args == RANDOM_TALK_SYNTAX:
        print(f"{TerminalFormatter.DIM}Attempting to talk to a random NPC in '{current_area}'...{TerminalFormatter.RESET}")
        if not npcs_in_current_area:
            print(f"{TerminalFormatter.YELLOW}⚠️ No NPCs found in {current_area} to talk to randomly.{TerminalFormatter.RESET}")
        else:
            target_npc_info = random.choice(npcs_in_current_area)
            print(f"{TerminalFormatter.DIM}Randomly selected: {target_npc_info['name']}{TerminalFormatter.RESET}")
            initiate_talk = True # source [57]
    else:
        # Partial/Full Name Matching
        target_npc_prefix = args.lower()
        print(f"{TerminalFormatter.DIM}Looking for NPCs starting with '{args}' in '{current_area}'...{TerminalFormatter.RESET}")
        matches = [n for n in npcs_in_current_area if n.get('name','').lower().startswith(target_npc_prefix)]

        if len(matches) == 1:
            target_npc_info = matches[0]
            print(f"{TerminalFormatter.DIM}Unique match found: {target_npc_info['name']}{TerminalFormatter.RESET}") # source [58]
            initiate_talk = True
        elif len(matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous NPC prefix '{args}'. Matches in {current_area}:{TerminalFormatter.RESET}") # source [59]
            for npc_match in sorted(matches, key=lambda x: x['name']):
                print(f"  {TerminalFormatter.DIM}- {npc_match.get('name')} ({npc_match.get('role', '???')}){TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Please be more specific using /talk <full_npc_name>.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.YELLOW}⚠️ NPC starting with '{args}' not found in {current_area}.{TerminalFormatter.RESET}")
            if npcs_in_current_area: print(f"{TerminalFormatter.DIM}NPCs here: {', '.join(sorted(n['name'] for n in npcs_in_current_area))}{TerminalFormatter.RESET}") # source [60]

    # --- Initiate conversation if a unique/random NPC was selected ---
    if initiate_talk and target_npc_info:
        if current_npc and current_npc.get('code') == target_npc_info.get('code'):
            print(f"{TerminalFormatter.DIM}You are already talking to {target_npc_info['name']}.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter) # MODIFIED
            correct_npc_name = target_npc_info['name'] # source [61]
            print(f"{TerminalFormatter.DIM}Starting conversation with '{correct_npc_name}'...{TerminalFormatter.RESET}")

            # Call the session utility to load/prepare
            npc_data, new_session = session_utils.load_and_prepare_conversation(
                db, player_id, current_area, correct_npc_name, model_name, story, ChatSession, TerminalFormatter # MODIFIED # source [62]
            )

            if npc_data and new_session:
                # Update state to be returned
                new_state.update({
                    'current_npc': npc_data,
                    'chat_session': new_session
                }) # source [63]
                # Print intro messages (part of the handler's responsibility)
                print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_data.get('name', 'NPC').upper()} IN {current_area.upper()} {TerminalFormatter.RESET}")
                print(f"{TerminalFormatter.DIM}Type '/exit' to leave, '/help' for commands.{TerminalFormatter.RESET}")
                print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}\n")
                print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{npc_data['name']} > {TerminalFormatter.RESET}") # source [64]
                opening_line = session_utils.get_npc_opening_line(npc_data, TerminalFormatter)
                print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
                print()
            else:
                print(f"{TerminalFormatter.RED}❌ Failed to start conversation with {correct_npc_name}. Check logs.{TerminalFormatter.RESET}") # source [65]
                # Reset state if loading failed
                new_state.update({'current_npc': None, 'chat_session': None})

    return new_state # Return potentially updated state

def handle_who(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /who command."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    current_area = state['current_area']

    if not current_area:
        print(f"{TerminalFormatter.YELLOW}You are not in any specific area. Use /go <area> first.{TerminalFormatter.RESET}") # source [66]
    else:
        all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
        npcs_in_current_area = [npc for npc in all_known_npcs if npc.get('area', '').lower() == current_area.lower()]
        if not npcs_in_current_area:
            print(f"\n{TerminalFormatter.YELLOW}No known NPCs found in {current_area}.{TerminalFormatter.RESET}")
        else:
            print(f"\n{TerminalFormatter.YELLOW}NPCs in '{current_area}':{TerminalFormatter.RESET}")
            for npc_info in sorted(npcs_in_current_area, key=lambda x: x.get('name','').lower()): # source [67]
                print(f"  {TerminalFormatter.DIM}- {npc_info.get('name', '???')} ({npc_info.get('role', '???')}){TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /whereami command."""
    TerminalFormatter = state['TerminalFormatter']
    current_area = state['current_area']
    current_npc = state['current_npc']
    loc_msg = f"Location: {TerminalFormatter.BOLD}{current_area or 'Nowhere (Use /go)'}{TerminalFormatter.RESET}"
    npc_msg = f"Talking to: {TerminalFormatter.BOLD}{current_npc['name'] if current_npc else 'Nobody (Use /talk)'}{TerminalFormatter.RESET}"
    print(f"\n{TerminalFormatter.CYAN}{loc_msg}\n{npc_msg}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True} # source [68]

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /npcs command."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    from main_utils import format_npcs_list # Import here or pass

    print(f"\n{TerminalFormatter.DIM}Fetching list of all known NPCs...{TerminalFormatter.RESET}")
    all_npcs_list = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    if not all_npcs_list:
        print(f"{TerminalFormatter.YELLOW}No NPC data could be loaded.{TerminalFormatter.RESET}")
    else:
        print(format_npcs_list(all_npcs_list))
    return {'status': 'ok', 'continue_loop': True}

def handle_stats(state: Dict[str, Any]) -> HandlerResult: # source [69]
    """Handles the /stats command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']
    format_stats = state['format_stats'] # Pass function reference

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}")
    else:
        last_stats = chat_session.get_last_stats()
        if last_stats:
            print(f"\n{TerminalFormatter.DIM}{'-'*20} Last Turn Stats {'-'*20}{TerminalFormatter.RESET}") # source [70]
            print(format_stats(last_stats))
        else:
            print(f"{TerminalFormatter.YELLOW}No stats available for the last interaction.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /session_stats command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}") # source [71]
    else:
        print(f"\n{TerminalFormatter.DIM}{'-'*20} Current Session Stats {'-'*20}{TerminalFormatter.RESET}")
        print(chat_session.format_session_stats())
    return {'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /clear command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    # Added logic from original handle_clear
    if not chat_session:
        print(f"{TerminalFormatter.YELLOW}You are not in an active conversation to clear.{TerminalFormatter.RESET}")
    else:
        chat_session.clear_memory() # clear_memory() prints its own confirmation
        # No need to print additional confirmation here if clear_memory handles it
    return {'status': 'ok', 'continue_loop': True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> HandlerResult:
    """
    Process user input and dispatch to appropriate handler functions.
    Args: # source [72]
        user_input: The raw user input string
        state: Current application state dictionary

    Returns:
        HandlerResult: Dictionary with updated state information
    """
    # Default result (continue normally)
    result = {'status': 'ok', 'continue_loop': True}

    # Empty input
    if not user_input.strip():
        return result

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc') # source [73]

    # Handle commands (starting with /)
    if user_input.startswith('/'):
        parts = user_input[1:].split(None, 1)  # Split into command and args
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        try:
            # Dispatch to appropriate handler based on command
            if command == 'exit' or command == 'quit': # source [74]
                return handle_exit(state)
            elif command == 'help':
                return handle_help(state)
            elif command == 'go':
                return handle_go(args, state)
            elif command == 'talk': # source [75]
                return handle_talk(args, state)
            elif command == 'who':
                return handle_who(state)
            elif command == 'whereami':
                return handle_whereami(state)
            elif command == 'npcs': # source [76]
                return handle_npcs(state)
            elif command == 'stats':
                return handle_stats(state)
            elif command == 'session_stats':
                return handle_session_stats(state)
            elif command == 'clear': # source [77]
                return handle_clear(state)
            # ADDED /history command from original main_core
            elif command == 'history':
                if chat_session:
                    print(f"\n{TerminalFormatter.DIM}--- Conversation History (JSON) ---{TerminalFormatter.RESET}")
                    # Assuming get_history() returns List[Dict[str, str]]
                    history_json = json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)
                    print(history_json)
                else:
                    print(f"{TerminalFormatter.YELLOW}No active conversation to show history for.{TerminalFormatter.RESET}")
                return {'status': 'ok', 'continue_loop': True}
            else:
                # Unknown command
                print(f"{TerminalFormatter.YELLOW}Unknown command '/{command}'. Type /help for available commands.{TerminalFormatter.RESET}") # source [78]
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error processing command '/{command}': {e}{TerminalFormatter.RESET}")
            traceback.print_exc()

    # Handle normal dialogue (if in active conversation)
    elif current_npc and chat_session:
        try:
            # Send the message to the current NPC via the chat session
            print(f"{TerminalFormatter.DIM}Processing your message...{TerminalFormatter.RESET}") # source [79]
            # MODIFIED to use chat_session.ask which aligns with ChatSession class structure
            response, stats = chat_session.ask(
                user_input,
                stream=state.get('use_stream', True),
                collect_stats=True # Always collect, decision to show is separate
            )

            # Formatting and printing is handled by llm_wrapper via chat_session.ask
            # if streaming is True. If streaming is False, llm_wrapper also prints.
            # So, no explicit print(TerminalFormatter.format_terminal_text(response...)) here.
            # An empty line for spacing after LLM output (which includes its own newline)
            print()

            if state.get('auto_show_stats', False) and stats:
                print(format_stats(stats)) # Use the passed format_stats function reference
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error in conversation: {e}{TerminalFormatter.RESET}") # source [80]
            traceback.print_exc()

    # Not in a conversation and not a command # source [81]
    else:
        print(f"{TerminalFormatter.YELLOW}You are not currently talking to anyone. Use /go to navigate to an area, then /talk to speak with an NPC.{TerminalFormatter.RESET}") # source [82]

    return result