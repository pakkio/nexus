import json
import random
import traceback
import re
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Callable

# --- Assuming 'nexus' is the root package or is on PYTHONPATH ---
# Import all modular command handlers
from command_handlers.handle_exit import handle_exit
from command_handlers.handle_help import handle_help # Or from command_handlers.handle+help import handle_help
from command_handlers.handle_go import handle_go
from command_handlers.handle_talk import handle_talk
from command_handlers.handle_who import handle_who
from command_handlers.handle_whereami import handle_whereami
from command_handlers.handle_npcs import handle_npcs
from command_handlers.handle_areas import handle_areas # Assuming specific file, not __init__.py
from command_handlers.handle_stats import handle_stats
from command_handlers.handle_session_stats import handle_session_stats
from command_handlers.handle_clear import handle_clear
from command_handlers.handle_hint import handle_hint
from command_handlers.handle_endhint import handle_endhint
from command_handlers.handle_inventory import handle_inventory
from command_handlers.handle_give import handle_give
from command_handlers.handle_profile import handle_profile
from command_handlers.heandle_profile_for_npc import handle_profile_for_npc # Corrected filename
from command_handlers.handle_history import handle_history

import session_utils # Direct import if session_utils.py is at the same level as command_processor.py
from command_handler_utils import HandlerResult, _add_profile_action, hint_manager, get_distilled_profile_insights_for_npc

# Updated command_handlers_map to use imported handlers
command_handlers_map: Dict[str, Callable] = {
  'exit': handle_exit, 'quit': handle_exit,
  'help': handle_help,
  'go': handle_go,
  'talk': handle_talk,
  'who': handle_who,
  'whereami': handle_whereami,
  'npcs': handle_npcs,
  'areas': handle_areas,
  'stats': handle_stats,
  'session_stats': handle_session_stats,
  'clear': handle_clear,
  'hint': handle_hint,
  'endhint': handle_endhint,
  'inventory': handle_inventory, 'inv': handle_inventory,
  'give': handle_give,
  'profile': handle_profile,
  'profile_for_npc': handle_profile_for_npc,
  'history': handle_history,
}

def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
  """
  Processes user input, dispatching to command handlers or LLM.
  This version uses the modular command handlers with absolute-style imports.
  """
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
      else:
        print(f"{TF.YELLOW}Unknown command '/{command}'. Try /help.{TF.RESET}")
        command_processed_this_turn = True
    except Exception as e:
      print(f"{TF.RED}Error processing command '/{command}': {type(e).__name__} - {e}{TF.RESET}")
      if debug_mode:
        traceback.print_exc()
      command_processed_this_turn = True

  force_npc_turn_after_command = state.get('force_npc_turn_after_command', False)
  if force_npc_turn_after_command:
    state.pop('force_npc_turn_after_command', None)

  needs_llm_call = False
  prompt_for_llm = user_input

  if not command_processed_this_turn:
    needs_llm_call = True
    _add_profile_action(state, f"Said to NPC: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
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

      # This logic to avoid double printing NPC name seems correct
      if not (is_in_lyra_hint_mode and command_processed_this_turn and command == 'hint' and prompt_for_llm != user_input):
        print(f"\n{TF.BOLD}{npc_color}{npc_name_for_prompt} > {TF.RESET}")

      try:
        _response_text, stats = chat_session.ask(
          prompt_for_llm,
          current_npc.get('name', 'NPC'),
          state.get('use_stream', True),
          True
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
        if debug_mode:
          traceback.print_exc()
    elif user_input:
      print(f"{TF.YELLOW}You're not talking to anyone. Use /go to move to an area, then /talk <npc_name>.{TF.RESET}")
      _add_profile_action(state, f"Attempted to talk while not in conversation: '{user_input[:50]}'")

  return state