# Path: command_processor.py

import json
import random
import traceback # Keep if used elsewhere
from typing import Dict, List, Any, Optional, Tuple

import session_utils # Ensure this is imported

# Assume TerminalFormatter, etc., are passed in 'state'
RANDOM_TALK_SYNTAX = '.'
HandlerResult = Dict[str, Any] # Example: {'status': 'ok', 'new_area': 'Tavern', ... 'exit': False}

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    player_id = state['player_id']
    # For summarization, save_current_conversation would need llm_wrapper and model_name from state
    # For now, assuming it saves full history or the hint logic doesn't make it async
    print(f"\n{TerminalFormatter.DIM}Saving last conversation (if active)...{TerminalFormatter.RESET}")
    session_utils.save_current_conversation(
        state['db'], player_id, state['current_npc'], state['chat_session'], TerminalFormatter
        # If save becomes async or needs llm_wrapper:
        # state.get('llm_wrapper'), state.get('model_name')
    )
    print(f"{TerminalFormatter.YELLOW}Arrivederci! Leaving Eldoria... for now.{TerminalFormatter.RESET}")
    return {'status': 'exit'}

def handle_help(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter'] # Not used in current help text, but good practice
    try:
        from main_utils import get_help_text # Assuming main_utils is available
        print(get_help_text())
    except ImportError:
        print(f"{TerminalFormatter.RED}Error: Help utility not found.{TerminalFormatter.RESET}")
        print("Available commands: /exit, /go <area>, /talk <npc>, /who, /whereami, /npcs, /stats, /session_stats, /clear, /history, /hint, /profile")
    return {'status': 'ok', 'continue_loop': True}

# --- NEW: handle_hint ---
def handle_hint(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be in an active conversation to get a relevant hint.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    # Use the get_player_hint method from ChatSession
    hint_text = chat_session.get_player_hint() # Relies on ChatSession.current_player_hint being set

    if hint_text:
        print(f"\n{TerminalFormatter.BRIGHT_CYAN}{TerminalFormatter.BOLD}Hint regarding {current_npc.get('name', 'your current interaction')}:{TerminalFormatter.RESET}")
        # Format the hint text nicely
        formatted_hint = TerminalFormatter.format_terminal_text(hint_text, width=TerminalFormatter.get_terminal_width() - 4)
        for line in formatted_hint.split('\n'):
            print(f"  {TerminalFormatter.CYAN}➢ {line}{TerminalFormatter.RESET}")
    else:
        # This part should ideally not be reached if set_player_hint always provides something
        print(f"{TerminalFormatter.YELLOW}No specific hint available for {current_npc.get('name', 'this interaction')} right now. Try exploring or talking more!{TerminalFormatter.RESET}")

    return {'status': 'ok', 'continue_loop': True}
# --- END NEW ---

def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep existing implementation, but ensure it calls session_utils.auto_start_default_npc_conversation) ...
    # This was provided in the previous step and should be correct.
    # Make sure the print message when no default NPC is found is clear.
    # The auto_start_default_npc_conversation in session_utils now handles printing its own status.
    # So, handle_go might only need a generic "You are now in X" if no conversation started.
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc_old = state['current_npc']
    chat_session_old = state['chat_session']

    if not args: # ... (no args message) ...
        print(f"{TerminalFormatter.YELLOW}Usage: /go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}


    target_area_prefix = args.lower()
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [area for area in known_areas if area.lower().startswith(target_area_prefix)]
    new_state = {'status': 'ok', 'continue_loop': True} # Default return

    if len(matches) == 1:
        matched_area = matches[0]
        print(f"{TerminalFormatter.DIM}Unique area match found: {matched_area}{TerminalFormatter.RESET}")
        print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
        session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
        print(f"{TerminalFormatter.CYAN}Moving to area: {matched_area}...{TerminalFormatter.RESET}")

        new_state.update({
            'current_area': matched_area,
            'current_npc': None,
            'chat_session': None
        })

        default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
            db, player_id, matched_area, state['model_name'], state['story'],
            state['ChatSession'], TerminalFormatter
        )
        if default_npc_data and default_session:
            new_state['current_npc'] = default_npc_data
            new_state['chat_session'] = default_session
        else: # No default NPC or error, auto_start prints its own message
            if not (default_npc_data and default_session) : # Extra check if needed
                print(f"{TerminalFormatter.YELLOW}You are now in {matched_area}. Use {TerminalFormatter.BOLD}/talk <npc_name_or_prefix|.>{TerminalFormatter.YELLOW} or {TerminalFormatter.BOLD}/who{TerminalFormatter.YELLOW} to interact.")


    elif len(matches) > 1: # ... (ambiguous message) ...
        print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area prefix '{args}'. Matches:{TerminalFormatter.RESET}")
        for area_match in sorted(matches): print(f"  {TerminalFormatter.DIM}- {area_match}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}Please be more specific using /go <full_area_name>.{TerminalFormatter.RESET}")

    else: # ... (not found message) ...
        print(f"{TerminalFormatter.YELLOW}⚠️ Area starting with '{args}' not found or has no known NPCs.{TerminalFormatter.RESET}")
        if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(sorted(known_areas))}{TerminalFormatter.RESET}")

    return new_state


