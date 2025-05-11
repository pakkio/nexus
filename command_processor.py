# Path: command_processor.py
# Updated for inventory commands, Credits handling, fixed /hint, and fixed /npcs syntax

import json
import random
import traceback
import re # For parsing credits in /give
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
        print(f"\n{TerminalFormatter.BRIGHT_CYAN}{TerminalFormatter.BOLD}Hint ({current_npc.get('name', 'your current interaction')}):{TerminalFormatter.RESET}")
        formatted_hint_lines = TerminalFormatter.format_terminal_text(hint_text, width=TerminalFormatter.get_terminal_width() - 4).split('\n')
        for line_in_formatted_hint in formatted_hint_lines:
            print(f"  {TerminalFormatter.CYAN}➢ {line_in_formatted_hint}{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.YELLOW}No specific hint available for {current_npc.get('name', 'this interaction')} right now.{TerminalFormatter.RESET}")

    return {'status': 'ok', 'continue_loop': True}

def handle_inventory(state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']

    inventory_list = state.get('player_inventory', db.load_inventory(player_id))
    current_credits = state.get('player_credits_cache', db.get_player_credits(player_id))

    print(f"\n{TerminalFormatter.BRIGHT_GREEN}{TerminalFormatter.BOLD}--- Your Inventory ---{TerminalFormatter.RESET}")
    if inventory_list:
        for item in inventory_list:
            print(f"  {TerminalFormatter.GREEN}❖ {item.title()}{TerminalFormatter.RESET}")
    else:
        print(f"  {TerminalFormatter.DIM}(Your inventory is empty){TerminalFormatter.RESET}")

    print(f"{TerminalFormatter.BRIGHT_YELLOW}Credits: {current_credits}{TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_GREEN}{'-'*22}{TerminalFormatter.RESET}")
    return {'status': 'ok', 'continue_loop': True}

def handle_give(args: str, state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    current_npc = state['current_npc']; chat_session = state['chat_session']
    handler_action_payload: Dict[str, Any] = {}

    if not current_npc or not chat_session:
        print(f"{TerminalFormatter.YELLOW}Not talking to anyone to give an item to.{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True, **handler_action_payload}


    input_str = args.strip()
    if not input_str:
        print(f"{TerminalFormatter.YELLOW}What do you want to give? Usage: /give <item_name_or_amount Credits>{TerminalFormatter.RESET}")
        return {'status': 'ok', 'continue_loop': True, **handler_action_payload}


    credit_match = re.match(r"(\d+)\s+(credits?)$", input_str, re.IGNORECASE)

    if credit_match:
        amount_to_give = int(credit_match.group(1))
        player_current_credits = state.get('player_credits_cache', db.get_player_credits(player_id))
        if amount_to_give <= 0:
            print(f"{TerminalFormatter.YELLOW}You must give a positive amount of Credits.{TerminalFormatter.RESET}")
            return {'status': 'ok', 'continue_loop': True, **handler_action_payload}

        if player_current_credits >= amount_to_give:
            if db.update_player_credits(player_id, -amount_to_give, state):
                item_name_for_log = f"{amount_to_give} Credits"
                print(f"{TerminalFormatter.DIM}You hand {item_name_for_log} to {current_npc['name']}.{TerminalFormatter.RESET}")
                player_action_message = f"*You hand over {item_name_for_log} to {current_npc['name']}.*"
                chat_session.add_message("user", player_action_message)
                handler_action_payload['item_given_to_npc_this_turn'] = {
                    'item_name': item_name_for_log, 'type': 'currency', 'amount': amount_to_give,
                    'npc_code': current_npc.get('code') }
                handler_action_payload['force_npc_turn_after_command'] = True
        else:
            print(f"{TerminalFormatter.YELLOW}You don't have enough Credits. You only have {player_current_credits}.{TerminalFormatter.RESET}")
    else:
        item_name_to_give = input_str
        if not db.check_item_in_inventory(player_id, item_name_to_give):
            print(f"{TerminalFormatter.YELLOW}You don't have '{item_name_to_give}' (or similar) in your inventory.{TerminalFormatter.RESET}")
            return {'status': 'ok', 'continue_loop': True, **handler_action_payload}

        if db.remove_item_from_inventory(player_id, item_name_to_give, state):
            cleaned_item_name_for_log = item_name_to_give.strip().lower()
            print(f"{TerminalFormatter.DIM}You hand '{item_name_to_give.strip()}' to {current_npc['name']}.{TerminalFormatter.RESET}")
            player_action_message = f"*You hand the {item_name_to_give.strip()} to {current_npc['name']}.*"
            chat_session.add_message("user", player_action_message)
            handler_action_payload['item_given_to_npc_this_turn'] = {
                'item_name': cleaned_item_name_for_log, 'type': 'item',
                'npc_code': current_npc.get('code') }
            handler_action_payload['force_npc_turn_after_command'] = True
        else:
            print(f"{TerminalFormatter.RED}Error: Could not remove '{item_name_to_give}' from inventory.{TerminalFormatter.RESET}")

    return {**handler_action_payload, 'status': 'ok', 'continue_loop': True}


def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
    TerminalFormatter = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    current_npc_old = state['current_npc']; chat_session_old = state['chat_session']
    if not args: print(f"{TerminalFormatter.YELLOW}Usage: /go <area>{TerminalFormatter.RESET}"); return {'status': 'ok', 'continue_loop': True}
    target_prefix = args.lower()
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
    matches = [a for a in known_areas if a.lower().startswith(target_prefix)]
    state_changes: Dict[str, Any] = {}

    if len(matches) == 1:
        area = matches[0]; print(f"{TerminalFormatter.DIM}Area match: {area}{TerminalFormatter.RESET}")
        print(f"{TerminalFormatter.DIM}Saving previous conversation...{TerminalFormatter.RESET}")
        session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TerminalFormatter)
        print(f"{TerminalFormatter.CYAN}Moving to: {area}...{TerminalFormatter.RESET}")
        state_changes.update({'current_area': area, 'current_npc': None, 'chat_session': None})

        npc_data, session = session_utils.auto_start_default_npc_conversation(
            db, player_id, area, state['model_name'], state['story'], state['ChatSession'], TerminalFormatter)
        if npc_data and session: state_changes['current_npc'], state_changes['chat_session'] = npc_data, session
        elif not (npc_data and session) : print(f"{TerminalFormatter.YELLOW}You are in {area}. Use /talk or /who.{TerminalFormatter.RESET}")
    elif len(matches) > 1: print(f"{TerminalFormatter.YELLOW}⚠️ Ambiguous area '{args}'. Matches: {', '.join(sorted(matches))}{TerminalFormatter.RESET}")
    else: print(f"{TerminalFormatter.YELLOW}⚠️ Area '{args}' not found. Known: {', '.join(sorted(known_areas))}{TerminalFormatter.RESET}")
    # Return only the changes to be applied to the state, plus status flags
    return {**state_changes, 'status': 'ok', 'continue_loop': True}


def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']; db = state['db']; player_id = state['player_id']
    area = state['current_area']; npc_old = state['current_npc']; session_old = state['chat_session']
    model, story, ChatSession_cls = state['model_name'], state['story'], state['ChatSession']
    if not area: print(f"{TF.YELLOW}Not in area. Use /go.{TF.RESET}"); return {'status': 'ok', 'continue_loop': True}
    if not args: print(f"{TF.YELLOW}Usage: /talk <npc|.>{TF.RESET}"); return {'status': 'ok', 'continue_loop': True}

    target_npc_info = None; talk = False; state_changes: Dict[str, Any] = {}
    all_npcs = session_utils.refresh_known_npcs_list(db, TF); npcs_here = [n for n in all_npcs if n.get('area','').lower() == area.lower()]

    if args == RANDOM_TALK_SYNTAX:
        if not npcs_here: print(f"{TF.YELLOW}No NPCs in {area}.{TF.RESET}")
        else: target_npc_info = random.choice(npcs_here); print(f"{TF.DIM}Random: {target_npc_info['name']}{TF.RESET}"); talk = True
    else:
        prefix = args.lower()
        matches = [n for n in npcs_here if n.get('name','').lower().startswith(prefix)]
        if len(matches) == 1: target_npc_info = matches[0]; print(f"{TF.DIM}Match: {target_npc_info['name']}{TF.RESET}"); talk = True
        elif len(matches) > 1: print(f"{TF.YELLOW}Ambiguous '{args}'. Matches: {', '.join(m.get('name','') for m in matches)}{TF.RESET}")
        else: print(f"{TF.YELLOW}NPC '{args}' not found in {area}.{TF.RESET}")

    if talk and target_npc_info:
        if npc_old and npc_old.get('code') == target_npc_info.get('code'): print(f"{TF.DIM}Already talking to {target_npc_info['name']}.{TF.RESET}")
        else:
            print(f"{TF.DIM}Saving chat...{TF.RESET}")
            session_utils.save_current_conversation(db, player_id, npc_old, session_old, TF)
            npc_data, new_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, area, target_npc_info['name'], model, story, ChatSession_cls, TF)
            if npc_data and new_session: state_changes.update({'current_npc': npc_data, 'chat_session': new_session})
            else: state_changes.update({'current_npc': None, 'chat_session': None})
    return {**state_changes, 'status': 'ok', 'continue_loop': True}

def handle_who(state: Dict[str, Any]) -> HandlerResult:
    TF=state['TerminalFormatter'];db=state['db'];area=state['current_area']
    if not area:print(f"{TF.YELLOW}Not in area.{TF.RESET}");return{'status':'ok','continue_loop':True}
    all_npcs=session_utils.refresh_known_npcs_list(db,TF);npcs_here=[n for n in all_npcs if n.get('area','').lower()==area.lower()]
    if not npcs_here:print(f"\n{TF.YELLOW}No NPCs in {area}.{TF.RESET}")
    else:print(f"\n{TF.YELLOW}NPCs in '{area}':{TF.RESET}");[print(f"  {TF.DIM}- {n.get('name','???')} ({n.get('role','???')}){TF.RESET}")for n in sorted(npcs_here,key=lambda x:x.get('name','').lower())]
    return{'status':'ok','continue_loop':True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
    TF=state['TerminalFormatter'];area=state['current_area'];npc=state['current_npc'];session=state['chat_session']
    loc=f"Location: {TF.BOLD}{area or 'Nowhere'}{TF.RESET}";npc_name=npc['name']if npc and'name'in npc else'Nobody'
    talking=f"Talking to: {TF.BOLD}{npc_name}{TF.RESET}"
    if npc and session and session.get_player_hint():hint=session.get_player_hint();talking+=f"\n  {TF.DIM}(Hint: {hint[:70]}{'...'if len(hint)>70 else''}){TF.RESET}"
    print(f"\n{TF.CYAN}{loc}\n{talking}{TF.RESET}");return{'status':'ok','continue_loop':True}

# --- CORRECTED handle_npcs ---
def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    try:
        # This import should be at the top of the file if it's a common utility
        from main_utils import format_npcs_list

        # print(f"{TF.DIM}Fetching list of all known NPCs...{TF.RESET}") # Less verbose
        all_npcs = session_utils.refresh_known_npcs_list(db, TF)

        # This logic is now correctly inside the try block
        if not all_npcs:
            print(f"{TF.YELLOW}No NPC data could be loaded.{TF.RESET}")
        else:
            print(format_npcs_list(all_npcs))

    except ImportError:
        print(f"{TF.RED}Error: main_utils.format_npcs_list utility missing.{TF.RESET}")
    except Exception as e: # Catch other potential errors (e.g., from DB calls)
        print(f"{TF.RED}Error fetching or displaying NPCs: {e}{TF.RESET}")
        # traceback.print_exc() # For debugging

    return {'status': 'ok', 'continue_loop': True}
# --- END CORRECTION ---

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
    TF=state['TerminalFormatter'];session=state['chat_session'];npc=state['current_npc'];fmt_stats=state['format_stats']
    if not session or not npc:print(f"{TF.YELLOW}Not in chat.{TF.RESET}");return{'status':'ok','continue_loop':True}
    ls=session.get_last_stats()
    if ls:print(f"\n{TF.DIM}{'-'*15}Last Turn Stats{'-'*15}{TF.RESET}");print(fmt_stats(ls))
    else:print(f"{TF.YELLOW}No last turn stats.{TF.RESET}")
    return{'status':'ok','continue_loop':True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
    TF=state['TerminalFormatter'];session=state['chat_session'];npc=state['current_npc']
    if not session or not npc:print(f"{TF.YELLOW}Not in chat.{TF.RESET}");return{'status':'ok','continue_loop':True}
    print(f"\n{TF.DIM}{'-'*15}Session Stats{'-'*15}{TF.RESET}");print(session.format_session_stats())
    return{'status':'ok','continue_loop':True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
    TF=state['TerminalFormatter'];session=state['chat_session']
    if not session:print(f"{TF.YELLOW}Not in chat to clear.{TF.RESET}")
    else:session.clear_memory()
    return{'status':'ok','continue_loop':True}


def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
    state['npc_made_new_response_this_turn'] = False
    if not user_input.strip(): return state

    TerminalFormatter = state.get('TerminalFormatter')
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')
    format_stats_func = state.get('format_stats')
    command_processed_and_took_turn = False

    handler_returned_payload: Dict[str, Any] = {}

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
                if command in ['go', 'talk', 'give']:
                    handler_returned_payload = handler_func(args, state)
                else:
                    handler_returned_payload = handler_func(state)

                state.update(handler_returned_payload)

                if state.get('status') == 'exit': return state
                command_processed_and_took_turn = True
            elif command == 'history':
                if chat_session: print(f"\n{TerminalFormatter.DIM}--- History ---{TerminalFormatter.RESET}\n{json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)}")
                else: print(f"{TerminalFormatter.YELLOW}No active chat.{TerminalFormatter.RESET}")
                command_processed_and_took_turn = True
            else: print(f"{TerminalFormatter.YELLOW}Unknown cmd '/{command}'.{TerminalFormatter.RESET}"); command_processed_and_took_turn = True
        except Exception as e: print(f"{TerminalFormatter.RED}Cmd err '/{command}': {e}{TerminalFormatter.RESET}"); command_processed_and_took_turn = True

    force_npc_turn = state.pop('force_npc_turn_after_command', False)

    if force_npc_turn and current_npc and chat_session:
        if not chat_session.messages or chat_session.messages[-1].get("role") != "user":
            chat_session.add_message("user", "[Player awaits NPC reaction to action...]")

        # print(f"{TerminalFormatter.DIM}{current_npc.get('name', 'NPC')} considers your action...{TerminalFormatter.RESET}") # Less verbose
        try:
            _response_text, stats = chat_session.ask(
                prompt="[NPC reacts]",
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            state['npc_made_new_response_this_turn'] = True
            print()
            if state.get('auto_show_stats', False) and stats and format_stats_func: print(format_stats_func(stats))
        except Exception as e: state['npc_made_new_response_this_turn'] = False; print(f"{TerminalFormatter.RED}NPC reaction err: {e}{TerminalFormatter.RESET}")
        # This counts as a turn where NPC responded.
    elif not command_processed_and_took_turn and current_npc and chat_session:
        try:
            # print(f"{TerminalFormatter.DIM}Processing input to {current_npc.get('name', 'NPC')}...{TerminalFormatter.RESET}")
            _response_text, stats = chat_session.ask(
                user_input,
                stream=state.get('use_stream', True),
                collect_stats=True
            )
            state['npc_made_new_response_this_turn'] = True
            print()
            if state.get('auto_show_stats', False) and stats and format_stats_func: print(format_stats_func(stats))
        except Exception as e: state['npc_made_new_response_this_turn'] = False; print(f"{TerminalFormatter.RED}Chat err: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
    elif not command_processed_and_took_turn and user_input:
        print(f"{TerminalFormatter.YELLOW}Not talking to anyone. Use /go, then /talk.{TerminalFormatter.RESET}")

    return state