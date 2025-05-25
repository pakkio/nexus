# Path: hint_manager.py
# FIXED: Updated build_initial_lyra_prompt() to accept 6 parameters including story_context

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
    if 'seals_collected' in plot_flags:
        critical_flags_parts.append(f"seals:{plot_flags['seals_collected']}")
    if 'evidence_count' in plot_flags:
        critical_flags_parts.append(f"evidence:{plot_flags['evidence_count']}")

    critical_flags_str = "_".join(critical_flags_parts) if critical_flags_parts else "no_flags"

    # Combine all elements
    cache_key_raw = f"{player_id}_{npc_code}_{last_messages_hash}_{critical_flags_str}"
    return hashlib.md5(cache_key_raw.encode('utf-8')).hexdigest()


def summarize_conversation_for_lyra(chat_history: List[Dict[str, str]],
                                    llm_wrapper_func: Callable,
                                    model_name: str,
                                    TF: type) -> str:
    """
    Summarizes the current conversation between player and NPC for Lyra's guidance.
    """
    if not chat_history or len(chat_history) == 0:
        return "No conversation has taken place yet."

    # Take last 6 messages for context (3 exchanges)
    recent_messages = chat_history[-6:] if len(chat_history) > 6 else chat_history

    conversation_text = ""
    for msg in recent_messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if role == 'user':
            conversation_text += f"Player: {content}\n"
        elif role == 'assistant':
            conversation_text += f"NPC: {content}\n"

    # Create summarization prompt
    summarization_messages = [
        {
            "role": "system",
            "content": """You are an expert at summarizing conversations for strategic guidance. 
            Summarize this player-NPC conversation focusing on:
            - What the player learned or discovered
            - What the player asked about or seemed interested in
            - Any quests, items, or objectives mentioned
            - The NPC's key responses or offers
            - The player's apparent goals or concerns
            
            Keep it concise but include all strategically relevant details."""
        },
        {
            "role": "user",
            "content": f"Summarize this conversation:\n\n{conversation_text}"
        }
    ]

    try:
        summary, _ = llm_wrapper_func(
            messages=summarization_messages,
            model_name=model_name,
            stream=False,
            collect_stats=False
        )
        return summary.strip()
    except Exception as e:
        print(f"{TF.YELLOW}Warning: Could not generate conversation summary: {e}{TF.RESET}")
        return f"Recent conversation summary unavailable. Last exchange: {conversation_text[-200:]}"


