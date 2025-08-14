import json
import random
import traceback
import re
import hashlib
import time
import threading
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

logger = logging.getLogger(__name__)

# MODIFIED: Explicitly import new/changed handlers
from command_handlers.handle_exit import handle_exit
from command_handlers.handle_help import handle_help
from command_handlers.handle_go import handle_go
from command_handlers.handle_talk import handle_talk
from command_handlers.handle_who import handle_who
from command_handlers.handle_whereami import handle_whereami
from command_handlers.handle_npcs import handle_npcs
from command_handlers.handle_areas import handle_areas
from command_handlers.handle_describe import handle_describe
from command_handlers.handle_listareas import handle_listareas
from command_handlers.handle_stats import handle_stats
from command_handlers.handle_session_stats import handle_session_stats
from command_handlers.handle_all_stats import handle_all_stats
from command_handlers.handle_clear import handle_clear
from command_handlers.handle_hint import handle_hint # MODIFIED
from command_handlers.handle_endhint import handle_endhint # MODIFIED
from command_handlers.handle_inventory import handle_inventory
from command_handlers.handle_give import handle_give
from command_handlers.handle_receive import handle_receive
from command_handlers.handle_profile import handle_profile
from command_handlers.heandle_profile_for_npc import handle_profile_for_npc
from command_handlers.handle_history import handle_history
from command_handlers.handle_sussurri import handle_sussurri

import session_utils # Keep for other utilities like get_npc_color
from command_handler_utils import HandlerResult, _add_profile_action, hint_manager, get_distilled_profile_insights_for_npc
from consequence_system import show_philosophical_consequences, track_relationship_changes

try:
  from command_interpreter import interpret_user_intent
except ImportError:
  print("Warning: command_interpreter.py not found. Natural language command interpretation disabled.")
  def interpret_user_intent(user_input, game_state, llm_wrapper_func, model_name, confidence_threshold=0.7):
    return {'is_command': False, 'confidence': 0.0, 'original_input': user_input, 'reasoning': 'Fallback: interpreter missing'}

def _speculative_nlp_interpretation(user_input: str, state: Dict[str, Any], result_container: Dict[str, Any]):
  """Run NLP interpretation in background thread, storing result in container."""
  try:
    llm_wrapper_func = state.get('llm_wrapper_func')
    nlp_model_name = state.get('nlp_command_model_name') or \
                     state.get('profile_analysis_model_name') or \
                     state.get('model_name')
    nlp_confidence_threshold = state.get('nlp_command_confidence_threshold', 0.7)
    
    if llm_wrapper_func and nlp_model_name:
      logger.info(f"[NLP-SPECULATIVE] Starting interpretation for: '{user_input[:30]}...'")
      start_time = time.time()
      
      # Use cached NPCs if available from game system
      state_copy = state.copy()
      game_system_instance = state.get('game_system_instance')
      if game_system_instance and hasattr(game_system_instance, '_get_cached_areas_list'):
        try:
          state_copy['available_areas'] = game_system_instance._get_cached_areas_list()
        except Exception as e:
          logger.warning(f"[NLP-SPECULATIVE] Cache access failed, using fallback: {e}")
          # Fallback to original method
          db = state.get('db')
          if db:
            all_known_npcs = session_utils.refresh_known_npcs_list(db, state.get('TerminalFormatter'))
            available_areas = session_utils.get_known_areas_from_list(all_known_npcs)
            state_copy['available_areas'] = available_areas
      else:
        db = state.get('db')
        if db:
          all_known_npcs = session_utils.refresh_known_npcs_list(db, state.get('TerminalFormatter'))
          available_areas = session_utils.get_known_areas_from_list(all_known_npcs)
          state_copy['available_areas'] = available_areas
      
      intent_result = interpret_user_intent(
        user_input, state_copy, llm_wrapper_func, nlp_model_name, nlp_confidence_threshold
      )
      
      elapsed_ms = int((time.time() - start_time) * 1000)
      logger.info(f"[NLP-SPECULATIVE] Completed in {elapsed_ms}ms: is_command={intent_result['is_command']}, confidence={intent_result['confidence']:.2f}")
      
      result_container['intent_result'] = intent_result
      result_container['completed'] = True
    else:
      result_container['intent_result'] = {'is_command': False, 'confidence': 0.0, 'original_input': user_input}
      result_container['completed'] = True
      
  except Exception as e:
    logger.error(f"[NLP-SPECULATIVE] Error: {str(e)}")
    result_container['intent_result'] = {'is_command': False, 'confidence': 0.0, 'original_input': user_input, 'error': str(e)}
    result_container['completed'] = True

