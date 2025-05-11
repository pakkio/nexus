# Path: command_processor.py

import json
import random
import traceback
from typing import Dict, List, Any, Optional, Tuple

import session_utils # Import the session_utils module

# Assume necessary classes/functions are passed in 'state' or imported globally if shared
# from terminal_formatter import TerminalFormatter (from state)
# from chat_manager import ChatSession (class from state)
# from db_manager import DbManager (from state)
# from main_utils import get_help_text, format_npcs_list (from state or direct import)

RANDOM_TALK_SYNTAX = '.'
HandlerResult = Dict[str, Any]

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /exit command."""
    TerminalFormatter = state['TerminalFormatter']
    player_id = state['player_id']
    print(f"\n{TerminalFormatter.DIM}Saving last conversation (if active)...{TerminalFormatter.RESET}")
    session_utils.save_current_conversation(
        state['db'], player_id, state['current_npc'], state['chat_session'], TerminalFormatter
    )
    print(f"{TerminalFormatter.YELLOW}Arrivederci! Leaving Eldoria... for now.{TerminalFormatter.RESET}")
    return {'status': 'exit'}

def handle_help(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /help command."""
    # Assuming get_help_text is available, e.g., from main_utils
    try:
        from main_utils import get_help_text
        print(get_help_text())
    except ImportError:
        print("Help text unavailable.")
    return {'status': 'ok', 'continue_loop': True}

def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    """Handles the /go command with partial matching and auto-talk to default NPC."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc_old = state['current_npc'] # NPC before moving
    chat_session_old = state['chat_session'] # Session before moving

    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    target_area_prefix = args.lower()
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter) # Refresh for current data
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [area for area in known_areas if area.lower().startswith(target_area_prefix)]

    new_state = {'status': 'ok', 'continue_loop': True}

    if len(matches) == 1:
        matched_area = matches[0]
        print(f"{TerminalFormatter.DIM}Unique area match found: {matched_area}{TerminalFormatter.RESET}")
        print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
        session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
        print(f"{TerminalFormatter.CYAN}Moving to area: {matched_area}...{TerminalFormatter.RESET}")

        # Base state update for moving
        new_state.update({
            'current_area': matched_area,
            'current_npc': None,
            'chat_session': None
        })

        # --- MODIFIED: Attempt to auto-start conversation with default NPC ---
        default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
            db,
            player_id,
            matched_area,
            state['model_name'],
            state['story'],
            state['ChatSession'], # Pass ChatSession class from state
            TerminalFormatter
        )

        if default_npc_data and default_session:
            new_state['current_npc'] = default_npc_data
            new_state['chat_session'] = default_session
            # auto_start_default_npc_conversation handles printing its intro messages
        else:
            # No default NPC found or error during auto-start.
            # auto_start_default_npc_conversation prints "No default NPC found..."
            # So, if no conversation was started, provide general guidance.
            if not (default_npc_data and default_session) :
                print(f"{TerminalFormatter.YELLOW}You are now in {matched_area}. Use {TerminalFormatter.BOLD}/talk <npc_name_or_prefix|.>{TerminalFormatter.YELLOW} or {TerminalFormatter.BOLD}/who{TerminalFormatter.YELLOW} to interact.")

    elif len(matches) > 1:
        print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area prefix '{args}'. Matches:{TerminalFormatter.RESET}")
        for area_match in sorted(matches):
            print(f"  {TerminalFormatter.DIM}- {area_match}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}Please be more specific using /go <full_area_name>.{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.YELLOW}⚠️ Area starting with '{args}' not found or has no known NPCs.{TerminalFormatter.RESET}")
        if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(sorted(known_areas))}{TerminalFormatter.RESET}")

    return new_state

def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    """Handles the /talk command with partial matching and random selection."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_area = state['current_area']
    current_npc_old = state['current_npc']
    chat_session_old = state['chat_session']
    # Get necessary items from state for starting a new session
    model_name_for_session = state['model_name']
    story_for_session = state['story']
    ChatSession_class = state['ChatSession']

    if not current_area:
        print(f"{TerminalFormatter.YELLOW}You need to be in an area first. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}
    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /talk <npc_name_or_prefix | . > ({TerminalFormatter.BOLD}.{TerminalFormatter.YELLOW} for random){TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    target_npc_info = None
    initiate_talk = False
    new_state = {'status': 'ok', 'continue_loop': True}

    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_current_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()]

    if args == RANDOM_TALK_SYNTAX:
        if not npcs_in_current_area:
            print(f"{TerminalFormatter.YELLOW}⚠️ No NPCs found in {current_area} to talk to randomly.{TerminalFormatter.RESET}")
        else:
            target_npc_info = random.choice(npcs_in_current_area)
            initiate_talk = True
    else:
        target_npc_prefix = args.lower()
        matches = [n for n in npcs_in_current_area if n.get('name','').lower().startswith(target_npc_prefix)]
        if len(matches) == 1:
            target_npc_info = matches[0]
            initiate_talk = True
        elif len(matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous NPC prefix '{args}'. Matches in {current_area}:{TerminalFormatter.RESET}")
            for npc_match in sorted(matches, key=lambda x: x['name']):
                print(f"  {TerminalFormatter.DIM}- {npc_match.get('name')} ({npc_match.get('role', '???')}){TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Please be more specific.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.YELLOW}⚠️ NPC starting with '{args}' not found in {current_area}.{TerminalFormatter.RESET}")
            if npcs_in_current_area: print(f"{TerminalFormatter.DIM}NPCs here: {', '.join(sorted(n['name'] for n in npcs_in_current_area))}{TerminalFormatter.RESET}")

    if initiate_talk and target_npc_info:
        if current_npc_old and current_npc_old.get('code') == target_npc_info.get('code'):
            print(f"{TerminalFormatter.DIM}You are already talking to {target_npc_info['name']}.{TerminalFormatter.RESET}")
        else:
            print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)

            correct_npc_name = target_npc_info['name']
            # --- MODIFIED: Use new session_utils.start_conversation_with_specific_npc ---
            npc_data, new_chat_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, current_area, correct_npc_name, model_name_for_session, story_for_session, ChatSession_class, TerminalFormatter
            )

            if npc_data and new_chat_session:
                new_state.update({
                    'current_npc': npc_data,
                    'chat_session': new_chat_session
                })
                # Intro printing is now handled by start_conversation_with_specific_npc
            else:
                # Error messages are handled within the called function
                new_state.update({'current_npc': None, 'chat_session': None})
    return new_state

