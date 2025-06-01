import hashlib
import time
from typing import Dict, List, Any, Optional, Callable

# Note: llm_wrapper and TerminalFormatter are assumed to be importable from the project root.
# If they are in a subdirectory, adjust the import path.
try:
    from llm_wrapper import llm_wrapper
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("WARNING (hint_manager): llm_wrapper or terminal_formatter not found. Using basic fallbacks.")
    def llm_wrapper(messages, model_name, stream, collect_stats, **kwargs):
        return "Fallback LLM response (hint_manager)", {"error": "llm_wrapper missing"}
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; ITALIC = "";
        BRIGHT_CYAN = ""
        @staticmethod
        def format_terminal_text(text, width=80): return text


def generate_cache_key(state: Dict[str, Any]) -> str:
    """
    Generates a cache key based on the current game state relevant to the guide's advice.
    MODIFIED: Considers generic hint_mode and wise_guide_npc_name.
    """
    player_id = state.get('player_id', 'unknown_player')

    # Determine current NPC context (either main NPC or stashed NPC if in hint mode)
    # If in hint mode, the "current NPC" for context is the one player was talking to *before* hint.
    # The wise_guide_npc_name itself is part of the context if in hint mode.
    active_npc_for_context = state.get('current_npc')
    if state.get('in_hint_mode', False) and state.get('stashed_npc'):
        active_npc_for_context = state.get('stashed_npc')

    npc_code = "None"
    if active_npc_for_context:
        npc_code = active_npc_for_context.get('code', 'UnknownNPC')

    # Relevant chat session (main or stashed if in hint mode)
    relevant_chat_session = state.get('chat_session')
    if state.get('in_hint_mode', False) and state.get('stashed_chat_session'):
        relevant_chat_session = state.get('stashed_chat_session')

    last_messages_hash = "no_active_chat"
    if relevant_chat_session and relevant_chat_session.messages:
        # Hash last few messages of the relevant conversation (not the guide's)
        history_for_hash = "".join([m['content'] for m in relevant_chat_session.messages[-3:]]) # More context
        last_messages_hash = hashlib.md5(history_for_hash.encode('utf-8')).hexdigest()

    player_state_data = state.get('db').load_player_state(player_id) or {}
    plot_flags = player_state_data.get('plot_flags', {})
    critical_flags_parts = []
    # Example flags (customize to your game's critical plot points)
    if 'veil_status' in plot_flags: critical_flags_parts.append(f"veil:{plot_flags['veil_status']}")
    if 'seals_collected' in plot_flags: critical_flags_parts.append(f"seals:{plot_flags['seals_collected']}")
    # Add more flags as needed

    critical_flags_str = "_".join(sorted(critical_flags_parts)) if critical_flags_parts else "no_flags"

    # Include wise_guide_npc_name if in hint mode, as the guide might give different advice
    # based on who *they* are, even if player context is same.
    guide_context_part = ""
    if state.get('in_hint_mode', False) and state.get('wise_guide_npc_name'):
        guide_context_part = f"_guide:{state['wise_guide_npc_name']}"

    cache_key_raw = f"{player_id}_{npc_code}_{last_messages_hash}_{critical_flags_str}{guide_context_part}"
    return hashlib.md5(cache_key_raw.encode('utf-8')).hexdigest()


def summarize_conversation_for_guide(chat_history: List[Dict[str, str]],
                                     llm_wrapper_func: Callable,
                                     model_name: str,
                                     TF: type) -> str:
    """
    Summarizes the current conversation between player and NPC for the guide's context.
    MODIFIED: Generic name, was summarize_conversation_for_lyra.
    """
    if not chat_history or len(chat_history) < 2: # Need at least one user and one assistant turn
        return "No significant conversation has taken place yet with the other NPC."

    # Take a bit more history for better summary context
    recent_messages = chat_history[-8:] if len(chat_history) > 8 else chat_history
    conversation_text = ""
    for msg in recent_messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if role == 'user':
            conversation_text += f"Player: {content}\n"
        elif role == 'assistant':
            # Try to get NPC name from a potential system prompt or game state if available
            # For simplicity here, just using "NPC:"
            conversation_text += f"NPC: {content}\n"

    summarization_messages = [
        {
            "role": "system",
            "content": """You are an expert at summarizing RPG conversations for strategic guidance.
            Summarize this player-NPC interaction focusing on:
            - What the player explicitly asked for or was trying to achieve.
            - Key information revealed by the NPC.
            - Any unresolved questions or player goals.
            - Player's expressed emotions or intentions.
            - Items exchanged or quests offered/updated.
            Keep it concise (2-3 sentences) but strategically rich for a wise guide to understand the player's immediate context and needs.
            This summary is for a 'wise guide' NPC who will advise the player."""
        },
        {
            "role": "user",
            "content": f"Please summarize this conversation excerpt:\n\n{conversation_text}"
        }
    ]
    try:
        summary, stats = llm_wrapper_func(
            messages=summarization_messages,
            model_name=model_name, # Or a dedicated summarization model
            stream=False,
            collect_stats=False
        )
        if stats and stats.get("error"):
            print(f"{TF.YELLOW}Warning: LLM error during conversation summary: {stats['error']}{TF.RESET}")
            return f"Summary unavailable due to LLM error. Last exchange: {conversation_text[-250:]}"
        return summary.strip() if summary else "Summary generation failed or returned empty."
    except Exception as e:
        print(f"{TF.YELLOW}Warning: Could not generate conversation summary: {e}{TF.RESET}")
        return f"Recent conversation summary unavailable. Last exchange: {conversation_text[-250:]}"


