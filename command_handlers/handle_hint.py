import time
from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action, hint_manager # Uses the (potentially fallback) hint_manager

def handle_hint(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    player_id = state['player_id']
    db = state['db']
    ChatSession_class = state['ChatSession'] # Get ChatSession class from state
    llm_wrapper_func = state.get('llm_wrapper_func') # Get LLM wrapper from state
    debug_mode = state.get('debug_mode', False)
    _add_profile_action(state, "Used /hint command")

    if not llm_wrapper_func:
        print(f"{TF.RED}LLM wrapper function not available in game state. Advanced hint cannot proceed.{TF.RESET}")
        # Fallback to simple hint if LLM is not available for advanced mode
        if state.get('chat_session') and state.get('current_npc') and not state.get('in_lyra_hint_mode'):
            simple_hint = state['chat_session'].get_player_hint()
            if simple_hint:
                print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Hint ({state['current_npc'].get('name', 'your current interaction')}):{TF.RESET}\n {TF.CYAN}➢ {simple_hint}{TF.RESET}")
            else:
                print(f"{TF.YELLOW}No specific hint for {state['current_npc'].get('name', 'this interaction')} right now.{TF.RESET}")
        else:
            print(f"{TF.YELLOW}Not in a regular conversation to get a simple hint, or LLM for advanced hint is unavailable.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    if state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}You are already consulting Lyra. Use /endhint to return.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    # Check if player is in a situation to ask Lyra about

    if not state.get('current_npc') or not state.get('chat_session'):
        print(f"{TF.YELLOW}You need to be in a situation (talking to an NPC) to ask Lyra about.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    # If already talking to Lyra, just provide her normal player hint.

    if state['current_npc'].get('name', '').lower() == "lyra":
        print(f"{TF.YELLOW}You are already talking to Lyra. Ask her directly.{TF.RESET}")
        lyra_player_hint = state['chat_session'].get_player_hint()
        if lyra_player_hint:
            print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Lyra's current general guidance for you:{TF.RESET}\n {TF.CYAN}➢ {lyra_player_hint}{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    # --- Advanced Lyra Consultation Logic ---

    current_cache_key = hint_manager.generate_cache_key(state)
    cached_hint_data = state.get('lyra_hint_cache') # This is specific to advanced Lyra hints
    lyra_npc_data_from_db = db.get_npc("Sanctum of Whispers", "Lyra")
    if not lyra_npc_data_from_db:
        print(f"{TF.RED}Critical Error: Lyra's NPC data not found! Cannot consult.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    player_profile = state.get('player_profile_cache', {}) # Get cached profile

    # Check cache first for advanced Lyra consultation

    if cached_hint_data and cached_hint_data.get('key') == current_cache_key and \
       (time.time() - cached_hint_data.get('timestamp', 0)) < 300: # 5 min cache
        if debug_mode:
            print(f"{TF.DIM}Recalling Lyra's recent guidance for this situation...{TF.RESET}")
        lyra_hint_session_restored = ChatSession_class(model_name=state['model_name'])
        lyra_system_prompt = session_utils.build_system_prompt(
            lyra_npc_data_from_db, state['story'], TF, player_id, db,
            player_profile=player_profile, # Pass profile to Lyra's system prompt build
            llm_wrapper_func=llm_wrapper_func, llm_model_name=state['model_name']
        )
        lyra_hint_session_restored.set_system_prompt(lyra_system_prompt)
        for msg in cached_hint_data.get('lyra_chat_history', []):
            if msg.get("role") != "system": # Don't re-add system prompt
                lyra_hint_session_restored.add_message(msg['role'], msg['content'])

        if lyra_hint_session_restored.messages and lyra_hint_session_restored.messages[-1]['role'] == 'assistant':
            lyra_color = session_utils.get_npc_color("Lyra", TF)
            print(f"\n{TF.BOLD}{lyra_color}{lyra_npc_data_from_db.get('name', 'Lyra')} (recalled) > {TF.RESET}")
            print(TF.format_terminal_text(lyra_hint_session_restored.messages[-1]['content']))
        else: # Should not happen if cache is valid, but safety
            print(f"{TF.YELLOW}Could not recall Lyra's last specific advice for this exact state, preparing fresh consultation.{TF.RESET}")
        # Switch to Lyra hint mode
        state['stashed_chat_session'] = state['chat_session']
        state['stashed_npc'] = state['current_npc']
        state['in_lyra_hint_mode'] = True
        state['current_npc'] = lyra_npc_data_from_db
        state['chat_session'] = lyra_hint_session_restored
        print(f"{TF.DIM}You can ask Lyra a follow-up, or type /endhint to return.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    # No valid cache, or cache expired - consult Lyra fresh

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

    # Prepare player data for Lyra's prompt

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
        conversation_summary_for_lyra=conversation_summary, # Pass summary to Lyra's system prompt
        player_profile=player_profile, # Pass full profile to Lyra's system prompt build
        llm_wrapper_func=llm_wrapper_func, llm_model_name=state['model_name']
    )
    lyra_hint_session_new.set_system_prompt(lyra_system_prompt)

    lyra_color = session_utils.get_npc_color("Lyra", TF)
    print(f"\n{TF.BOLD}{lyra_color}{lyra_npc_data_from_db.get('name', 'Lyra')} > {TF.RESET}")
    try:
        _response_text, stats = lyra_hint_session_new.ask(initial_lyra_user_prompt, "Lyra", state.get('use_stream', True), True)
        if not _response_text.strip() and not (stats and stats.get("error")): # Handle empty but non-error LLM responses
            print(f"{TF.DIM}{TF.ITALIC}Lyra ponders deeply...{TF.RESET}")
        if state.get('auto_show_stats', False) and stats and state.get('format_stats'):
            print(state['format_stats'](stats)) # Corrected call
    except Exception as e:
        print(f"{TF.RED}Error during Lyra consultation: {e}{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True} # Return to main loop

    # Cache the new consultation

    state['lyra_hint_cache'] = {
        'key': current_cache_key,
        'lyra_chat_history': lyra_hint_session_new.get_history(), # Save the full history of this hint session
        'timestamp': time.time()
    }

    # Switch to Lyra hint mode

    state['stashed_chat_session'] = stashed_session_temp
    state['stashed_npc'] = stashed_npc_temp
    state['in_lyra_hint_mode'] = True
    state['current_npc'] = lyra_npc_data_from_db
    state['chat_session'] = lyra_hint_session_new

    print(f"{TF.DIM}You can continue asking Lyra for advice, or type /endhint to return.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}