def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep existing implementation, but ensure it calls session_utils.start_conversation_with_specific_npc) ...
    # This was provided in the previous step and should be correct.
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_area = state['current_area']
    current_npc_old = state['current_npc']
    chat_session_old = state['chat_session']
    model_name_for_session = state['model_name']
    story_for_session = state['story']
    ChatSession_class = state['ChatSession']

    if not current_area: # ... (no area message) ...
        print(f"{TerminalFormatter.YELLOW}You need to be in an area first. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    if not args: # ... (no args message) ...
        print(f"{TerminalFormatter.YELLOW}Usage: /talk <npc_name_or_prefix | . > ({TerminalFormatter.BOLD}.{TerminalFormatter.YELLOW} for random){TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}


    target_npc_info = None; initiate_talk = False
    new_state = {'status': 'ok', 'continue_loop': True}
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_current_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()]

    if args == RANDOM_TALK_SYNTAX: # ... (random logic) ...
        if not npcs_in_current_area: print(f"{TerminalFormatter.YELLOW}⚠️ No NPCs found in {current_area} to talk to randomly.{TerminalFormatter.RESET}")
        else: target_npc_info = random.choice(npcs_in_current_area); initiate_talk = True; print(f"{TerminalFormatter.DIM}Randomly selected: {target_npc_info['name']}{TerminalFormatter.RESET}")
    else: # ... (specific name logic) ...
        target_npc_prefix = args.lower()
        print(f"{TerminalFormatter.DIM}Looking for NPCs starting with '{args}' in '{current_area}'...{TerminalFormatter.RESET}")
        matches = [n for n in npcs_in_current_area if n.get('name','').lower().startswith(target_npc_prefix)]
        if len(matches) == 1: target_npc_info = matches[0]; initiate_talk = True; print(f"{TerminalFormatter.DIM}Unique match found: {target_npc_info['name']}{TerminalFormatter.RESET}")
        elif len(matches) > 1: # ... (ambiguous message) ...
            print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous NPC prefix '{args}'. Matches in {current_area}:{TerminalFormatter.RESET}")
            for npc_match in sorted(matches, key=lambda x: x['name']): print(f"  {TerminalFormatter.DIM}- {npc_match.get('name')} ({npc_match.get('role', '???')}){TerminalFormatter.RESET}")
            print(f"{TerminalFormatter.YELLOW}Please be more specific.{TerminalFormatter.RESET}")
        else: # ... (not found message) ...
            print(f"{TerminalFormatter.YELLOW}⚠️ NPC starting with '{args}' not found in {current_area}.{TerminalFormatter.RESET}")
            if npcs_in_current_area: print(f"{TerminalFormatter.DIM}NPCs here: {', '.join(sorted(n['name'] for n in npcs_in_current_area))}{TerminalFormatter.RESET}")


    if initiate_talk and target_npc_info:
        if current_npc_old and current_npc_old.get('code') == target_npc_info.get('code'):
            print(f"{TerminalFormatter.DIM}You are already talking to {target_npc_info['name']}.{TerminalFormatter.RESET}")
        else:
            print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
            correct_npc_name = target_npc_info['name']

            npc_data, new_chat_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, current_area, correct_npc_name, model_name_for_session, story_for_session, ChatSession_class, TerminalFormatter
            )
            if npc_data and new_chat_session:
                new_state.update({'current_npc': npc_data, 'chat_session': new_chat_session})
            else: new_state.update({'current_npc': None, 'chat_session': None})
    return new_state