def _speculative_dialogue_generation(user_input: str, state: Dict[str, Any], result_container: Dict[str, Any]):
  """Run dialogue generation in background thread for simple chat messages."""
  try:
    current_npc = state.get('current_npc')
    chat_session = state.get('chat_session')
    
    if not current_npc or not chat_session:
      result_container['dialogue_result'] = None
      result_container['completed'] = True
      return
    
    logger.info(f"[DIALOGUE-SPECULATIVE] Starting dialogue generation for: '{user_input[:30]}...'")
    start_time = time.time()
    
    # Create a temporary copy of chat session to avoid side effects
    import copy
    temp_session = copy.deepcopy(chat_session)
    
    # Generate NPC response using temporary session
    npc_name_for_prompt = current_npc.get('name', 'NPC')
    temp_session.add_message("user", user_input)
    
    response_text, response_stats = temp_session.ask(
      prompt=user_input,
      current_npc_name_for_placeholder=npc_name_for_prompt,
      stream=state.get('use_stream', False),
      collect_stats=True,
      npc_data=current_npc
    )
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"[DIALOGUE-SPECULATIVE] Completed in {elapsed_ms}ms for NPC: {npc_name_for_prompt}")
    
    result_container['dialogue_result'] = {
      'response_text': response_text,
      'response_stats': response_stats,
      'npc_name': npc_name_for_prompt,
      'temp_session': temp_session  # Include the session with the conversation
    }
    result_container['completed'] = True
    
  except Exception as e:
    elapsed_ms = int((time.time() - time.time()) * 1000)  # Will be 0 but keeps format
    logger.error(f"[DIALOGUE-SPECULATIVE] Error: {str(e)}")
    result_container['dialogue_result'] = None
    result_container['completed'] = True

def _build_dialogue_response(state: Dict[str, Any], dialogue_data: Dict[str, Any]) -> Dict[str, Any]:
  """Build a properly formatted response from speculative dialogue generation."""
  TF = state.get('TerminalFormatter')
  response_text = dialogue_data['response_text']
  npc_name = dialogue_data['npc_name']
  temp_session = dialogue_data.get('temp_session')
  
  # Format and display the response
  if response_text:
    npc_color = session_utils.get_npc_color(npc_name, TF)
    print(f"{npc_color}{npc_name} > {TF.RESET}{response_text}")
    
    # Replace the current chat session with the completed one
    if temp_session and state.get('chat_session'):
      state['chat_session'] = temp_session
  
  return state

command_handlers_map: Dict[str, Callable] = {
  'exit': handle_exit, 'quit': handle_exit,
  'help': handle_help,
  'go': handle_go,
  'talk': handle_talk,
  'who': handle_who,
  'whereami': handle_whereami,
  'npcs': handle_npcs,
  'areas': handle_areas,
  'describe': handle_describe,
  'listareas': handle_listareas,
  'stats': handle_stats,
  'session_stats': handle_session_stats,
  'all_stats': handle_all_stats,
  'clear': handle_clear,
  'hint': handle_hint,           # MODIFIED
  'endhint': handle_endhint,     # MODIFIED
  'inventory': handle_inventory, 'inv': handle_inventory,
  'give': handle_give,
  'receive': handle_receive,
  'profile': handle_profile,
  'profile_for_npc': handle_profile_for_npc,
  'history': handle_history,
  'sussurri': handle_sussurri,
}

