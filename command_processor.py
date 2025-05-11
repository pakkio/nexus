# Path: command_processor.py

import json
import random
import traceback 
from typing import Dict, List, Any, Optional, Tuple

import session_utils 

RANDOM_TALK_SYNTAX = '.'
HandlerResult = Dict[str, Any] 

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    player_id = state['player_id']
    print(f"\n{TerminalFormatter.DIM}Saving last conversation (if active)...{TerminalFormatter.RESET}")
    session_utils.save_current_conversation(
        state['db'], player_id, state['current_npc'], state['chat_session'], TerminalFormatter
        # If save becomes async or needs llm_wrapper:
        # state.get('llm_wrapper_func'), state.get('model_name') # Pass actual function
    )
    print(f"{TerminalFormatter.YELLOW}Arrivederci! Leaving Eldoria... for now.{TerminalFormatter.RESET}")
    return {'status': 'exit'}

def handle_help(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    try:
        from main_utils import get_help_text
        print(get_help_text())
    except ImportError:
        print(f"{TerminalFormatter.RED}Error: Help utility not found.{TerminalFormatter.RESET}")
        print("Basic commands: /exit, /go, /talk, /who, /whereami, /npcs, /hint, /inventory, /give, /stats, /clear, /history")
    return {'status': 'ok', 'continue_loop': True}

def handle_hint(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    chat_session = state['chat_session']
    current_npc = state['current_npc']

    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}You need to be in an active conversation to get a relevant hint.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    hint_text = chat_session.get_player_hint() 
    if hint_text:
        print(f"\n{TerminalFormatter.BRIGHT_CYAN}{TerminalFormatter.BOLD}Hint regarding {current_npc.get('name', 'your current interaction')}:{TerminalFormatter.RESET}")
        formatted_hint = TerminalFormatter.format_terminal_text(hint_text, width=TerminalFormatter.get_terminal_width() - 4)
        for line in formatted_hint.split('\n'): print(f"  {TerminalFormatter.CYAN}➢ {line}{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.YELLOW}No specific hint available for {current_npc.get('name', 'this interaction')} right now.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

# --- NEW: Inventory Command ---
def handle_inventory(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']

    inventory_list = db.load_inventory(player_id) # This loads fresh every time
    # Update cached player inventory if used in state (optional optimization)
    if 'player_inventory' in state: state['player_inventory'] = inventory_list 

    print(f"\n{TerminalFormatter.BRIGHT_GREEN}{TerminalFormatter.BOLD}--- Your Inventory ---{TerminalFormatter.RESET}")
    if inventory_list:
        for item in inventory_list: # Already sorted by load_inventory
            print(f"  {TerminalFormatter.GREEN}❖ {item}{TerminalFormatter.RESET}")
    else:
        print(f"  {TerminalFormatter.DIM}(Your inventory is empty){TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_GREEN}{'-'*22}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}
# --- END NEW ---

# --- NEW: Give Command ---
def handle_give(args: str, state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc = state['current_npc']
    chat_session = state['chat_session'] # This is a ChatSession INSTANCE

    if not current_npc or not chat_session:
        print(f"{TerminalFormatter.YELLOW}You need to be talking to someone to give them an item.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    item_name_to_give = args.strip()
    if not item_name_to_give:
        print(f"{TerminalFormatter.YELLOW}What item do you want to give? Usage: /give <item_name>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    if not db.check_item_in_inventory(player_id, item_name_to_give):
        print(f"{TerminalFormatter.YELLOW}You don't have '{item_name_to_give}' in your inventory.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    # Proceed to give: Remove item from player, add to NPC (conceptually), let NPC react
    if db.remove_item_from_inventory(player_id, item_name_to_give, state): # state for TF & cache update
        # This message confirms removal to player BEFORE NPC reaction
        print(f"{TerminalFormatter.DIM}You hand '{item_name_to_give}' to {current_npc['name']}. They look at it...{TerminalFormatter.RESET}")
        
        # Add this action to the chat history so the LLM (NPC) "sees" it as the player's turn.
        # This is what the NPC will react to.
        player_action_message = f"*You hand the {item_name_to_give} to {current_npc['name']}.*"
        chat_session.add_message("user", player_action_message)
        
        # Set a flag in the state that an item was given.
        # main_core.py will check this flag *after* the NPC's response to player_action_message
        # to process game logic consequences (like NPC giving treasure).
        # This flag is directly added to the mutable `state` dictionary.
        state['item_given_to_npc_this_turn'] = {
            'item_name': item_name_to_give,
            'npc_code': current_npc.get('code') 
        }
        
        # We don't call chat_session.ask() here.
        # The main loop in main_core.py will proceed, and because a "user" message
        # (the action_as_player_turn) was added to history, the existing dialogue
        # processing logic in process_input_revised will trigger the LLM call for the NPC's reaction.
        # This keeps command handlers focused on updating state/DB and preparing context.
    else:
        # remove_item_from_inventory would have printed "not found" if check_item somehow passed then failed,
        # or if there was an issue with removal. This path should be rare.
        print(f"{TerminalFormatter.RED}Error: Could not remove '{item_name_to_give}' from inventory, though it was expected to be there.{TerminalFormatter.RESET}")
            
    return {'status': 'ok', 'continue_loop': True} # Loop continues for NPC reaction
# --- END NEW ---


def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc_old = state['current_npc'] 
    chat_session_old = state['chat_session'] 

    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    target_area_prefix = args.lower()
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter) 
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [area for area in known_areas if area.lower().startswith(target_area_prefix)]
    new_state_updates: Dict[str, Any] = {} # To collect updates for the state

    if len(matches) == 1:
        matched_area = matches[0]
        print(f"{TerminalFormatter.DIM}Unique area match found: {matched_area}{TerminalFormatter.RESET}")
        print(f"\n{TerminalFormatter.DIM}Saving previous conversation (if active)...{TerminalFormatter.RESET}")
        session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
        print(f"{TerminalFormatter.CYAN}Moving to area: {matched_area}...{TerminalFormatter.RESET}")

        new_state_updates.update({
            'current_area': matched_area,
            'current_npc': None, 
            'chat_session': None
        })
        
        default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
            db, player_id, matched_area, state['model_name'], state['story'],
            state['ChatSession'], TerminalFormatter # Pass ChatSession CLASS
        )
        if default_npc_data and default_session:
            new_state_updates['current_npc'] = default_npc_data
            new_state_updates['chat_session'] = default_session
        else: 
             if not (default_npc_data and default_session) :
                 print(f"{TerminalFormatter.YELLOW}You are now in {matched_area}. Use {TerminalFormatter.BOLD}/talk <npc_name_or_prefix|.>{TerminalFormatter.YELLOW} or {TerminalFormatter.BOLD}/who{TerminalFormatter.YELLOW} to interact.")
    elif len(matches) > 1:
        print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area prefix '{args}'. Matches:{TerminalFormatter.RESET}")
        for area_match in sorted(matches): print(f"  {TerminalFormatter.DIM}- {area_match}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.YELLOW}Please be more specific.{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.YELLOW}⚠️ Area starting with '{args}' not found.{TerminalFormatter.RESET}")
        if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(sorted(known_areas))}{TerminalFormatter.RESET}")

    # Return a result that includes any state changes
    return {**state, **new_state_updates, 'status': 'ok', 'continue_loop': True}


def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_area = state['current_area']
    current_npc_old = state['current_npc']
    chat_session_old = state['chat_session']
    model_name_for_session = state['model_name']
    story_for_session = state['story']
    ChatSession_class = state['ChatSession'] 

    if not current_area:
        print(f"{TerminalFormatter.YELLOW}You need to be in an area first. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}
    if not args:
        print(f"{TerminalFormatter.YELLOW}Usage: /talk <npc_name_or_prefix | . > ({TerminalFormatter.BOLD}.{TerminalFormatter.YELLOW} for random){TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    target_npc_info = None; initiate_talk = False
    new_state_updates: Dict[str, Any] = {}
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_current_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()]

    if args == RANDOM_TALK_SYNTAX:
        if not npcs_in_current_area: print(f"{TerminalFormatter.YELLOW}⚠️ No NPCs in {current_area} to talk to randomly.{TerminalFormatter.RESET}")
        else: target_npc_info = random.choice(npcs_in_current_area); print(f"{TerminalFormatter.DIM}Randomly selected: {target_npc_info['name']}{TerminalFormatter.RESET}"); initiate_talk = True
    else:
        target_npc_prefix = args.lower()
        # print(f"{TerminalFormatter.DIM}Looking for NPCs starting with '{args}' in '{current_area}'...{TerminalFormatter.RESET}") # Can be noisy
        matches = [n for n in npcs_in_current_area if n.get('name','').lower().startswith(target_npc_prefix)]
        if len(matches) == 1: target_npc_info = matches[0]; print(f"{TerminalFormatter.DIM}Unique match: {target_npc_info['name']}{TerminalFormatter.RESET}"); initiate_talk = True
        elif len(matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous NPC prefix '{args}'. Matches in {current_area}:{TerminalFormatter.RESET}")
            for m in sorted(matches, key=lambda x: x['name']): print(f"  {TerminalFormatter.DIM}- {m.get('name')} ({m.get('role','???')}){TerminalFormatter.RESET}")
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
            
            npc_data, new_chat_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, current_area, correct_npc_name, model_name_for_session, story_for_session, ChatSession_class, TerminalFormatter
            )
            if npc_data and new_chat_session:
                new_state_updates.update({'current_npc': npc_data, 'chat_session': new_chat_session})
            else: new_state_updates.update({'current_npc': None, 'chat_session': None})
            
    return {**state, **new_state_updates, 'status': 'ok', 'continue_loop': True}


def handle_who(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
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
    # ... (Modified slightly to show hint context from /whereami if available) ...
    TerminalFormatter = state['TerminalFormatter']; current_area = state['current_area']; current_npc = state['current_npc']; chat_session = state['chat_session']
    loc_msg = f"Location: {TerminalFormatter.BOLD}{current_area or 'Nowhere (Use /go)'}{TerminalFormatter.RESET}"
    npc_name_display = current_npc['name'] if current_npc and 'name' in current_npc else 'Nobody'
    npc_msg = f"Talking to: {TerminalFormatter.BOLD}{npc_name_display}{TerminalFormatter.RESET}"
    if current_npc and chat_session and chat_session.get_player_hint():
        hint_preview = chat_session.get_player_hint()
        if hint_preview: # Ensure hint_preview is not None before slicing
             npc_msg += f"\n  {TerminalFormatter.DIM}(Hint related to {current_npc['name']}: {hint_preview[:70]}{'...' if len(hint_preview) > 70 else ''}){TerminalFormatter.RESET}"
    print(f"\n{TerminalFormatter.CYAN}{loc_msg}\n{npc_msg}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
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
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']; current_npc = state['current_npc']; format_stats_func = state['format_stats']
    if not chat_session or not current_npc: print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    last_stats = chat_session.get_last_stats()
    if last_stats: print(f"\n{TerminalFormatter.DIM}{'-'*20} Last Turn Stats {'-'*20}{TerminalFormatter.RESET}"); print(format_stats_func(last_stats))
    else: print(f"{TerminalFormatter.YELLOW}No stats available for the last interaction.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']; current_npc = state['current_npc']
    if not chat_session or not current_npc: print(f"{TerminalFormatter.YELLOW}You need to be actively talking to an NPC for this command.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    print(f"\n{TerminalFormatter.DIM}{'-'*20} Current Session Stats {'-'*20}{TerminalFormatter.RESET}"); print(chat_session.format_session_stats())
    return {'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']
    if not chat_session: print(f"{TerminalFormatter.YELLOW}You are not in an active conversation to clear.{TerminalFormatter.RESET}")
    else: chat_session.clear_memory()
    return {'status': 'ok', 'continue_loop': True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> HandlerResult:
    """Process user input and dispatch to appropriate handler functions."""
    # Default result, which includes the original state unless modified by a handler
    handler_result_payload = {'status': 'ok', 'continue_loop': True}

    # Clear any 'item_given_to_npc_this_turn' from previous turn in main_core before it's re-evaluated
    # This is now handled in main_core.py after this function returns.

    if not user_input.strip(): 
        # Pass back current state if input is empty, but it's not an error.
        return {**state, **handler_result_payload} 

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    format_stats_func = state.get('format_stats')

    # This will hold the direct return value from the command handler function
    command_handler_output: Optional[HandlerResult] = None 

    if user_input.startswith('/'):
        parts = user_input[1:].split(None, 1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        command_handlers_map = {
            'exit': handle_exit, 'quit': handle_exit, 'help': handle_help,
            'go': handle_go, 'talk': handle_talk, 'who': handle_who,
            'whereami': handle_whereami, 'npcs': handle_npcs,
            'stats': handle_stats, 'session_stats': handle_session_stats,
            'clear': handle_clear, 'hint': handle_hint,
            'inventory': handle_inventory, 'inv': handle_inventory, # NEW
            'give': handle_give, # NEW
        }
        try:
            if command in command_handlers_map:
                handler_func = command_handlers_map[command]
                # Pass args only if the handler is expected to take it (like 'go', 'talk', 'give')
                if command in ['go', 'talk', 'give']:
                    command_handler_output = handler_func(args, state)
                else:
                    command_handler_output = handler_func(state)
            elif command == 'history':
                if chat_session:
                    print(f"\n{TerminalFormatter.DIM}--- Conversation History (JSON) ---{TerminalFormatter.RESET}")
                    history_json = json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)
                    print(history_json)
                else: print(f"{TerminalFormatter.YELLOW}No active conversation for history.{TerminalFormatter.RESET}")
                # No state change from /history itself typically, just prints
            else:
                print(f"{TerminalFormatter.YELLOW}Unknown command '/{command}'. Type /help.{TerminalFormatter.RESET}")
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error processing command '/{command}': {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() 

    elif current_npc and chat_session: # Normal dialogue if not a command
        try:
            # This is where player's text input is sent to LLM
            # If a /give command happened, it added an action message to history.
            # This .ask() call will then get the NPC's response to that action.
            print(f"{TerminalFormatter.DIM}Processing your message to {current_npc.get('name', 'NPC')}...{TerminalFormatter.RESET}")
            response_text, stats = chat_session.ask(
                user_input, # The player's typed dialogue
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            print() # Spacing after LLM output (which should have its own newline)

            if state.get('auto_show_stats', False) and stats and format_stats_func:
                print(format_stats_func(stats))
            
            # No specific state changes to return from dialogue itself, main_core updates current state vars
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error in conversation with {current_npc.get('name', 'NPC')}: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            # traceback.print_exc()
    else: 
        print(f"{TerminalFormatter.YELLOW}You are not talking to anyone. Use /go, then /talk or wait.{TerminalFormatter.RESET}")

    # If a command handler returned something, use it as the base for our return.
    # Otherwise, start with the original state.
    # Then merge in the default handler_result_payload ('status', 'continue_loop').
    if command_handler_output:
        # Ensure all original state keys are preserved if not overridden by handler
        # and that 'status' and 'continue_loop' are present.
        final_result = {**state, **command_handler_output}
        if 'status' not in final_result: final_result['status'] = 'ok'
        if 'continue_loop' not in final_result: final_result['continue_loop'] = True
        return final_result
    else:
        # No command run, or command didn't return a full state dict (e.g. /history)
        # Just return the original state merged with default payload.
        return {**state, **handler_result_payload}