# ... (Keep handle_who, handle_whereami, handle_npcs, handle_stats, handle_session_stats, handle_clear as they are) ...
def handle_who(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; current_area = state['current_area']
    if not current_area: print(f"{TerminalFormatter.YELLOW}You are not in any specific area. Use /go <area> first.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_current_area = [npc for npc in all_known_npcs if npc.get('area', '').lower() == current_area.lower()]
    if not npcs_in_current_area: print(f"\n{TerminalFormatter.YELLOW}No known NPCs found in {current_area}.{TerminalFormatter.RESET}")
    else:
        print(f"\n{TerminalFormatter.YELLOW}NPCs in '{current_area}':{TerminalFormatter.RESET}")
        for npc_info in sorted(npcs_in_current_area, key=lambda x: x.get('name','').lower()): print(f"  {TerminalFormatter.DIM}- {npc_info.get('name', '???')} ({npc_info.get('role', '???')}){TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; current_area = state['current_area']; current_npc = state['current_npc']
    loc_msg = f"Location: {TerminalFormatter.BOLD}{current_area or 'Nowhere (Use /go)'}{TerminalFormatter.RESET}"
    npc_name_display = current_npc['name'] if current_npc and 'name' in current_npc else 'Nobody'
    npc_msg = f"Talking to: {TerminalFormatter.BOLD}{npc_name_display}{TerminalFormatter.RESET}"
    print(f"\n{TerminalFormatter.CYAN}{loc_msg}\n{npc_msg}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; db = state['db']
    try:
        from main_utils import format_npcs_list
        print(f"\n{TerminalFormatter.DIM}Fetching list of all known NPCs...{TerminalFormatter.RESET}")
        all_npcs_list = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
        if not all_npcs_list: print(f"{TerminalFormatter.YELLOW}No NPC data could be loaded.{TerminalFormatter.RESET}")
        else: print(format_npcs_list(all_npcs_list))
    except ImportError: print(f"{TerminalFormatter.RED}Error: main_utils.format_npcs_list not found.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']; current_npc = state['current_npc']; format_stats_func = state['format_stats']
    if not chat_session or not current_npc: print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    last_stats = chat_session.get_last_stats()
    if last_stats: print(f"\n{TerminalFormatter.DIM}{'-'*20} Last Turn Stats {'-'*20}{TerminalFormatter.RESET}"); print(format_stats_func(last_stats))
    else: print(f"{TerminalFormatter.YELLOW}No stats available for the last interaction.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']; current_npc = state['current_npc']
    if not chat_session or not current_npc: print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    print(f"\n{TerminalFormatter.DIM}{'-'*20} Current Session Stats {'-'*20}{TerminalFormatter.RESET}"); print(chat_session.format_session_stats())
    return {'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']
    if not chat_session: print(f"{TerminalFormatter.YELLOW}You are not in an active conversation to clear.{TerminalFormatter.RESET}")
    else: chat_session.clear_memory()
    return {'status': 'ok', 'continue_loop': True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> HandlerResult:
    result = {'status': 'ok', 'continue_loop': True}
    if not user_input.strip(): return result

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    format_stats_func = state.get('format_stats')

    if user_input.startswith('/'):
        parts = user_input[1:].split(None, 1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        command_handlers = {
            'exit': handle_exit, 'quit': handle_exit, 'help': handle_help,
            'go': handle_go, 'talk': handle_talk, 'who': handle_who,
            'whereami': handle_whereami, 'npcs': handle_npcs,
            'stats': handle_stats, 'session_stats': handle_session_stats,
            'clear': handle_clear,
            'hint': handle_hint, # NEW
            # '/profile' will be added later here
        }
        try:
            if command in command_handlers:
                # Commands that don't take 'args' in their signature
                if command in ['exit', 'quit', 'help', 'who', 'whereami', 'npcs', 'stats', 'session_stats', 'clear', 'hint']:
                    return command_handlers[command](state)
                else: # Commands that take 'args'
                    return command_handlers[command](args, state)
            elif command == 'history':
                if chat_session:
                    print(f"\n{TerminalFormatter.DIM}--- Conversation History (JSON) ---{TerminalFormatter.RESET}")
                    history_json = json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)
                    print(history_json)
                else: print(f"{TerminalFormatter.YELLOW}No active conversation for history.{TerminalFormatter.RESET}")
                return {'status': 'ok', 'continue_loop': True}
            else:
                print(f"{TerminalFormatter.YELLOW}Unknown command '/{command}'. Type /help.{TerminalFormatter.RESET}")
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error processing command '/{command}': {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() # For debugging

    elif current_npc and chat_session:
        try:
            print(f"{TerminalFormatter.DIM}Processing your message...{TerminalFormatter.RESET}")
            response, stats = chat_session.ask(
                user_input, stream=state.get('use_stream', True), collect_stats=True
            )
            print()
            if state.get('auto_show_stats', False) and stats and format_stats_func:
                print(format_stats_func(stats))
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error in conversation: {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() # For debugging
    else:
        print(f"{TerminalFormatter.YELLOW}Not talking to anyone. Use /go, then /talk or wait for a conversation.{TerminalFormatter.RESET}")
    return result