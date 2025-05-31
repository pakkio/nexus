import json
import random
import traceback
import re
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
import session_utils

try:
  import hint_manager
  from player_profile_manager import get_distilled_profile_insights_for_npc
except ImportError:
  print("WARNING (command_processor): hint_manager.py or player_profile_manager.py not found. Advanced /hint or /profile features will not fully function.")
  class hint_manager:
    @staticmethod
    def generate_cache_key(state): return "fallback_key"
    @staticmethod
    def summarize_conversation_for_lyra(chat_history, llm_wrapper_func, model_name, TF): return "[Summary unavailable]"
    @staticmethod
    def build_initial_lyra_prompt(summary, player_data, player_profile, stashed_npc_data, TF, story_context): return "Lyra, the Seeker needs guidance."
  def get_distilled_profile_insights_for_npc(player_profile, current_npc_data, story_context_summary, llm_wrapper_func, model_name, TF):
    return "[Profile insights unavailable for this NPC]"

RANDOM_TALK_SYNTAX = '.'
HandlerResult = Dict[str, Any]

def _add_profile_action(state: Dict[str, Any], action_description: str):
  if 'actions_this_turn_for_profile' not in state:
    state['actions_this_turn_for_profile'] = []
  state['actions_this_turn_for_profile'].append(action_description)

