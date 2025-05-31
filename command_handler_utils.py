from typing import Dict, Any

HandlerResult = Dict[str, Any]
RANDOM_TALK_SYNTAX = '.'

def _add_profile_action(state: Dict[str, Any], action_description: str):
    if 'actions_this_turn_for_profile' not in state:
        state['actions_this_turn_for_profile'] = []
    state['actions_this_turn_for_profile'].append(action_description)

# Centralized fallbacks for hint_manager and player_profile_manager

try:
    import hint_manager as hm
    from player_profile_manager import get_distilled_profile_insights_for_npc as gdpifn

    print("DEBUG (command_handler_utils): Successfully imported REAL hint_manager and player_profile_manager.")

except ImportError:
    print("WARNING (command_handler_utils): hint_manager.py or player_profile_manager.py not found. Advanced /hint or /profile features will not fully function.")
    class hint_manager_fallback:
        @staticmethod
        def generate_cache_key(state): return "fallback_key"
        @staticmethod
        def summarize_conversation_for_lyra(chat_history, llm_wrapper_func, model_name, TF): return "[Summary unavailable]"
        @staticmethod
        def build_initial_lyra_prompt(summary, player_data, player_profile, stashed_npc_data, TF, story_context): return "Lyra, the Seeker needs guidance."
    hm = hint_manager_fallback

    def get_distilled_profile_insights_for_npc_fallback(player_profile, current_npc_data, story_context_summary, llm_wrapper_func, model_name, TF):
        return "[Profile insights unavailable for this NPC]"
    gdpifn = get_distilled_profile_insights_for_npc_fallback

# Export them consistently

hint_manager = hm
get_distilled_profile_insights_for_npc = gdpifn