# Path: command_processor.py
# Updated for inventory commands and refined NPC reaction to /give

import json
import random
import traceback 
from typing import Dict, List, Any, Optional, Tuple

import session_utils 

RANDOM_TALK_SYNTAX = '.'
HandlerResult = Dict[str, Any] 

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; player_id = state['player_id']
    print(f"\n{TerminalFormatter.DIM}Saving last conversation (if active)...{TerminalFormatter.RESET}")
    session_utils.save_current_conversation(state['db'], player_id, state['current_npc'], state['chat_session'], TerminalFormatter)
    print(f"{TerminalFormatter.YELLOW}Arrivederci!{TerminalFormatter.RESET}")
    return {'status': 'exit'}

def handle_help(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is, ensure main_utils.get_help_text is up-to-date) ...
    TerminalFormatter = state['TerminalFormatter']
    try:
        from main_utils import get_help_text
        print(get_help_text())
    except ImportError:
        print(f"{TerminalFormatter.RED}Error: Help utility not found.{TerminalFormatter.RESET}")
        print("Basic commands: /exit, /go, /talk, /who, /whereami, /npcs, /hint, /inventory, /give, /stats, /clear, /history")
    return {'status': 'ok', 'continue_loop': True}

def handle_hint(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; chat_session = state['chat_session']; current_npc = state['current_npc']
    if not chat_session or not current_npc:
        print(f"{TerminalFormatter.YELLOW}Not talking to anyone to get a hint.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    hint_text = chat_session.get_player_hint() 
    if hint_text:
        print(f"\n{TerminalFormatter.BRIGHT_CYAN}{TerminalFormatter.BOLD}Hint ({current_npc.get('name')}):{TerminalFormatter.RESET}")
        formatted_hint = TerminalFormatter.format_terminal_text(hint_text, width=TerminalFormatter.get_terminal_width() - 2)
        for line in formatted_hint.split('\n'): print(f"  {TerminalFormatter.CYAN}{line}{TerminalFormatter.RESET}")
    else: print(f"{TerminalFormatter.YELLOW}No specific hint available for {current_npc.get('name')}.{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_inventory(state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is) ...
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    inventory_list = db.load_inventory(player_id) 
    if 'player_inventory' in state: state['player_inventory'] = inventory_list 
    print(f"\n{TerminalFormatter.BRIGHT_GREEN}{TerminalFormatter.BOLD}--- Your Inventory ---{TerminalFormatter.RESET}")
    if inventory_list: [print(f"  {TerminalFormatter.GREEN}❖ {item}{TerminalFormatter.RESET}") for item in inventory_list]
    else: print(f"  {TerminalFormatter.DIM}(empty){TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_GREEN}{'-'*22}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}


def handle_give(args: str, state: Dict[str, Any]) -> HandlerResult:
    """Handles the /give command, setting up for NPC reaction."""
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc = state['current_npc']
    chat_session = state['chat_session']
    
    # This will be part of the return value to main_core.py
    # It signals that an item was given and consequences should be checked AFTER NPC reacts.
    # And that NPC turn should be forced.
    handler_action_payload: Dict[str, Any] = {}

    if not current_npc or not chat_session:
        print(f"{TerminalFormatter.YELLOW}You're not talking to anyone to give an item to.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    item_name_to_give = args.strip()
    if not item_name_to_give:
        print(f"{TerminalFormatter.YELLOW}What do you want to give? Usage: /give <item_name>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    if not db.check_item_in_inventory(player_id, item_name_to_give):
        print(f"{TerminalFormatter.YELLOW}You don't have '{item_name_to_give}' in your inventory.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True}

    if db.remove_item_from_inventory(player_id, item_name_to_give, state): # state for TF access
        print(f"{TerminalFormatter.DIM}You hand '{item_name_to_give}' to {current_npc['name']}.{TerminalFormatter.RESET}")
        
        player_action_message = f"*You hand the {item_name_to_give} to {current_npc['name']}.*"
        chat_session.add_message("user", player_action_message) 
        
        handler_action_payload['item_given_to_npc_this_turn'] = {
            'item_name': item_name_to_give,
            'npc_code': current_npc.get('code') 
        }
        handler_action_payload['force_npc_turn_after_command'] = True # Signal for process_input_revised
    else:
        print(f"{TerminalFormatter.RED}Error removing '{item_name_to_give}' from inventory.{TerminalFormatter.RESET}")
            
    return {**handler_action_payload, 'status': 'ok', 'continue_loop': True}


def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is, it correctly calls auto_start_default_npc_conversation) ...
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    current_npc_old = state['current_npc']; chat_session_old = state['chat_session']
    if not args: print(f"{TerminalFormatter.YELLOW}Usage: /go <area_name_or_prefix>{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}

    target_area_prefix = args.lower()
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter) 
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [area for area in known_areas if area.lower().startswith(target_area_prefix)]
    state_changes: Dict[str, Any] = {}

    if len(matches) == 1:
        matched_area = matches[0]
        print(f"{TerminalFormatter.DIM}Area match: {matched_area}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}Saving previous conversation...{TerminalFormatter.RESET}")
        session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
        print(f"{TerminalFormatter.CYAN}Moving to: {matched_area}...{TerminalFormatter.RESET}")
        state_changes.update({'current_area': matched_area, 'current_npc': None, 'chat_session': None})
        
        default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
            db, player_id, matched_area, state['model_name'], state['story'], state['ChatSession'], TerminalFormatter)
        if default_npc_data and default_session:
            state_changes['current_npc'] = default_npc_data
            state_changes['chat_session'] = default_session
        elif not (default_npc_data and default_session) :
             print(f"{TerminalFormatter.YELLOW}You are in {matched_area}. Use /talk or /who.{TerminalFormatter.RESET}")
    elif len(matches) > 1: # ... (ambiguous) ...
        print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area '{args}'. Matches:{TerminalFormatter.RESET}")
        for m in sorted(matches): print(f"  - {m}")
        print(f"{TerminalFormatter.YELLOW}Be more specific.{TerminalFormatter.RESET}")
    else: # ... (not found) ...
        print(f"{TerminalFormatter.YELLOW}⚠️ Area '{args}' not found.{TerminalFormatter.RESET}")
        if known_areas: print(f"{TerminalFormatter.DIM}Known: {', '.join(known_areas)}{TerminalFormatter.RESET}")
    return {**state_changes, 'status': 'ok', 'continue_loop': True}


def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    # ... (Keep as is, it correctly calls start_conversation_with_specific_npc) ...
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    current_area = state['current_area']; current_npc_old = state['current_npc']; chat_session_old = state['chat_session']
    model_name = state['model_name']; story = state['story']; ChatSession_class = state['ChatSession']
    if not current_area: print(f"{TerminalFormatter.YELLOW}Not in an area. Use /go.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    if not args: print(f"{TerminalFormatter.YELLOW}Usage: /talk <npc_name|.>{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}

    target_npc_info = None; initiate_talk = False; state_changes: Dict[str, Any] = {}
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_in_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()]

    if args == RANDOM_TALK_SYNTAX: # ... (random logic) ...
        if not npcs_in_area: print(f"{TerminalFormatter.YELLOW}⚠️ No NPCs in {current_area}.{TerminalFormatter.RESET}")
        else: target_npc_info = random.choice(npcs_in_area); print(f"{TerminalFormatter.DIM}Randomly selected: {target_npc_info['name']}{TerminalFormatter.RESET}"); initiate_talk = True
    else: # ... (specific name logic) ...
        prefix = args.lower()
        matches = [n for n in npcs_in_area if n.get('name','').lower().startswith(prefix)]
        if len(matches) == 1: target_npc_info = matches[0]; print(f"{TerminalFormatter.DIM}Match: {target_npc_info['name']}{TerminalFormatter.RESET}"); initiate_talk = True
        elif len(matches) > 1: print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous '{args}'. Matches:{TerminalFormatter.RESET}"); [print(f"  - {m.get('name')}") for m in sorted(matches, key=lambda x:x['name'])]
        else: print(f"{TerminalFormatter.YELLOW}⚠️ NPC '{args}' not found in {current_area}.{TerminalFormatter.RESET}")
    
    if initiate_talk and target_npc_info:
        if current_npc_old and current_npc_old.get('code') == target_npc_info.get('code'): print(f"{TerminalFormatter.DIM}Already talking to {target_npc_info['name']}.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.DIM}Saving previous chat...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
            npc_data, new_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, current_area, target_npc_info['name'], model_name, story, ChatSession_class, TerminalFormatter)
            if npc_data and new_session: state_changes.update({'current_npc': npc_data, 'chat_session': new_session})
            else: state_changes.update({'current_npc': None, 'chat_session': None})
    return {**state_changes, 'status': 'ok', 'continue_loop': True}

# --- Keep other handlers (who, whereami, npcs, stats, session_stats, clear) as they are ---
def handle_who(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; current_area = state['current_area']
    if not current_area: print(f"{TerminalFormatter.YELLOW}Not in an area. Use /go.{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    all_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    npcs_here = [n for n in all_npcs if n.get('area', '').lower() == current_area.lower()]
    if not npcs_here: print(f"\n{TerminalFormatter.YELLOW}No NPCs in {current_area}.{TerminalFormatter.RESET}")
    else:
        print(f"\n{TerminalFormatter.YELLOW}NPCs in '{current_area}':{TerminalFormatter.RESET}")
        for npc in sorted(npcs_here, key=lambda x: x.get('name','').lower()): print(f"  {TerminalFormatter.DIM}- {npc.get('name','???')} ({npc.get('role','???')}){TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; area = state['current_area']; npc = state['current_npc']; session = state['chat_session']
    loc = f"Location: {TF.BOLD}{area or 'Nowhere'}{TF.RESET}"
    npc_name = npc['name'] if npc and 'name' in npc else 'Nobody'
    talking = f"Talking to: {TF.BOLD}{npc_name}{TF.RESET}"
    if npc and session and session.get_player_hint():
        hint = session.get_player_hint(); talking += f"\n  {TF.DIM}(Hint: {hint[:70]}{'...' if len(hint) > 70 else ''}){TF.RESET}"
    print(f"\n{TF.CYAN}{loc}\n{talking}{TF.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; db = state['db']
    try:
        from main_utils import format_npcs_list
        all_npcs = session_utils.refresh_known_npcs_list(db, TF)
        if not all_npcs: print(f"{TF.YELLOW}No NPCs loaded.{TF.RESET}")
        else: print(format_npcs_list(all_npcs))
    except ImportError: print(f"{TF.RED}Error: format_npcs_list util missing.{TF.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; session = state['chat_session']; npc = state['current_npc']; fmt_stats = state['format_stats']
    if not session or not npc: print(f"{TF.YELLOW}Not in a conversation.{TF.RESET}"); return {'status': 'ok', 'continue_loop': True}
    ls = session.get_last_stats()
    if ls: print(f"\n{TF.DIM}{'-'*15} Last Turn Stats {'-'*15}{TF.RESET}"); print(fmt_stats(ls))
    else: print(f"{TF.YELLOW}No stats for last interaction.{TF.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; session = state['chat_session']; npc = state['current_npc']
    if not session or not npc: print(f"{TF.YELLOW}Not in a conversation.{TF.RESET}"); return {'status': 'ok', 'continue_loop': True}
    print(f"\n{TF.DIM}{'-'*15} Current Session Stats {'-'*15}{TF.RESET}"); print(session.format_session_stats())
    return {'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; session = state['chat_session']
    if not session: print(f"{TF.YELLOW}Not in a conversation to clear.{TF.RESET}")
    else: session.clear_memory() # Prints its own confirmation
    return {'status': 'ok', 'continue_loop': True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Processes user input: handles commands or passes to LLM as dialogue."""
    # `state` is mutable and can be updated by handlers. This function will return the (potentially) new state.
    # Initialize flag for this turn; handlers don't set this, dialogue block does.
    state['npc_made_new_response_this_turn'] = False 

    if not user_input.strip():
        return state # No input, no change, just continue loop

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    format_stats_func = state.get('format_stats')
    
    command_processed_and_took_turn = False
    handler_action_payload = {} # To capture special flags from handlers like /give

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
            'inventory': handle_inventory, 'inv': handle_inventory, 
            'give': handle_give,
        }
        try:
            if command in command_handlers_map:
                handler_func = command_handlers_map[command]
                # Call handler: it receives current state and returns a dict of updates/signals
                # These updates are then merged back into the main 'state' dict.
                if command in ['go', 'talk', 'give']: # Commands that take 'args'
                    handler_return_dict = handler_func(args, state)
                else: # Commands that only take 'state'
                    handler_return_dict = handler_func(state)
                
                state.update(handler_return_dict) # Merge results back into the primary state
                
                if state.get('status') == 'exit': return state # Exit immediately
                command_processed_and_took_turn = True
            elif command == 'history':
                # ... (history printing logic, does not significantly change state) ...
                if chat_session: print(f"\n{TerminalFormatter.DIM}--- History ---{TerminalFormatter.RESET}\n{json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)}")
                else: print(f"{TerminalFormatter.YELLOW}No active chat for history.{TerminalFormatter.RESET}")
                command_processed_and_took_turn = True
            else:
                print(f"{TerminalFormatter.YELLOW}Unknown command '/{command}'. Type /help.{TerminalFormatter.RESET}")
                command_processed_and_took_turn = True
        except Exception as e:
            print(f"{TerminalFormatter.RED}Error processing command '/{command}': {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            command_processed_and_took_turn = True
            # traceback.print_exc()

    # --- Force NPC turn if a command (like /give) set the flag ---
    # The flag would have been merged into 'state' by state.update(handler_return_dict)
    force_npc_turn = state.pop('force_npc_turn_after_command', False) # Check and consume

    if force_npc_turn and current_npc and chat_session:
        if not chat_session.messages or chat_session.messages[-1].get("role") != "user":
            # This case should ideally not happen if /give correctly added a "user" action.
            # Add a generic user prompt if history is empty or last wasn't user.
            chat_session.add_message("user", "[Player takes a moment after their action, awaiting a response.]")

        print(f"{TerminalFormatter.DIM}{current_npc.get('name', 'NPC')} considers your action...{TerminalFormatter.RESET}")
        try:
            # The "prompt" for ask is the last user message in history (which /give added)
            # We pass a dummy prompt string here just to satisfy ask() signature,
            # as the actual prompt comes from the history.
            _response_text, stats = chat_session.ask(
                prompt="[NPC reacts to action]", # This is effectively a placeholder
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            state['npc_made_new_response_this_turn'] = True # NPC responded
            print() 
            if state.get('auto_show_stats', False) and stats and format_stats_func:
                print(format_stats_func(stats))
        except Exception as e:
            state['npc_made_new_response_this_turn'] = False
            print(f"{TerminalFormatter.RED}Error during forced NPC reaction: {e}{TerminalFormatter.RESET}")
        command_processed_and_took_turn = True # This counts as the NPC's turn too

    # --- Normal Dialogue if no command took the turn AND no forced NPC turn happened above ---
    elif not command_processed_and_took_turn and current_npc and chat_session: 
        try:
            print(f"{TerminalFormatter.DIM}Processing your input to {current_npc.get('name', 'NPC')}...{TerminalFormatter.RESET}")
            _response_text, stats = chat_session.ask(
                user_input, # The player's typed dialogue
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            state['npc_made_new_response_this_turn'] = True 
            print() 
            if state.get('auto_show_stats', False) and stats and format_stats_func:
                print(format_stats_func(stats))
        except Exception as e:
            state['npc_made_new_response_this_turn'] = False
            print(f"{TerminalFormatter.RED}Error in conversation: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
    
    # If no command was run, and not in a state to talk (e.g., no NPC, no area)
    elif not command_processed_and_took_turn and not (current_npc and chat_session):
        if user_input: # Only print if user actually typed something
            print(f"{TerminalFormatter.YELLOW}You are not talking to anyone. Use /go, then /talk or wait.{TerminalFormatter.RESET}")

    return state # Return the final state for this turn