def handle_exit(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  player_id = state['player_id']
  if state.get('in_lyra_hint_mode'):
    print(f"\n{TF.DIM}Exiting Lyra consultation mode before quitting...{TF.RESET}")
    state = handle_endhint(state)
  print(f"\n{TF.DIM}Saving last active conversation (if any)...{TF.RESET}")
  session_utils.save_current_conversation(
    state['db'], player_id, state.get('current_npc'), state.get('chat_session'), TF
  )
  print(f"{TF.YELLOW}Arrivederci! Leaving Eldoria... for now.{TF.RESET}")
  _add_profile_action(state, "Used /exit command")
  return {**state, 'status': 'exit'}

def handle_help(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  try:
    from main_utils import get_help_text
    print(get_help_text())
  except ImportError:
    print(f"{TF.RED}Error: Help utility not found.{TF.RESET}")
    print("Basic commands: /exit, /go, /areas, /talk, /who, /whereami, /npcs, /hint, /endhint, /inventory, /give, /stats, /clear, /history, /profile, /profile_for_npc")
  _add_profile_action(state, "Used /help command")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_hint(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  player_id = state['player_id']
  db = state['db']
  ChatSession_class = state['ChatSession']
  llm_wrapper_func = state.get('llm_wrapper_func')
  debug_mode = state.get('debug_mode', False)
  
  _add_profile_action(state, "Used /hint command")
  
  if not llm_wrapper_func:
    print(f"{TF.RED}LLM wrapper function not available in game state. Advanced hint cannot proceed.{TF.RESET}")
    if state.get('chat_session') and state.get('current_npc') and not state.get('in_lyra_hint_mode'):
      simple_hint = state['chat_session'].get_player_hint()
      if simple_hint: 
        print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Hint ({state['current_npc'].get('name', 'your current interaction')}):{TF.RESET}\n  {TF.CYAN}➢ {simple_hint}{TF.RESET}")
      else: 
        print(f"{TF.YELLOW}No specific hint for {state['current_npc'].get('name', 'this interaction')} right now.{TF.RESET}")
    else: 
      print(f"{TF.YELLOW}Not in a regular conversation to get a simple hint, or LLM for advanced hint is unavailable.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if state.get('in_lyra_hint_mode'):
    print(f"{TF.YELLOW}You are already consulting Lyra. Use /endhint to return.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if not state.get('current_npc') or not state.get('chat_session'):
    print(f"{TF.YELLOW}You need to be in a situation (talking to an NPC) to ask Lyra about.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if state['current_npc'].get('name', '').lower() == "lyra":
    print(f"{TF.YELLOW}You are already talking to Lyra. Ask her directly.{TF.RESET}")
    lyra_player_hint = state['chat_session'].get_player_hint()
    if lyra_player_hint: 
      print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Lyra's current general guidance for you:{TF.RESET}\n  {TF.CYAN}➢ {lyra_player_hint}{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  current_cache_key = hint_manager.generate_cache_key(state)
  cached_hint_data = state.get('lyra_hint_cache')
  lyra_npc_data_from_db = db.get_npc("Sanctum of Whispers", "Lyra")
  
  if not lyra_npc_data_from_db:
    print(f"{TF.RED}Critical Error: Lyra's NPC data not found! Cannot consult.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  player_profile = state.get('player_profile_cache', {})
  
  if cached_hint_data and cached_hint_data.get('key') == current_cache_key and \
     (time.time() - cached_hint_data.get('timestamp', 0)) < 300:
    if debug_mode:
      print(f"{TF.DIM}Recalling Lyra's recent guidance for this situation...{TF.RESET}")
    lyra_hint_session_restored = ChatSession_class(model_name=state['model_name'])
    lyra_system_prompt = session_utils.build_system_prompt(
      lyra_npc_data_from_db, state['story'], TF, player_id, db,
      player_profile=player_profile,
      llm_wrapper_func=llm_wrapper_func, llm_model_name=state['model_name']
    )
    lyra_hint_session_restored.set_system_prompt(lyra_system_prompt)
    for msg in cached_hint_data.get('lyra_chat_history', []):
      if msg.get("role") != "system":
        lyra_hint_session_restored.add_message(msg['role'], msg['content'])
    
    if lyra_hint_session_restored.messages and lyra_hint_session_restored.messages[-1]['role'] == 'assistant':
      lyra_color = session_utils.get_npc_color("Lyra", TF)
      print(f"\n{TF.BOLD}{lyra_color}{lyra_npc_data_from_db.get('name', 'Lyra')} (recalled) > {TF.RESET}")
      print(TF.format_terminal_text(lyra_hint_session_restored.messages[-1]['content']))
    else: 
      print(f"{TF.YELLOW}Could not recall Lyra's last specific advice for this exact state, preparing fresh consultation.{TF.RESET}")
    
    state['stashed_chat_session'] = state['chat_session']
    state['stashed_npc'] = state['current_npc']
    state['in_lyra_hint_mode'] = True
    state['current_npc'] = lyra_npc_data_from_db
    state['chat_session'] = lyra_hint_session_restored
    print(f"{TF.DIM}You can ask Lyra a follow-up, or type /endhint to return.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if debug_mode:
    print(f"{TF.DIM}Reaching out to Lyra for fresh guidance... (This may take a moment){TF.RESET}")
  
  stashed_session_temp = state['chat_session']
  stashed_npc_temp = state['current_npc']
  conversation_summary = "[No current interaction to summarize or summarization failed]"
  
  if stashed_session_temp and stashed_session_temp.messages and llm_wrapper_func:
    try:
      if debug_mode:
        print(f"{TF.DIM}Summarizing current interaction with {stashed_npc_temp.get('name','NPC')} for Lyra...{TF.RESET}")
      conversation_summary = hint_manager.summarize_conversation_for_lyra(
        stashed_session_temp.get_history(), llm_wrapper_func, state.get('model_name'), TF)
    except Exception as e: 
      conversation_summary = f"[Error during summarization: {e}]"

  player_state_data = db.load_player_state(player_id) or {}
  player_data_for_lyra = {
    'inventory': state.get('player_inventory', []), 
    'credits': state.get('player_credits_cache', 0),
    'plot_flags': player_state_data.get('plot_flags', {}),
    'current_area': stashed_npc_temp.get('area', state.get('current_area', 'Unknown')) if stashed_npc_temp else state.get('current_area', 'Unknown')
  }

  initial_lyra_user_prompt = hint_manager.build_initial_lyra_prompt(
    conversation_summary, player_data_for_lyra, player_profile, stashed_npc_temp, TF, state['story']
  )

  lyra_hint_session_new = ChatSession_class(model_name=state['model_name'])
  lyra_system_prompt = session_utils.build_system_prompt(
    lyra_npc_data_from_db, state['story'], TF, player_id, db,
    conversation_summary_for_lyra=conversation_summary,
    player_profile=player_profile,
    llm_wrapper_func=llm_wrapper_func, llm_model_name=state['model_name']
  )
  lyra_hint_session_new.set_system_prompt(lyra_system_prompt)

  lyra_color = session_utils.get_npc_color("Lyra", TF)
  print(f"\n{TF.BOLD}{lyra_color}{lyra_npc_data_from_db.get('name', 'Lyra')} > {TF.RESET}")
  
  try:
    _response_text, stats = lyra_hint_session_new.ask(initial_lyra_user_prompt, "Lyra", state.get('use_stream', True), True)
    if not _response_text.strip() and not (stats and stats.get("error")):
      print(f"{TF.DIM}{TF.ITALIC}*Lyra ponders deeply...*{TF.RESET}")
    if state.get('auto_show_stats', False) and stats and state.get('format_stats'): 
      print(state['format_stats'](stats))
  except Exception as e: 
    print(f"{TF.RED}Error during Lyra consultation: {e}{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  state['lyra_hint_cache'] = {
    'key': current_cache_key, 
    'lyra_chat_history': lyra_hint_session_new.get_history(), 
    'timestamp': time.time()
  }
  state['stashed_chat_session'] = stashed_session_temp
  state['stashed_npc'] = stashed_npc_temp
  state['in_lyra_hint_mode'] = True
  state['current_npc'] = lyra_npc_data_from_db
  state['chat_session'] = lyra_hint_session_new
  print(f"{TF.DIM}You can continue asking Lyra for advice, or type /endhint to return.{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_endhint(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  _add_profile_action(state, "Used /endhint command")
  if not state.get('in_lyra_hint_mode'):
    print(f"{TF.YELLOW}You are not currently consulting Lyra.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  restored_npc = state.get('stashed_npc')
  restored_session = state.get('stashed_chat_session')
  state['in_lyra_hint_mode'] = False
  state['current_npc'] = restored_npc
  state['chat_session'] = restored_session
  state['stashed_npc'] = None
  state['stashed_chat_session'] = None

  if restored_npc and restored_session:
    print(f"\n{TF.DIM}You withdraw from your consultation with Lyra and return your attention to {restored_npc.get('name', 'your previous interaction')}...{TF.RESET}")
    if restored_session.messages:
      print(f"{TF.DIM}--- Resuming conversation with {restored_npc.get('name', 'NPC')} ---{TF.RESET}")
      last_msg_count = min(2, len(restored_session.messages))
      for msg in restored_session.messages[-last_msg_count:]:
        role_display = "You" if msg['role'] == 'user' else restored_npc.get('name', 'NPC')
        if msg['role'] == 'user':
          color = TF.GREEN
        else:
          color = session_utils.get_npc_color(restored_npc.get('name', 'NPC'), TF)
        print(f"\n{TF.BOLD}{color}{role_display} > {TF.RESET}")
        print(TF.format_terminal_text(msg['content']))
      print()
  else:
    state['current_npc'] = None
    state['chat_session'] = None
    print(f"{TF.YELLOW}Returned from hint mode, but previous context was unclear. Please use /go or /talk.{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_inventory(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  _add_profile_action(state, "Used /inventory command")
  
  inventory_list = state.get('player_inventory', db.load_inventory(player_id))
  current_credits = state.get('player_credits_cache', db.get_player_credits(player_id))
  
  print(f"\n{TF.BRIGHT_GREEN}{TF.BOLD}--- Your Inventory ---{TF.RESET}")
  if inventory_list: 
    [print(f"  {TF.GREEN}❖ {item.title()}{TF.RESET}") for item in inventory_list]
  else: 
    print(f"  {TF.DIM}(Your inventory is empty){TF.RESET}")
  print(f"{TF.BRIGHT_YELLOW}Credits: {current_credits}{TF.RESET}")
  print(f"{TF.BRIGHT_GREEN}{'-'*22}{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_give(args: str, state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  current_npc = state['current_npc']
  chat_session = state['chat_session']
  command_result_payload: Dict[str, Any] = {}

  if state.get('in_lyra_hint_mode'):
    print(f"{TF.YELLOW}You cannot use /give while consulting Lyra. Use /endhint first.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if not current_npc or not chat_session:
    print(f"{TF.YELLOW}Not talking to anyone to give an item to.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  input_str = args.strip()
  if not input_str: 
    print(f"{TF.YELLOW}What do you want to give? Usage: /give <item_name_or_amount Credits>{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  credit_match = re.match(r"(\d+)\s+(credits?)$", input_str, re.IGNORECASE)
  item_name_for_log_and_action = ""
  
  if credit_match:
    amount_to_give = int(credit_match.group(1))
    player_current_credits = state.get('player_credits_cache', db.get_player_credits(player_id))
    if amount_to_give <= 0: 
      print(f"{TF.YELLOW}You must give a positive amount of Credits.{TF.RESET}")
      return {**state, 'status': 'ok', 'continue_loop': True}
    if player_current_credits >= amount_to_give:
      if db.update_player_credits(player_id, -amount_to_give, state):
        item_name_for_log_and_action = f"{amount_to_give} Credits"
        command_result_payload['item_given_to_npc_this_turn'] = {
          'item_name': item_name_for_log_and_action, 
          'type': 'currency', 
          'amount': amount_to_give, 
          'npc_code': current_npc.get('code')
        }
    else: 
      print(f"{TF.YELLOW}You don't have enough Credits. You only have {player_current_credits}.{TF.RESET}")
      return {**state, 'status': 'ok', 'continue_loop': True}
  else:
    item_name_to_give = input_str
    cleaned_item_name_for_check = db._clean_item_name(item_name_to_give)
    if not db.check_item_in_inventory(player_id, cleaned_item_name_for_check):
      print(f"{TF.YELLOW}You don't have '{item_name_to_give}' (or similar) in your inventory.{TF.RESET}")
      return {**state, 'status': 'ok', 'continue_loop': True}
    if db.remove_item_from_inventory(player_id, cleaned_item_name_for_check, state):
      item_name_for_log_and_action = item_name_to_give.strip()
      command_result_payload['item_given_to_npc_this_turn'] = {
        'item_name': cleaned_item_name_for_check, 
        'original_user_input_item_name': item_name_for_log_and_action, 
        'type': 'item', 
        'npc_code': current_npc.get('code')
      }
    else: 
      print(f"{TF.RED}Error: Could not remove '{item_name_to_give}' from inventory (unexpected).{TF.RESET}")
      return {**state, 'status': 'ok', 'continue_loop': True}

  if item_name_for_log_and_action:
    print(f"{TF.DIM}You hand {item_name_for_log_and_action} to {current_npc['name']}.{TF.RESET}")
    player_action_message = f"*You hand over {item_name_for_log_and_action} to {current_npc['name']}.*"
    chat_session.add_message("user", player_action_message)
    command_result_payload['force_npc_turn_after_command'] = True
    _add_profile_action(state, f"Gave '{item_name_for_log_and_action}' to NPC '{current_npc['name']}'")

  state.update(command_result_payload)
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_go(args: str, state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  _add_profile_action(state, f"Used /go command with args: '{args}'")
  
  if state.get('in_lyra_hint_mode'): 
    print(f"{TF.YELLOW}You cannot use /go while consulting Lyra. Use /endhint first.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  current_npc_old = state.get('current_npc')
  chat_session_old = state.get('chat_session')
  
  if not args: 
    print(f"{TF.YELLOW}Usage: /go <area_name_fragment>{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  target_terms = args.lower().split()
  all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
  known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
  matches = []
  
  if target_terms: 
    matches = [area_name_full for area_name_full in known_areas if all(term in area_name_full.lower() for term in target_terms)]

  new_state_part: Dict[str, Any] = {}
  
  if len(matches) == 1:
    area = matches[0]
    current_area_from_state = state.get('current_area')
    if current_area_from_state is not None and current_area_from_state.lower() == area.lower():
      print(f"{TF.DIM}You are already in {area}.{TF.RESET}")
      return {**state, 'status': 'ok', 'continue_loop': True}
    
    print(f"{TF.DIM}Area match: {area}{TF.RESET}")
    if chat_session_old:
      print(f"{TF.DIM}Saving previous conversation with {current_npc_old.get('name', 'NPC')}...{TF.RESET}")
      session_utils.save_current_conversation(db, player_id, current_npc_old, chat_session_old, TF)
    
    print(f"{TF.CYAN}Moving to: {area}...{TF.RESET}")
    new_state_part.update({'current_area': area, 'current_npc': None, 'chat_session': None})
    
    llm_wrapper_for_npc_setup = state.get('llm_wrapper_func')
    npc_data, session = session_utils.auto_start_default_npc_conversation(
      db, player_id, area, state['model_name'], state['story'], state['ChatSession'], TF,
      llm_wrapper_for_profile_distillation=llm_wrapper_for_npc_setup
    )
    if npc_data and session: 
      new_state_part['current_npc'] = npc_data
      new_state_part['chat_session'] = session
  elif len(matches) > 1: 
    print(f"{TF.YELLOW}⚠️ Ambiguous area '{args}'. Matches: {', '.join(sorted(matches))}{TF.RESET}")
  else: 
    print(f"{TF.YELLOW}⚠️ Area '{args}' not found. Known areas can be listed with /areas.{TF.RESET}")

  state.update(new_state_part)
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  _add_profile_action(state, f"Used /talk command with args: '{args}'")
  
  if state.get('in_lyra_hint_mode'): 
    print(f"{TF.YELLOW}You cannot use /talk while consulting Lyra. Use /endhint first.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  area = state.get('current_area')
  npc_old = state.get('current_npc')
  session_old = state.get('chat_session')
  model, story, ChatSession_cls = state['model_name'], state['story'], state['ChatSession']
  
  if not area: 
    print(f"{TF.YELLOW}Not in an area. Use /go.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if not args: 
    print(f"{TF.YELLOW}Usage: /talk <npc_name|.>{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  target_npc_info = None
  talk_initiated = False
  new_state_part: Dict[str, Any] = {}
  
  all_npcs = session_utils.refresh_known_npcs_list(db, TF)
  npcs_here = [n for n in all_npcs if n.get('area','').lower() == area.lower()]
  
  if args == RANDOM_TALK_SYNTAX:
    if not npcs_here: 
      print(f"{TF.YELLOW}No NPCs in {area}.{TF.RESET}")
      return state
    eligible_npcs = [n for n in npcs_here if not (npc_old and n.get('code') == npc_old.get('code'))]
    if not eligible_npcs and npc_old: 
      print(f"{TF.DIM}Only {npc_old.get('name')} is here, and you're already talking to them.{TF.RESET}")
      return state
    elif not eligible_npcs and not npc_old: 
      print(f"{TF.YELLOW}No other NPCs in {area} to talk to randomly.{TF.RESET}")
      return state
    target_npc_info = random.choice(eligible_npcs if eligible_npcs else npcs_here)
    print(f"{TF.DIM}Randomly approaching: {target_npc_info['name']}{TF.RESET}")
    talk_initiated = True
  else:
    prefix = args.lower()
    matches = [n for n in npcs_here if n.get('name','').lower().startswith(prefix)]
    if len(matches) == 1: 
      target_npc_info = matches[0]
      talk_initiated = True
    elif len(matches) > 1: 
      print(f"{TF.YELLOW}Ambiguous NPC name '{args}'. Matches: {', '.join(m.get('name','') for m in matches)}{TF.RESET}")
    else: 
      print(f"{TF.YELLOW}NPC '{args}' not found in {area}.{TF.RESET}")

  if talk_initiated and target_npc_info:
    if npc_old and npc_old.get('code') == target_npc_info.get('code'): 
      print(f"{TF.DIM}You are already talking to {target_npc_info['name']}.{TF.RESET}")
    else:
      if session_old:
        print(f"{TF.DIM}Saving previous conversation with {npc_old.get('name','NPC')}...{TF.RESET}")
        session_utils.save_current_conversation(db, player_id, npc_old, session_old, TF)
      
      llm_wrapper_for_npc_setup = state.get('llm_wrapper_func')
      npc_data, new_session = session_utils.start_conversation_with_specific_npc(
        db, player_id, area, target_npc_info['name'], model, story, ChatSession_cls, TF,
        llm_wrapper_for_profile_distillation=llm_wrapper_for_npc_setup
      )
      if npc_data and new_session: 
        new_state_part.update({'current_npc': npc_data, 'chat_session': new_session})
      else: 
        new_state_part.update({'current_npc': None, 'chat_session': None})
        print(f"{TF.RED}Error initiating talk with {target_npc_info.get('name', 'NPC')}.{TF.RESET}")

  state.update(new_state_part)
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_who(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  _add_profile_action(state, "Used /who command")
  
  current_display_area = state.get('current_area')
  if state.get('in_lyra_hint_mode'):
    stashed_npc_data = state.get('stashed_npc', {})
    stashed_area = stashed_npc_data.get('area', state.get('current_area', 'Unknown Area'))
    print(f"{TF.YELLOW}Currently consulting Lyra. Your physical location is {stashed_area}. NPCs there:{TF.RESET}")
    current_display_area = stashed_area

  if not current_display_area: 
    print(f"{TF.YELLOW}Not in an area. Use /go.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  all_npcs = session_utils.refresh_known_npcs_list(db, TF)
  npcs_here = [n for n in all_npcs if n.get('area','').lower() == current_display_area.lower()]
  
  if not npcs_here:
    print(f"\n{TF.YELLOW}No NPCs in {current_display_area}.{TF.RESET}")
  else:
    if not state.get('in_lyra_hint_mode'): 
      print(f"\n{TF.YELLOW}NPCs in '{current_display_area}':{TF.RESET}")
    for n in sorted(npcs_here, key=lambda x: x.get('name','').lower()): 
      npc_color = session_utils.get_npc_color(n.get('name', 'NPC'), TF)
      print(f"  {TF.DIM}- {npc_color}{n.get('name','???')}{TF.RESET} {TF.DIM}({n.get('role','???')}){TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_whereami(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  _add_profile_action(state, "Used /whereami command")
  
  is_hint_mode = state.get('in_lyra_hint_mode', False)
  current_location_area = state.get('current_area', 'Nowhere')
  current_talking_to_npc = state.get('current_npc')
  current_chat_session_obj = state.get('chat_session')
  
  display_area = current_location_area
  display_npc_name = "Nobody"
  hint_for_display = None
  
  if is_hint_mode:
    stashed_npc_data = state.get('stashed_npc')
    stashed_area = stashed_npc_data.get('area', "Unknown (stashed)") if stashed_npc_data else "Unknown (stashed)"
    display_area = f"{stashed_area} (Physically)"
    lyra_name = current_talking_to_npc.get('name', 'Lyra') if current_talking_to_npc else 'Lyra'
    display_npc_name = f"{lyra_name} (In Consultation)"
  else:
    if current_talking_to_npc:
      display_npc_name = current_talking_to_npc.get('name', 'Unknown NPC')
      if current_chat_session_obj: 
        hint_for_display = current_chat_session_obj.get_player_hint()

  loc_msg = f"Location: {TF.BOLD}{display_area}{TF.RESET}"
  
  # FIXED: Use NPC color for talking status
  if current_talking_to_npc and not is_hint_mode:
    npc_color = session_utils.get_npc_color(current_talking_to_npc.get('name', 'NPC'), TF)
    talking_msg = f"Talking to: {TF.BOLD}{npc_color}{display_npc_name}{TF.RESET}"
  elif is_hint_mode:
    lyra_color = session_utils.get_npc_color("Lyra", TF)
    talking_msg = f"Talking to: {TF.BOLD}{lyra_color}{display_npc_name}{TF.RESET}"
  else:
    talking_msg = f"Talking to: {TF.BOLD}{display_npc_name}{TF.RESET}"
  
  if hint_for_display and not is_hint_mode: 
    talking_msg += f"\n  {TF.DIM}(Hint for {display_npc_name}: {hint_for_display[:70]}{'...' if len(hint_for_display) > 70 else ''}){TF.RESET}"

  print(f"\n{TF.CYAN}{loc_msg}\n{talking_msg}{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_npcs(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  _add_profile_action(state, "Used /npcs command")
  
  try:
    from main_utils import format_npcs_list
    all_npcs = session_utils.refresh_known_npcs_list(db, TF)
    if not all_npcs: 
      print(f"{TF.YELLOW}No NPC data could be loaded.{TF.RESET}")
    else: 
      print(format_npcs_list(all_npcs))
  except ImportError: 
    print(f"{TF.RED}Error: main_utils.format_npcs_list utility missing.{TF.RESET}")
  except Exception as e: 
    print(f"{TF.RED}Error fetching or displaying NPCs: {e}{TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_areas(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  _add_profile_action(state, "Used /areas command")
  
  all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
  known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
  
  if not known_areas: 
    print(f"{TF.YELLOW}No known areas found.{TF.RESET}")
  else:
    print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Available Areas to /go to:{TF.RESET}")
    for area_name in known_areas: 
      print(f"  {TF.CYAN}➢ {area_name}{TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_profile(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  _add_profile_action(state, "Used /profile command")
  
  profile_data = state.get('player_profile_cache', db.load_player_profile(player_id))
  
  print(f"\n{TF.BRIGHT_YELLOW}{TF.BOLD}--- Your Psychological Profile ---{TF.RESET}")
  if profile_data:
    print(f"{TF.YELLOW}Core Traits:{TF.RESET}")
    for trait, value in profile_data.get("core_traits", {}).items():
      print(f"  {TF.DIM}- {trait.replace('_', ' ').capitalize()}: {value}/10{TF.RESET}")
    
    print(f"\n{TF.YELLOW}Decision Patterns:{TF.RESET}")
    patterns = profile_data.get("decision_patterns", [])
    if patterns: 
      [print(f"  {TF.DIM}- {p.replace('_', ' ').capitalize()}{TF.RESET}") for p in patterns]
    else: 
      print(f"  {TF.DIM}(None observed yet){TF.RESET}")
    
    print(f"\n{TF.YELLOW}Veil Perception:{TF.RESET} {TF.DIM}{profile_data.get('veil_perception', 'Undefined').replace('_', ' ').capitalize()}{TF.RESET}")
    print(f"{TF.YELLOW}Interaction Style:{TF.RESET} {TF.DIM}{profile_data.get('interaction_style_summary', 'Undefined')}{TF.RESET}")
    
    print(f"\n{TF.YELLOW}Key Experiences:{TF.RESET}")
    experiences = profile_data.get("key_experiences_tags", [])
    if experiences: 
      [print(f"  {TF.DIM}- {exp.replace('_', ' ').capitalize()}{TF.RESET}") for exp in experiences]
    else: 
      print(f"  {TF.DIM}(None recorded yet){TF.RESET}")
    
    print(f"\n{TF.YELLOW}Trust Levels:{TF.RESET}")
    print(f"  {TF.DIM}- General: {profile_data.get('trust_levels', {}).get('general', 5)}/10{TF.RESET}")
    
    print(f"\n{TF.YELLOW}Inferred Motivations:{TF.RESET}")
    motivations = profile_data.get("inferred_motivations", [])
    if motivations: 
      [print(f"  {TF.DIM}- {m.replace('_', ' ').capitalize()}{TF.RESET}") for m in motivations]
    else: 
      print(f"  {TF.DIM}(Primary quest focus assumed){TF.RESET}")
  else:
    print(f"  {TF.DIM}(No profile data available. This is unexpected.){TF.RESET}")
  
  print(f"{TF.BRIGHT_YELLOW}{'-'*30}{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_profile_for_npc(state: Dict[str, Any]) -> HandlerResult:
  TF = state['TerminalFormatter']
  db = state['db']
  player_id = state['player_id']
  current_npc = state.get('current_npc')
  llm_wrapper_func = state.get('llm_wrapper_func')
  model_name = state.get('model_name')
  story_context = state.get('story', "")
  
  _add_profile_action(state, "Used /profile_for_npc command")
  
  if state.get('in_lyra_hint_mode'):
    print(f"{TF.YELLOW}This command is not available while consulting Lyra.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if not current_npc:
    print(f"{TF.YELLOW}You are not currently talking to an NPC.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  if not llm_wrapper_func or not model_name:
    print(f"{TF.RED}LLM tools not available to generate NPC insights for profile.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  profile_data = state.get('player_profile_cache', db.load_player_profile(player_id))
  npc_name = current_npc.get('name', 'Current NPC')
  npc_color = session_utils.get_npc_color(npc_name, TF)
  
  print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}--- Distilled Profile Insights for {npc_color}{npc_name}{TF.RESET}{TF.BRIGHT_CYAN}{TF.BOLD} ---{TF.RESET}")
  print(f"{TF.DIM}(This is what {npc_name} might subtly 'know' or infer about you based on your profile, used to tailor their responses. This is a debug view.){TF.RESET}")
  
  distilled_insights = get_distilled_profile_insights_for_npc(
    profile_data, current_npc, story_context, llm_wrapper_func, model_name, TF
  )
  
  if distilled_insights:
    print(f"{TF.CYAN}➢ {distilled_insights}{TF.RESET}")
  else:
    print(f"{TF.DIM}(No specific insights could be distilled for {npc_name} at this time, or an error occurred.){TF.RESET}")
  
  print(f"{TF.BRIGHT_CYAN}{'-'*40}{TF.RESET}")
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_stats(state: Dict[str, Any]) -> HandlerResult:
  _add_profile_action(state, "Used /stats command")
  TF = state['TerminalFormatter']
  session = state.get('chat_session')
  npc = state.get('curre_npc')
  fmt_stats = state['format_stats']
  
  if not session or not npc:
    print(f"{TF.YELLOW}Not in an active chat session to show stats for.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  ls = session.get_last_stats()
  npc_name_for_stats = npc.get('name', 'Current NPC')
  if state.get('in_lyra_hint_mode') and npc_name_for_stats.lower() == 'lyra': 
    npc_name_for_stats = "Lyra (Consultation)"
  
  if ls:
    print(f"\n{TF.DIM}{'-'*15}Last Turn Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
    print(fmt_stats(ls))
  else:
    print(f"{TF.YELLOW}No last turn stats available for {npc_name_for_stats}.{TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_session_stats(state: Dict[str, Any]) -> HandlerResult:
  _add_profile_action(state, "Used /session_stats command")
  TF = state['TerminalFormatter']
  session = state.get('chat_session')
  npc = state.get('current_npc')
  
  if not session or not npc:
    print(f"{TF.YELLOW}Not in an active chat session.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}

  npc_name_for_stats = npc.get('name', 'Current NPC')
  if state.get('in_lyra_hint_mode') and npc_name_for_stats.lower() == 'lyra': 
    npc_name_for_stats = "Lyra (Consultation)"
  
  print(f"\n{TF.DIM}{'-'*15}Session Stats ({npc_name_for_stats}){'-'*15}{TF.RESET}")
  print(session.format_session_stats())
  return {**state, 'status': 'ok', 'continue_loop': True}

def handle_clear(state: Dict[str, Any]) -> HandlerResult:
  _add_profile_action(state, "Used /clear command")
  TF = state['TerminalFormatter']
  session = state.get('chat_session')
  
  if not session:
    print(f"{TF.YELLOW}Not in an active chat to clear.{TF.RESET}")
  else:
    session.clear_memory()
    npc_name = state.get('current_npc', {}).get('name', 'current')
    mode_info = "(Lyra Consultation)" if state.get('in_lyra_hint_mode') else ""
    print(f"{TF.YELLOW}Conversation memory with {npc_name} {mode_info} has been cleared (in this session only).{TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}

def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
  state['npc_made_new_response_this_turn'] = False
  if not user_input.strip(): 
    return state

  TF = state.get('TerminalFormatter')
  chat_session = state.get('chat_session')
  current_npc = state.get('current_npc')
  fmt_stats_func = state.get('format_stats')
  is_in_lyra_hint_mode = state.get('in_lyra_hint_mode', False)
  debug_mode = state.get('debug_mode', False)
  command_processed_this_turn = False

  if user_input.startswith('/'):
    parts = user_input[1:].split(None, 1)
    command = parts[0].lower() if parts else ""
    args_str = parts[1] if len(parts) > 1 else ""
    
    command_handlers_map = {
      'exit': handle_exit, 'quit': handle_exit, 'help': handle_help,
      'go': handle_go, 'talk': handle_talk, 'who': handle_who, 'whereami': handle_whereami,
      'npcs': handle_npcs, 'areas': handle_areas,
      'stats': handle_stats, 'session_stats': handle_session_stats, 'clear': handle_clear,
      'hint': handle_hint, 'endhint': handle_endhint,
      'inventory': handle_inventory, 'inv': handle_inventory, 'give': handle_give,
      'profile': handle_profile, 'profile_for_npc': handle_profile_for_npc
    }
    
    try:
      if command in command_handlers_map:
        handler_func = command_handlers_map[command]
        if command in ['go', 'talk', 'give']: 
          state = handler_func(args_str, state)
        else: 
          state = handler_func(state)
        if state.get('status') == 'exit': 
          return state
        command_processed_this_turn = True
      elif command == 'history':
        _add_profile_action(state, "Used /history command")
        if chat_session and current_npc:
          print(f"\n{TF.DIM}--- History with {current_npc.get('name', 'current NPC')} ---{TF.RESET}")
          print(json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False))
        else: 
          print(f"{TF.YELLOW}No active chat session to show history for.{TF.RESET}")
        command_processed_this_turn = True
      else:
        print(f"{TF.YELLOW}Unknown command '/{command}'. Try /help.{TF.RESET}")
        command_processed_this_turn = True
    except Exception as e:
      print(f"{TF.RED}Error processing command '/{command}': {type(e).__name__} - {e}{TF.RESET}")
      traceback.print_exc()
      command_processed_this_turn = True
  else:
    _add_profile_action(state, f"Said to NPC: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")

  force_npc_turn_after_command = state.get('force_npc_turn_after_command', False)
  if force_npc_turn_after_command: 
    state.pop('force_npc_turn_after_command', None)

  needs_llm_call = False
  prompt_for_llm = user_input
  
  if not command_processed_this_turn: 
    needs_llm_call = True
  elif force_npc_turn_after_command and not is_in_lyra_hint_mode:
    prompt_for_llm = "[NPC reacts to player's action]"
    needs_llm_call = True

  if is_in_lyra_hint_mode and not command_processed_this_turn:
    needs_llm_call = True

  if needs_llm_call:
    if current_npc and chat_session:
      npc_name_for_prompt = current_npc.get('name', 'NPC')
      if is_in_lyra_hint_mode: 
        npc_name_for_prompt = "Lyra (Consultation)"
      
      npc_color = session_utils.get_npc_color(current_npc.get('name', 'NPC'), TF)
      if is_in_lyra_hint_mode:
        npc_color = session_utils.get_npc_color("Lyra", TF)
      
      if not (is_in_lyra_hint_mode and command_processed_this_turn and command == 'hint'):
         print(f"\n{TF.BOLD}{npc_color}{npc_name_for_prompt} > {TF.RESET}")
      
      try:
        _response_text, stats = chat_session.ask(
          prompt_for_llm, current_npc.get('name', 'NPC'),
          state.get('use_stream', True), True
        )
        if not _response_text.strip() and not (stats and stats.get("error")):
          placeholder_msg = f"{TF.DIM}{TF.ITALIC}*{npc_name_for_prompt} seems to ponder for a moment...*{TF.RESET}"
          if is_in_lyra_hint_mode: 
            placeholder_msg = f"{TF.DIM}{TF.ITALIC}*Lyra ponders deeply...*{TF.RESET}"
          print(placeholder_msg)
        
        state['npc_made_new_response_this_turn'] = True
        if _response_text.strip():
          _add_profile_action(state, f"NPC Response from {npc_name_for_prompt}: '{_response_text[:50]}{'...' if len(_response_text) > 50 else ''}'")
        
        if state.get('auto_show_stats', False) and stats and fmt_stats_func: 
          print(fmt_stats_func(stats))
        
        if is_in_lyra_hint_mode and state.get('lyra_hint_cache'):
          state['lyra_hint_cache']['lyra_chat_history'] = chat_session.get_history()
          state['lyra_hint_cache']['timestamp'] = time.time()
      except Exception as e:
        state['npc_made_new_response_this_turn'] = False
        print(f"{TF.RED}LLM Chat Error with {npc_name_for_prompt}: {type(e).__name__} - {e}{TF.RESET}")
        traceback.print_exc()
    elif user_input:
      print(f"{TF.YELLOW}You're not talking to anyone. Use /go to move to an area, then /talk <npc_name>.{TF.RESET}")
  
  return state
