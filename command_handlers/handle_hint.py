# command_handlers/handle_hint.py
import time
from typing import Dict, Any, Optional, Callable

try:
    from session_utils import save_current_conversation, start_conversation_with_specific_npc, get_npc_color
    from hint_manager import (
        generate_cache_key,
        # summarize_conversation_for_lyra, # Original, will use renamed
        # build_initial_lyra_prompt,     # Original, will use renamed
        get_cached_hint,
        cache_hint,
        # format_lyra_response             # Original, will use renamed
    )
    # Use the actual renamed/refactored functions
    from hint_manager import build_initial_guide_prompt # Directly use the refactored name
    from hint_manager import summarize_conversation_for_guide # Directly use the refactored name
    from hint_manager import format_guide_response # Directly use the refactored name

except ImportError:
    # Basic fallbacks if full modules are not available during isolated testing
    print("WARNING (handle_hint): Failed to import session_utils or hint_manager components. Using fallbacks.")
    def save_current_conversation(db, player_id, npc, session, TF, game_state): pass
    # Update fallback signature for start_conversation_with_specific_npc
    def start_conversation_with_specific_npc(db, player_id, area, npc_name, model, story, ChatSession, TF, game_state, conversation_summary_for_guide_context=None, llm_wrapper_for_profile_distillation=None): return None, None
    def get_npc_color(npc_name, TF): return ""
    def generate_cache_key(state): return "fallback_key"
    def summarize_conversation_for_guide(history, llm, model, TF): return "No summary available (fallback)."
    # Update fallback signature for build_initial_guide_prompt
    def build_initial_guide_prompt(guide_name, summary_of_last_interaction, p_data, p_profile, stashed_npc_data, TF, story_ctx, game_session_state): return "Guide, I need your help (fallback)."
    def get_cached_hint(key, state): return None
    def cache_hint(key, hint, state): pass
    def format_guide_response(response, TF): return response


def handle_hint(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handles the /hint command to consult the wise guide."""
    TF = state['TerminalFormatter']
    player_id = state['player_id']
    db = state['db']

    wise_guide_npc_name = state.get('wise_guide_npc_name')
    if not wise_guide_npc_name:
        print(f"{TF.YELLOW}No wise guide has been identified for this story. Cannot provide a hint.{TF.RESET}")
        return state

    if state.get('in_hint_mode', False):
        print(f"{TF.YELLOW}You are already consulting {wise_guide_npc_name}. Ask your question or use /endhint.{TF.RESET}")
        return state

    print(f"\n{TF.DIM}Seeking guidance from {wise_guide_npc_name}...{TF.RESET}")

    # Stash current NPC and session if any
    if state.get('current_npc') and state.get('chat_session'):
        save_current_conversation(db, player_id, state['current_npc'], state['chat_session'], TF, state)
        state['stashed_npc'] = state['current_npc']
        state['stashed_chat_session'] = state['chat_session']
        print(f"{TF.DIM}Your conversation with {state['current_npc'].get('name', 'NPC')} has been paused.{TF.RESET}")

    state['current_npc'] = None
    state['chat_session'] = None
    state['in_hint_mode'] = True

    wise_guide_data = None
    all_npcs = db.list_npcs_by_area()
    for npc_info in all_npcs:
        if npc_info.get('name') == wise_guide_npc_name:
            wise_guide_data = db.get_npc(npc_info.get('area'), wise_guide_npc_name)
            break

    if not wise_guide_data or not wise_guide_data.get('area'):
        print(f"{TF.RED}Error: Could not find data or area for wise guide '{wise_guide_npc_name}'. Aborting hint.{TF.RESET}")
        if state.get('stashed_npc') and state.get('stashed_chat_session'):
            state['current_npc'] = state.pop('stashed_npc')
            state['chat_session'] = state.pop('stashed_chat_session')
        state['in_hint_mode'] = False
        return state

    wise_guide_area = wise_guide_data.get('area')

    # Prepare conversation summary for the guide's system prompt context
    conversation_summary_for_sys_prompt = "No recent conversation to summarize for guide's context."
    if state.get('stashed_chat_session') and state['stashed_chat_session'].messages:
        conversation_summary_for_sys_prompt = summarize_conversation_for_guide(
            state['stashed_chat_session'].messages,
            state['llm_wrapper_func'],
            state.get('profile_analysis_model_name') or state['model_name'], # Use analysis or default model for summary
            TF
        )

    # --- CORRECTED CALL to start_conversation_with_specific_npc ---
    guide_npc_obj, guide_session = start_conversation_with_specific_npc(
        db,                                         # 1. db
        player_id,                                  # 2. player_id
        wise_guide_area,                            # 3. area_name
        wise_guide_npc_name,                        # 4. npc_name
        state['model_name'],                        # 5. model_name (for the guide's dialogue)
        state['story'],                             # 6. story
        state['ChatSession'],                       # 7. ChatSession_class
        TF,                                         # 8. TF_class
        state,                                      # 9. game_session_state (passed positionally)
        conversation_summary_for_guide_context=conversation_summary_for_sys_prompt, # 10. (keyword ok for optional)
        llm_wrapper_for_profile_distillation=state['llm_wrapper_func'] # 11. (keyword ok for optional)
    )

    if not guide_npc_obj or not guide_session:
        print(f"{TF.RED}Error starting consultation with {wise_guide_npc_name}.{TF.RESET}")
        state['in_hint_mode'] = False
        if state.get('stashed_npc') and state.get('stashed_chat_session'):
            state['current_npc'] = state.pop('stashed_npc')
            state['chat_session'] = state.pop('stashed_chat_session')
        return state

    state['current_npc'] = guide_npc_obj
    state['chat_session'] = guide_session

    cache_key = generate_cache_key(state) # Key for caching the guide's response

    # Player data for building the actual first "question" to the guide
    player_data_for_prompt = {
        'player_id': player_id,
        'current_area': state.get('stashed_npc', {}).get('area') if state.get('stashed_npc') else state.get('current_area', 'Unknown'),
        'inventory': state.get('player_inventory', []),
        'credits': state.get('player_credits_cache', 0),
        'plot_flags': db.load_player_state(player_id).get('plot_flags', {}) # Fresh plot flags
    }

    # This is the first "user" message sent to the guide during the hint session
    initial_hint_prompt_to_guide = build_initial_guide_prompt(
        guide_npc_name=wise_guide_npc_name,
        summary_of_last_interaction=conversation_summary_for_sys_prompt, # Use the same summary
        player_data=player_data_for_prompt,
        player_profile=state['player_profile_cache'],
        stashed_npc_data=state.get('stashed_npc'),
        TF=TF,
        story_context=state['story'],
        game_session_state=state
    )

    guide_color = get_npc_color(wise_guide_npc_name, TF)
    print(f"\n{TF.BOLD}{guide_color}{wise_guide_npc_name} > {TF.RESET}") # Prompt for the guide's response

    response_text, stats = guide_session.ask(
        initial_hint_prompt_to_guide,
        wise_guide_npc_name,
        state['use_stream'],
        True # collect_stats
    )
    state['npc_made_new_response_this_turn'] = True

    if not response_text.strip() and not (stats and stats.get("error")):
        print(f"{TF.DIM}{TF.ITALIC}*{wise_guide_npc_name} ponders deeply...*{TF.RESET}")

    if response_text.strip(): # Only cache if there's actual text
        cache_hint(cache_key, response_text, state)

    if state.get('auto_show_stats', False) and stats:
        print(state['format_stats'](stats))

    return state