def handle_who(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /who command."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    current_area = state['current_area']

    if not current_area:
        print(f"{TerminalFormatter.YELLOW}You are not in any specific area. Use /go <area> first.{TerminalFormatter.RESET}")
    else:
        all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
        npcs_in_current_area = [npc for npc in all_known_npcs if npc.get('area', '').lower() == current_area.lower()]
        if not npcs_in_current_area:
            print(f"\n{TerminalFormatter.YELLOW}No known NPCs found in {current_area}.{TerminalFormatter.RESET}")
        else:
            print(f"\n{TerminalFormatter.YELLOW}NPCs in '{current_area}':{TerminalFormatter.RESET}")
            for npc_info in sorted(npcs_in_current_area, key=lambda x: x.get('name','').lower()):
                print(f"  {TerminalFormatter.DIM}- {npc_info.get('name', '???')} ({npc_info.get('role', '???')}){TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /whereami command."""
    TerminalFormatter = state['TerminalFormatter']
    current_area = state['current_area']
    current_npc = state['current_npc']
    loc_msg = f"Location: {TerminalFormatter.BOLD}{current_area or 'Nowhere (Use /go)'}{TerminalFormatter.RESET}"
    npc_name_display = current_npc['name'] if current_npc and 'name' in current_npc else 'Nobody (Use /talk or /go)'
    npc_msg = f"Talking to: {TerminalFormatter.BOLD}{npc_name_display}{TerminalFormatter.RESET}"
    print(f"\n{TerminalFormatter.CYAN}{loc_msg}\n{npc_msg}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /npcs command."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    try:
        from main_utils import format_npcs_list # Assuming format_npcs_list is in main_utils
        print(f"\n{TerminalFormatter.DIM}Fetching list of all known NPCs...{TerminalFormatter.RESET}")
        all_npcs_list = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
        if not all_npcs_list:
            print(f"{TerminalFormatter.YELLOW}No NPC data could be loaded.{TerminalFormatter.RESET}")
        else:
            print(format_npcs_list(all_npcs_list))
    except ImportError:
        print(f"{TerminalFormatter.RED}Error: main_utils.format_npcs_list not found.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /stats command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']
    format_stats_func = state['format_stats'] # Get from state

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}")
    else:
        last_stats = chat_session.get_last_stats()
        if last_stats:
            print(f"\n{TerminalFormatter.DIM}{'-'*20} Last Turn Stats {'-'*20}{TerminalFormatter.RESET}")
            print(format_stats_func(last_stats))
        else:
            print(f"{TerminalFormatter.YELLOW}No stats available for the last interaction.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /session_stats command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}")
    else:
        print(f"\n{TerminalFormatter.DIM}{'-'*20} Current Session Stats {'-'*20}{TerminalFormatter.RESET}")
        print(chat_session.format_session_stats())
    return {'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    """Handles the /clear command."""
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    if not chat_session:
        print(f"{TerminalFormatter.YELLOW}You are not in an active conversation to clear.{TerminalFormatter.RESET}")
    else:
        chat_session.clear_memory() # clear_memory() in ChatSession prints its own confirmation
    return {'status': 'ok', 'continue_loop': True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> HandlerResult:
    """
    Process user input and dispatch to appropriate handler functions.
    """
    result = {'status': 'ok', 'continue_loop': True}
    if not user_input.strip():
        return result

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    format_stats_func = state.get('format_stats') # For auto-showing stats after LLM call

    if user_input.startswith('/'):
        parts = user_input[1:].split(None, 1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        command_handlers = {
            'exit': handle_exit, 'quit': handle_exit,
            'help': handle_help,
            'go': handle_go,
            'talk': handle_talk,
            'who': handle_who,
            'whereami': handle_whereami,
            'npcs': handle_npcs,
            'stats': handle_stats,
            'session_stats': handle_session_stats,
            'clear': handle_clear,
        }

        try:
            if command in command_handlers:
                return command_handlers[command](state) if command in ['exit', 'help', 'who', 'whereami', 'npcs', 'stats', 'session_stats', 'clear'] else command_handlers[command](args, state)
            elif command == 'history': # Special case not requiring args in the same way
                if chat_session:
                    print(f"\n{TerminalFormatter.DIM}--- Conversation History (JSON) ---{TerminalFormatter.RESET}")
                    history_json = json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)
                    print(history_json)
                else:
                    print(f"{TerminalFormatter.YELLOW}No active conversation to show history for.{TerminalFormatter.RESET}")
                return {'status': 'ok', 'continue_loop': True}
            else:
                print(f"{TerminalFormatter.YELLOW}Unknown command '/{command}'. Type /help for available commands.{TerminalFormatter.RESET}")
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error processing command '/{command}': {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() # Uncomment for more detailed debug

    elif current_npc and chat_session:
        try:
            print(f"{TerminalFormatter.DIM}Processing your message...{TerminalFormatter.RESET}")
            response, stats = chat_session.ask(
                user_input,
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            print() # Spacing after LLM output

            if state.get('auto_show_stats', False) and stats and format_stats_func:
                print(format_stats_func(stats))
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error in conversation: {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() # Uncomment for more detailed debug

    else: # Not in a conversation and not a command
        print(f"{TerminalFormatter.YELLOW}You are not currently talking to anyone. Use /go to navigate, then /talk or wait for a conversation to start.{TerminalFormatter.RESET}")

    return result