def process_input_revised(user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
  state['npc_made_new_response_this_turn'] = False
  if not user_input.strip():
    return state

  TF = state.get('TerminalFormatter')
  chat_session = state.get('chat_session')
  current_npc = state.get('current_npc')
  fmt_stats_func = state.get('format_stats')
  is_in_hint_mode = state.get('in_hint_mode', False) # MODIFIED: Generic hint mode
  debug_mode = state.get('debug_mode', False)
  command_processed_this_turn = False

  # Start speculative processing for non-slash inputs immediately
  nlp_thread = None
  dialogue_thread = None
  nlp_result_container = {'completed': False, 'intent_result': None}
  dialogue_result_container = {'completed': False, 'dialogue_result': None}
  
  if not user_input.startswith('/'):
    nlp_enabled = state.get('nlp_command_interpretation_enabled', True)
    current_npc = state.get('current_npc')
    chat_session = state.get('chat_session')
    
    if nlp_enabled:
      # Always start NLP interpretation
      nlp_thread = threading.Thread(
        target=_speculative_nlp_interpretation,
        args=(user_input, state, nlp_result_container),
        daemon=True
      )
      nlp_thread.start()
      
      # For simple conversations, also start dialogue generation speculatively
      if current_npc and chat_session and not state.get('in_hint_mode', False):
        dialogue_thread = threading.Thread(
          target=_speculative_dialogue_generation,
          args=(user_input, state, dialogue_result_container),
          daemon=True
        )
        dialogue_thread.start()
        logger.info(f"[PARALLEL-PROCESSING] Started both NLP and dialogue threads")

  if user_input.startswith('/'):
    parts = user_input[1:].split(None, 1)
    command = parts[0].lower() if parts else ""
    args_str = parts[1] if len(parts) > 1 else ""
    try:
      if command in command_handlers_map:
        handler_func = command_handlers_map[command]
        # Pass args_str only to handlers that expect it
        if command in ['go', 'talk', 'give', 'receive', 'describe', 'profile', 'sussurri']:
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

  # Smart parallel processing results handling
  elif nlp_thread:
    # Wait a short time to see if NLP completes quickly
    nlp_thread.join(timeout=0.3)  # Quick check - 300ms
    
    if nlp_result_container['completed']:
      intent_result = nlp_result_container['intent_result']
      nlp_confidence_threshold = state.get('nlp_command_confidence_threshold', 0.7)
      
      if state.get('nlp_command_debug', False) or debug_mode:
        reasoning = intent_result.get('reasoning', 'N/A')
        print(f"{TF.DIM}[NLP-PARALLEL] Intent: {intent_result['is_command']}, Conf: {intent_result['confidence']:.2f}, Cmd: {intent_result.get('inferred_command')}, Reason: {reasoning}{TF.RESET}")

      # High confidence command - cancel dialogue and execute command
      if intent_result['is_command'] and intent_result['confidence'] >= nlp_confidence_threshold:
        if dialogue_thread and dialogue_thread.is_alive():
          logger.info(f"[PARALLEL-PROCESSING] NLP detected command, dialogue thread will be ignored")
        
        inferred_command_full = intent_result.get('inferred_command')
        if inferred_command_full:
          print(f"{TF.DIM}[Interpreted as: {inferred_command_full}]{TF.RESET}")
          _add_profile_action(state, f"Used natural language: '{user_input}' → '{inferred_command_full}'")
          return process_input_revised(inferred_command_full, state)
      
      # Low confidence - proceed with dialogue (use speculative result if available)
      elif dialogue_thread:
        dialogue_thread.join(timeout=1.5)  # Wait for dialogue to complete
        
        if dialogue_result_container['completed'] and dialogue_result_container['dialogue_result']:
          # Use the pre-generated dialogue response!
          dialogue_data = dialogue_result_container['dialogue_result']
          logger.info(f"[PARALLEL-PROCESSING] Using speculative dialogue result")
          
          state['npc_made_new_response_this_turn'] = True
          _add_profile_action(state, f"Said to NPC: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
          
          # Return early with the pre-generated response
          return _build_dialogue_response(state, dialogue_data)
        else:
          logger.info(f"[PARALLEL-PROCESSING] Dialogue not ready, falling back to normal processing")
    else:
      # NLP didn't complete quickly - wait longer or timeout
      nlp_thread.join(timeout=1.0)
      if debug_mode and not nlp_result_container['completed']:
        print(f"{TF.YELLOW}[NLP-PARALLEL] Timeout, proceeding as dialogue{TF.RESET}")
    
    # If we reach here, proceed with normal dialogue processing

  # LLM call for dialogue or forced NPC reaction
  force_npc_turn_after_command = state.get('force_npc_turn_after_command', False)
  if force_npc_turn_after_command:
    state.pop('force_npc_turn_after_command', None) # Consume flag

  needs_llm_call = False
  prompt_for_llm = user_input # Default to user's text input

  if not command_processed_this_turn: # Was dialogue
    needs_llm_call = True
    _add_profile_action(state, f"Said to NPC: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
  elif force_npc_turn_after_command and not is_in_hint_mode: # Command that needs NPC reaction
    prompt_for_llm = "[NPC reacts to player's action]"
    needs_llm_call = True

  if is_in_hint_mode and not command_processed_this_turn: # Dialogue during hint mode
    needs_llm_call = True

  if needs_llm_call:
    if current_npc and chat_session:
      npc_name_for_prompt = current_npc.get('name', 'NPC')
      npc_color = session_utils.get_npc_color(current_npc.get('name', 'NPC'), TF)

      if is_in_hint_mode: # MODIFIED: Adjust name and color for hint mode
        guide_name = state.get('wise_guide_npc_name', 'Guide')
        npc_name_for_prompt = f"{guide_name} (Consultation)"
        npc_color = session_utils.get_npc_color(guide_name, TF)


      # Avoid printing NPC prompt if it was an NLP-interpreted command that then resulted in an NPC reaction
      # This is tricky because of the recursive call. The `command_processed_this_turn` helps.
      # If it's a direct dialogue or a hint mode dialogue, print the prompt.
      # If it's an NPC reaction to a command, the prompt is already printed (or was a system action).
      if not command_processed_this_turn or (is_in_hint_mode and not command_processed_this_turn):
          print(f"\n{TF.BOLD}{npc_color}{npc_name_for_prompt} > {TF.RESET}")

      try:
        _response_text, stats = chat_session.ask(
          prompt_for_llm,
          current_npc.get('name', 'NPC'), # Original NPC name for placeholder logic in ask()
          state.get('use_stream', True),
          True, # collect_stats
          current_npc # Pass NPC data for SL command generation
        )
        if not _response_text.strip() and not (stats and stats.get("error")):
          placeholder_msg = f"{TF.DIM}{TF.ITALIC}*{npc_name_for_prompt} seems to ponder for a moment...*{TF.RESET}"
          if is_in_hint_mode: # MODIFIED
            placeholder_msg = f"{TF.DIM}{TF.ITALIC}*{state.get('wise_guide_npc_name', 'Guide')} ponders deeply...*{TF.RESET}"
          print(placeholder_msg)

        state['npc_made_new_response_this_turn'] = True
        if _response_text.strip():
          _add_profile_action(state, f"NPC Response from {npc_name_for_prompt}: '{_response_text[:50]}{'...' if len(_response_text) > 50 else ''}'")
          
        # Show philosophical consequences for the interaction
        if not is_in_hint_mode and user_input:
            show_philosophical_consequences(state, npc_name_for_prompt, user_input)
            track_relationship_changes(state, npc_name_for_prompt, _response_text)

        if state.get('auto_show_stats', False) and stats and fmt_stats_func:
          print(fmt_stats_func(stats))

        # MODIFIED: Cache hint if in hint mode
        if is_in_hint_mode and state.get('hint_cache') is not None: # hint_cache is now a dict
            current_guide_name = state.get('wise_guide_npc_name')
            if current_guide_name: # Only update cache if we know who the guide is
                # The cache key might need to be more specific if hints are multi-turn
                # For now, just store the latest history under a generic key for the guide
                state['hint_cache'][f"{current_guide_name}_chat_history"] = chat_session.get_history()
                state['hint_cache'][f"{current_guide_name}_timestamp"] = time.time()

      except Exception as e:
        state['npc_made_new_response_this_turn'] = False
        print(f"{TF.RED}LLM Chat Error with {npc_name_for_prompt}: {type(e).__name__} - {e}{TF.RESET}")
        if debug_mode:
          traceback.print_exc()

    elif user_input: # User typed something but not in a conversation
      print(f"{TF.YELLOW}You're not talking to anyone. Use /go to move to an area, then /talk <npc_name>.{TF.RESET}")
      _add_profile_action(state, f"Attempted to talk while not in conversation: '{user_input[:50]}'")

  return state