def build_initial_guide_prompt(guide_npc_name: str,
                               summary_of_last_interaction: str,
                               player_data: Dict[str, Any],
                               player_profile: Dict[str, Any],
                               stashed_npc_data: Optional[Dict[str, Any]], # NPC player was talking to
                               TF: type,
                               story_context: str,
                               game_session_state: Dict[str, Any] # Pass full state for rich context
                               ) -> str:
    """
    Builds the initial prompt for the Wise Guide consultation.
    MODIFIED: Was build_initial_lyra_prompt. Takes guide_npc_name.
    """
    player_id = player_data.get('player_id', 'Seeker')
    guide_label = guide_npc_name or "Wise Guide" # Fallback if name is somehow None

    prompt_parts = [
        f"Salutations, {guide_label}. I am {player_id}, often called the Seeker. I come to you for your wisdom.",
        "",
        f"**My Current Situation & Context:**"
    ]

    if stashed_npc_data:
        stashed_npc_name = stashed_npc_data.get('name', 'an individual')
        stashed_npc_area = stashed_npc_data.get('area', 'their location')
        prompt_parts.append(f"- I was just speaking with {stashed_npc_name} in {stashed_npc_area}.")
        prompt_parts.append(f"- Summary of that last interaction: \"{summary_of_last_interaction}\"")
    else:
        current_area_display = player_data.get('current_area', 'an unknown location')
        prompt_parts.append(f"- I am currently in {current_area_display} and was not in a specific conversation before seeking your counsel.")

    # Player Inventory & Status
    inventory_list = player_data.get('inventory', [])
    credits_amount = player_data.get('credits', 0)
    if inventory_list:
        prompt_parts.append(f"- In my possession, I have: {', '.join(inventory_list[:5])}{' and other items...' if len(inventory_list) > 5 else ''}.")
    prompt_parts.append(f"- I have {credits_amount} Credits.")

    # Player Profile Insights (simplified for the guide)
    prompt_parts.append("\n**A Glimpse Into My Nature (My Profile):**")
    if player_profile:
        core_traits = player_profile.get('core_traits', {})
        if core_traits:
            traits_summary = ", ".join([f"{trait.capitalize()}: {val}" for trait, val in core_traits.items() if val >=6 or val <=4]) # Highlight prominent
            prompt_parts.append(f"- Key Traits: {traits_summary if traits_summary else 'Balanced'}.")
        style = player_profile.get('interaction_style_summary', 'Observant.')
        prompt_parts.append(f"- My typical interaction style: {style}")
        motivations = player_profile.get('inferred_motivations', [])
        if motivations:
            prompt_parts.append(f"- I seem to be driven by: {', '.join(motivations)}.")
    else:
        prompt_parts.append("- My deeper nature is yet to be fully understood.")

    prompt_parts.append(f"\n**The World's Predicament (Story Context):**\n{story_context}")

    prompt_parts.extend([
        "\nGiven all this, wise one:",
        "- What should be my immediate focus or next significant action?",
        "- Are there any particular dangers or opportunities I should be aware of based on my current situation and the items I possess?",
        "- How might my own nature (profile) help or hinder me in what lies ahead?",
        "Please, offer your most pertinent counsel."
    ])
    return "\n".join(prompt_parts)


def get_cached_hint(cache_key: str, state: Dict[str, Any]) -> Optional[str]:
    """
    Retrieves cached hint if available and still valid.
    MODIFIED: Uses generic 'hint_cache'.
    """
    hint_cache_dict = state.get('hint_cache', {}) # Ensure it's a dict
    if cache_key in hint_cache_dict:
        cached_entry = hint_cache_dict[cache_key]
        # Cache validity period (e.g., 10 minutes = 600 seconds)
        if time.time() - cached_entry.get('timestamp', 0) < 600:
            return cached_entry.get('hint_text') # Assuming hint is stored under 'hint_text'
    return None

def cache_hint(cache_key: str, hint_text: str, state: Dict[str, Any]) -> None:
    """
    Stores hint in cache for future use.
    MODIFIED: Uses generic 'hint_cache'.
    """
    if 'hint_cache' not in state or not isinstance(state['hint_cache'], dict):
        state['hint_cache'] = {} # Initialize if not present or wrong type

    state['hint_cache'][cache_key] = {
        'hint_text': hint_text,
        'timestamp': time.time()
    }
    # Basic cache eviction: if cache grows too large, remove oldest entries
    if len(state['hint_cache']) > 30: # Max 30 cached hints
        sorted_cache = sorted(state['hint_cache'].items(), key=lambda x: x[1]['timestamp'])
        state['hint_cache'] = dict(sorted_cache[-20:]) # Keep the latest 20


def format_guide_response(raw_response: str, TF: type) -> str:
    """
    Formats the Guide's response with appropriate styling.
    MODIFIED: Generic name, was format_lyra_response. Uses TF passed as class.
    """
    response = raw_response.strip()
    formatted_lines = []
    lines = response.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            formatted_lines.append("")
            continue

        # Basic Markdown-like formatting
        if line_stripped.startswith('**') and line_stripped.endswith('**') and len(line_stripped) > 4:
            content = line_stripped[2:-2]
            formatted_lines.append(f"{TF.BOLD}{TF.BRIGHT_CYAN}{content}{TF.RESET}")
        elif line_stripped.startswith('* ') or line_stripped.startswith('- '):
            # Basic bullet points with dimming
            formatted_lines.append(f"{TF.DIM}{line_stripped}{TF.RESET}")
        elif line_stripped.startswith('# '): # Simple heading
            formatted_lines.append(f"{TF.BOLD}{TF.CYAN}{line_stripped[2:]}{TF.RESET}")
        else:
            formatted_lines.append(TF.format_terminal_text(line_stripped, width=TF.get_terminal_width() -2)) # Apply general wrapping

    return '\n'.join(formatted_lines)