def build_initial_lyra_prompt(summary: str,
                              player_data: Dict[str, Any],
                              player_profile: Dict[str, Any],
                              stashed_npc_data: Dict[str, Any],
                              TF: type,
                              story_context: str) -> str:
    """
    FIXED: Now accepts 6 parameters including story_context.
    Builds the initial prompt for Lyra consultation based on current game state.
    """

    # Extract key information
    player_name = player_data.get('player_id', 'Seeker')
    current_area = player_data.get('current_area', 'Unknown Location')

    # NPC information
    npc_name = stashed_npc_data.get('name', 'Unknown NPC') if stashed_npc_data else 'No one'
    npc_area = stashed_npc_data.get('area', current_area) if stashed_npc_data else current_area
    npc_role = stashed_npc_data.get('role', 'Unknown Role') if stashed_npc_data else None

    # Player profile insights
    core_traits = player_profile.get('core_traits', {})
    decision_patterns = player_profile.get('decision_patterns', [])
    key_experiences = player_profile.get('key_experiences_tags', [])
    interaction_style = player_profile.get('interaction_style_summary', 'Unknown style')

    # Build the prompt with story context
    prompt_parts = [
        f"Salve, Lyra. Sono {player_name}, il Cercatore di cui hai sentito parlare.",
        "",
        f"**Situazione attuale:**",
        f"- Mi trovo attualmente in: {current_area}",
    ]

    if npc_name != 'No one':
        prompt_parts.extend([
            f"- Stavo parlando con: {npc_name}",
            f"- Luogo dell'incontro: {npc_area}",
        ])
        if npc_role:
            prompt_parts.append(f"- Il loro ruolo: {npc_role}")
    else:
        prompt_parts.append("- Non stavo parlando con nessuno in particolare")

    prompt_parts.extend([
        "",
        f"**Contesto della conversazione:**",
        summary if summary else "Nessuna conversazione significativa ancora.",
        "",
        f"**Il mio profilo comportamentale:**"
    ])

    # Add key traits with values
    if core_traits:
        prompt_parts.append("- Tratti principali:")
        for trait, value in core_traits.items():
            if value >= 7:
                intensity = "molto alto"
            elif value >= 6:
                intensity = "alto"
            elif value >= 4:
                intensity = "moderato"
            else:
                intensity = "basso"
            prompt_parts.append(f"  * {trait.title()}: {intensity} ({value}/10)")

    # Add recent behavioral patterns
    if decision_patterns:
        recent_patterns = decision_patterns[-3:] if len(decision_patterns) > 3 else decision_patterns
        prompt_parts.extend([
            "- Schemi comportamentali recenti:",
            *[f"  * {pattern}" for pattern in recent_patterns]
        ])

    # Add key experiences
    if key_experiences:
        recent_experiences = key_experiences[-3:] if len(key_experiences) > 3 else key_experiences
        prompt_parts.extend([
            "- Esperienze chiave:",
            *[f"  * {exp}" for exp in recent_experiences]
        ])

    prompt_parts.extend([
        f"- Stile di interazione: {interaction_style}",
        "",
        f"**Contesto della storia ({story_context}):**",
    ])

    # Add story-specific context based on "The Shattered Veil"
    if "Shattered Veil" in story_context or "shattered" in story_context.lower():
        prompt_parts.extend([
            "Il Velo che protegge Eldoria si sta sgretolando. Ho bisogno della tua saggezza",
            "per capire come procedere nella mia missione di raccogliere prove della sua",
            "decadenza e trovare i componenti per riparare i Sigilli Antichi.",
        ])
    else:
        prompt_parts.extend([
            f"Sto vivendo un'avventura in {story_context}.",
            "Ho bisogno della tua guida per capire come procedere al meglio.",
        ])

    prompt_parts.extend([
        "",
        "Cosa consigli? Come dovrei procedere data la mia situazione attuale?",
        "Quali sono le priorità che dovrei considerare?"
    ])

    return "\n".join(prompt_parts)


def get_cached_hint(cache_key: str, state: Dict[str, Any]) -> Optional[str]:
    """
    Retrieves cached hint if available and still valid.
    """
    # Simple in-memory cache for now - in production this could be stored in DB
    hint_cache = state.get('hint_cache', {})

    if cache_key in hint_cache:
        cached_entry = hint_cache[cache_key]
        # Check if cache is still fresh (e.g., less than 10 minutes old)
        if time.time() - cached_entry.get('timestamp', 0) < 600:  # 10 minutes
            return cached_entry.get('hint')

    return None


def cache_hint(cache_key: str, hint: str, state: Dict[str, Any]) -> None:
    """
    Stores hint in cache for future use.
    """
    if 'hint_cache' not in state:
        state['hint_cache'] = {}

    state['hint_cache'][cache_key] = {
        'hint': hint,
        'timestamp': time.time()
    }

    # Limit cache size to prevent memory issues
    if len(state['hint_cache']) > 50:
        # Remove oldest entries
        sorted_cache = sorted(
            state['hint_cache'].items(),
            key=lambda x: x[1]['timestamp']
        )
        # Keep only the 30 most recent
        state['hint_cache'] = dict(sorted_cache[-30:])


def format_lyra_response(raw_response: str, TF: type) -> str:
    """
    Formats Lyra's response with appropriate styling.
    """
    # Clean up the response
    response = raw_response.strip()

    # Add Lyra's distinctive formatting
    formatted_lines = []
    lines = response.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append("")
            continue

        # Style different types of content
        if line.startswith('**') and line.endswith('**'):
            # Headers/emphasis
            clean_line = line.replace('**', '')
            formatted_lines.append(f"{TF.BOLD}{TF.CYAN}{clean_line}{TF.RESET}")
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet points
            formatted_lines.append(f"{TF.DIM}{line}{TF.RESET}")
        elif line.startswith('  '):
            # Indented content
            formatted_lines.append(f"{TF.DIM}{line}{TF.RESET}")
        else:
            # Regular text
            formatted_lines.append(line)

    return '\n'.join(formatted_lines)