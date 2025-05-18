# Path: hint_manager.py (NEW FILE)

import hashlib
import time
from typing import Dict, List, Any, Optional, Callable

# Assuming these are available in the global scope or via state later
# from llm_wrapper import llm_wrapper
# from terminal_formatter import TerminalFormatter
# import session_utils # For build_system_prompt if needed directly here

def generate_cache_key(state: Dict[str, Any]) -> str:
    """
    Generates a cache key based on the current game state relevant to Lyra's advice.
    """
    player_id = state.get('player_id', 'unknown_player')
    current_stashed_npc = state.get('stashed_npc', state.get('current_npc')) # Use stashed if in hint mode, else current

    npc_code = "None"
    if current_stashed_npc:
        npc_code = current_stashed_npc.get('code', 'UnknownNPC')

    # Consider last few messages of the *stashed/current* NPC's conversation
    # If we are about to enter hint mode, 'chat_session' is still the original NPC's session.
    # If we are already in hint mode and checking cache for a follow-up, 'stashed_chat_session' is the one.
    relevant_chat_session = state.get('stashed_chat_session', state.get('chat_session'))
    last_messages_hash = "no_active_chat"
    if relevant_chat_session and relevant_chat_session.messages:
        # Hash content of last 2 messages (user and assistant if available)
        history_for_hash = "".join([m['content'] for m in relevant_chat_session.messages[-2:]])
        last_messages_hash = hashlib.md5(history_for_hash.encode('utf-8')).hexdigest()

    # Key plot flags (example, make this more specific to your game's important flags)
    player_state_data = state.get('db').load_player_state(player_id) or {}
    plot_flags = player_state_data.get('plot_flags', {})
    critical_flags_parts = []
    # Example: Add flags that Lyra cares about for her current quest phase
    # This needs to be tailored to your game's logic.
    if 'veil_status' in plot_flags:
        critical_flags_parts.append(f"veil:{plot_flags['veil_status']}")
    if 'seals_found_count' in plot_flags:
        critical_flags_parts.append(f"seals:{plot_flags['seals_found_count']}")

    # Key inventory items (example)
    inventory = state.get('player_inventory', [])
    key_items_str = ""
    # Example: Check for items Lyra tracks for her quest
    # This also needs to be tailored.
    # key_quest_items = ["Heartseed of the Ancient Grove", "Frammento del Sigillo dello Spirito"]
    # found_key_items = [item for item in key_quest_items if state.get('db')._clean_item_name(item) in inventory]
    # if found_key_items:
    #    key_items_str = "keyitems:" + ",".join(sorted(found_key_items))
    # For simplicity now, hash a small representation of inventory
    inventory_sample_hash = hashlib.md5(",".join(sorted(inventory[:5])).encode('utf-8')).hexdigest()


    critical_flags_str = ";".join(sorted(critical_flags_parts))

    # Combine all parts into a single string for hashing
    # Adding player_id ensures cache is per-player.
    key_string = f"{player_id}:{npc_code}:{last_messages_hash}:{critical_flags_str}:{inventory_sample_hash}"

    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def summarize_conversation_for_lyra(
    chat_history: List[Dict[str, str]],
    llm_wrapper_func: Callable,
    model_name: Optional[str],
    TF # TerminalFormatter class/instance
    ) -> str:
    """
    Uses an LLM to summarize the provided chat history for Lyra.
    """
    if not llm_wrapper_func:
        return "[Summarization LLM not available]"
    if not chat_history:
        return "[No conversation to summarize]"

    # Filter out system messages from the history to be summarized, if any are present.
    # However, chat_history from chat_session.get_history() should already be filtered or structured.
    user_assistant_history = [msg for msg in chat_history if msg.get("role") in ["user", "assistant"]]
    if not user_assistant_history:
        return "[Conversation has no user/assistant messages to summarize]"

    # Construct the messages payload for the summarizer LLM
    summarizer_system_prompt = (
        "You are an expert summarizer. Given the following dialogue between a player (Seeker) "
        "and an NPC, provide a concise summary (max 3-4 sentences). Highlight the NPC's apparent goals or needs, "
        "what the Seeker was trying to achieve or ask, any key items, locations, or names mentioned, "
        "and any unresolved questions or conflicts. Focus on information that a wise sage mentor (Lyra) "
        "would find most relevant for guiding the Seeker."
    )

    # Present the history as a single block of text for the summarizer's "user" prompt
    dialogue_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in user_assistant_history])

    summarizer_messages = [
        {"role": "system", "content": summarizer_system_prompt},
        {"role": "user", "content": f"Please summarize this dialogue:\n\n{dialogue_text}"}
    ]

    try:
        summary_text, stats = llm_wrapper_func(
            messages=summarizer_messages,
            model_name=model_name, # Or a specific, fast model for summarization
            stream=False, # Summaries are usually short, no need to stream
            collect_stats=False # Stats for summarization might not be critical for player
        )
        if stats and stats.get("error"):
            return f"[Error during summarization: {stats.get('error')}]"
        return summary_text.strip() if summary_text else "[Summary was empty]"
    except Exception as e:
        print(f"{TF.RED}Exception during summarization call: {e}{TF.RESET}")
        return f"[Exception during summarization: {type(e).__name__}]"


def build_initial_lyra_prompt(
    conversation_summary: str,
    player_data: Dict[str, Any], # Contains inventory, credits, plot_flags, current_area (of stashed NPC)
    stashed_npc_data: Dict[str, Any], # Profile of the NPC the player was talking to
    TF, # TerminalFormatter
    story_context: str # Global story context
    ) -> str:
    """
    Constructs the detailed initial "user" prompt to send to Lyra for guidance.
    """

    stashed_npc_name = stashed_npc_data.get('name', 'an unknown individual')
    stashed_npc_role = stashed_npc_data.get('role', 'of unknown role')
    stashed_npc_area = player_data.get('current_area', stashed_npc_data.get('area', 'an unknown area'))
    stashed_npc_motivation = stashed_npc_data.get('motivation', 'Their motivations are unclear.')
    stashed_npc_goal = stashed_npc_data.get('goal', 'Their goals are unknown.')

    inventory_str = ", ".join(player_data.get('inventory', [])) or "nothing"
    credits_str = str(player_data.get('credits', 0))

    plot_flags_list = []
    for flag, value in player_data.get('plot_flags', {}).items():
        plot_flags_list.append(f"- {flag.replace('_', ' ').capitalize()}: {value}")
    plot_flags_str = "\n".join(plot_flags_list) if plot_flags_list else "No specific plot progress noted."

    prompt = f"""Lyra, my wise guide, the Seeker requires your counsel. They were just in {TF.BOLD}{stashed_npc_area}{TF.RESET}, interacting with {TF.BOLD}{stashed_npc_name}{TF.RESET} ({TF.ITALIC}{stashed_npc_role}{TF.RESET}).
This individual's motivations seem to be: "{stashed_npc_motivation}"
Their apparent goal is: "{stashed_npc_goal}"

{TF.DIM}--- Summary of their recent interaction ---{TF.RESET}
{conversation_summary}
{TF.DIM}--- End of Summary ---{TF.RESET}

{TF.DIM}--- Seeker's Current Status ---{TF.RESET}
{TF.BOLD}Area of last interaction:{TF.RESET} {stashed_npc_area}
{TF.BOLD}Inventory:{TF.RESET} {inventory_str}
{TF.BOLD}Credits:{TF.RESET} {credits_str}
{TF.BOLD}Known Plot Progress:{TF.RESET}
{plot_flags_str}

{TF.DIM}--- World Context ---{TF.RESET}
{story_context}
{TF.DIM}--- End World Context ---{TF.RESET}

{TF.BOLD}Considering all of this, Lyra, what insights, warnings, or guidance can you offer the Seeker? {TF.RESET}
What might be their next best step, something crucial they might be overlooking, or how should they approach the situation with {stashed_npc_name}?
Your advice should help them in their overall quest to mend the Veil and restore the Seals. Be thoughtful and perceptive.
"""
    return prompt.strip()

if __name__ == "__main__":
    class MockTF: BOLD=""; RESET=""; ITALIC=""; DIM="" # Basic mock for testing
    class MockLLMWrapper:
        def __call__(self, messages, model_name, stream, collect_stats):
            if "summarize this dialogue" in messages[-1]['content']:
                return "This is a test summary: NPC wants X, Player asked Y.", {"error": None}
            return "Lyra says: Consider the ancient prophecy.", {"error": None}

    mock_llm_wrapper = MockLLMWrapper()

    print("--- Testing Hint Manager ---")

    sample_chat_history = [
        {"role": "user", "content": "Hello Syra, what is this place?"},
        {"role": "assistant", "content": "These are the Ancient Ruins, seeker. They remember much."},
        {"role": "user", "content": "I need a fragment for Lyra."}
    ]
    summary = summarize_conversation_for_lyra(sample_chat_history, mock_llm_wrapper, "test-model", MockTF)
    print(f"Generated Summary: {summary}")
    assert "Test summary" in summary

    player_data_sample = {
        'inventory': ['Glowing Stone', 'Old Map'],
        'credits': 150,
        'plot_flags': {'ruins_visited': True, 'syra_met': True},
        'current_area': 'Ancient Ruins'
    }
    stashed_npc_data_sample = {
        'name': 'Syra',
        'role': 'Spirit Guardian',
        'area': 'Ancient Ruins',
        'motivation': 'Protect the ruins.',
        'goal': 'Guide a worthy soul.'
    }
    story_sample = "The Veil is shattering. Seals must be restored."

    lyra_prompt = build_initial_lyra_prompt(summary, player_data_sample, stashed_npc_data_sample, MockTF, story_sample)
    print(f"\nInitial Lyra Prompt:\n{lyra_prompt}")
    assert "Syra" in lyra_prompt
    assert "Glowing Stone" in lyra_prompt
    assert "ruins_visited: True" in lyra_prompt
    assert "Veil is shattering" in lyra_prompt

    # Mock state for cache key
    mock_state_for_cache = {
        'player_id': 'PlayerTest',
        'current_npc': stashed_npc_data_sample,
        'chat_session': type('Chat', (), {'messages': sample_chat_history})(), # Mock session
        'db': type('DB', (), {'load_player_state': lambda pid: player_data_sample, '_clean_item_name': lambda x: x.lower()})(), # Mock DB
        'player_inventory': player_data_sample['inventory']
    }
    key1 = generate_cache_key(mock_state_for_cache)
    print(f"\nCache Key 1: {key1}")

    # Change something minor
    mock_state_for_cache['chat_session'].messages.append({"role": "assistant", "content": "The fragment is hidden well."})
    key2 = generate_cache_key(mock_state_for_cache)
    print(f"Cache Key 2 (after msg add): {key2}")
    assert key1 != key2

    print("\nHint Manager tests seem okay.")
