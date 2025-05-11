# Path: session_utils.py

import random
import traceback # Keep if used for more detailed error logging elsewhere
from typing import Dict, List, Any, Optional, Tuple

# Assuming these are available (passed as args or globally/module-level imported)
# from terminal_formatter import TerminalFormatter
# from chat_manager import ChatSession # Class reference
# from db_manager import DbManager # Class reference

# Utility for formatting storyboard context in prompts
def _format_storyboard_for_prompt(story_text: str, max_length: int = 300) -> str:
    """Truncates and formats the storyboard for inclusion in prompts."""
    if not isinstance(story_text, str): return "[Invalid Storyboard Data]"
    if len(story_text) > max_length:
        truncated = story_text[:max_length].rsplit(' ', 1)[0] # Clean cut
        return truncated + "..."
    return story_text

def build_system_prompt(
        npc: Dict[str, Any],
        story: str,
        TerminalFormatter,
        # These are for future enhancements (summaries, profiles) - keep them for now if you added them previously
        player_id: Optional[str] = None,
        db=None, # DbManager instance, optional for now, needed for profiles
        conversation_summary: Optional[str] = None
) -> str:
    """Builds the system prompt for the LLM."""
    story_context = _format_storyboard_for_prompt(story) # Use local helper or import
    name = npc.get('name', 'Unknown NPC')
    role = npc.get('role', 'Unknown Role')
    area = npc.get('area', 'Unknown Area')
    motivation = npc.get('motivation', 'None specified')
    goal = npc.get('goal', 'achieve their objectives') # NPC's goal
    hooks = npc.get('dialogue_hooks', 'Standard dialogue')
    veil = npc.get('veil_connection', '')

    # --- NEW: V.O. Hint for NPC context ---
    # This is what the NPC "knows" the player *should* be doing to help *them*
    # It's based on the PlayerHint from NPC data, or derived from Goal.
    player_hint_for_npc_context = npc.get('playerhint', f"The player might try to help you achieve your goal: '{goal}'.")
    # --- END NEW ---

    prompt_lines = [
        f"Sei {name}, un/una {role} nell'area di {area}.",
        f"Motivazione: '{motivation}'. Obiettivo (cosa TU, l'NPC, vuoi ottenere): '{goal}'.",
        # --- NEW: Add V.O. to system prompt ---
        f"V.O. (Guida per l'azione del giocatore per aiutarti): \"{player_hint_for_npc_context}\"",
        # --- END NEW ---
        f"Stile di dialogo suggerito (usa queste frasi o simili come ispirazione): {hooks}.",
    ]
    if veil: prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto): {veil}")

    # For future enhancements (summary, gossips)
    if conversation_summary:
        prompt_lines.append(f"Riassunto delle tue interazioni precedenti con questo giocatore: {conversation_summary}")

    # if player_id and db: # For profile/gossips - keep for when you implement it
    #     player_profile = db.load_player_profile(player_id)
    #     if player_profile and player_profile.get("rumors"):
    #         rumor_list = player_profile["rumors"]
    #         if rumor_list:
    #             gossips = "; ".join(rumor_list[:3]) + ("..." if len(rumor_list) > 3 else "")
    #             prompt_lines.append(f"Voci che girano su questo giocatore: {gossips}")

    prompt_lines.extend([
        f"Contesto Globale del Mondo: {story_context}",
        "Parla in modo appropriato al setting e al tuo ruolo. Mantieni il personaggio.",
        "Risposte tendenzialmente concise (2-4 frasi), a meno che non venga richiesto di elaborare o la situazione lo richieda."
    ])
    return "\n".join(prompt_lines)

def save_current_conversation(
        db, player_id: str, current_npc: Optional[Dict[str, Any]],
        chat_session, TerminalFormatter,
        # Add these if/when summarization is implemented, for now they are not used here
        # llm_wrapper_func=None, model_name_for_summary=None
):
    if not current_npc or not chat_session: return
    npc_code = current_npc.get("code")
    if not npc_code or not player_id: print(f"{TerminalFormatter.RED}⚠️ Error: Cannot save, missing npc_code or player_id.{TerminalFormatter.RESET}"); return

    try:
        # For now, still saves full history. Summarization is a separate step.
        if chat_session.messages: # Only save if there's actual dialogue beyond system prompt
            history_to_save = chat_session.get_history()
            db.save_conversation(player_id, npc_code, history_to_save) # Saves full history
            # When summarization is added, this call changes:
            # 1. Generate summary (e.g., summary = await generate_conversation_summary(...))
            # 2. db.save_conversation(player_id, npc_code, summary) # Pass summary string
            # print(f"{TerminalFormatter.DIM}Conversation (full) saved for {npc_code}.{TerminalFormatter.RESET}")
    except Exception as e:
        print(f"{TerminalFormatter.RED}⚠️ Error saving conversation for {npc_code} (Player: {player_id}): {e}{TerminalFormatter.RESET}")

def load_and_prepare_conversation(
        db, player_id: str, area_name: str, npc_name: str,
        model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """Loads NPC, prepares session, loads history (full for now, or summary later). NO LONGER PRINTS INTRO."""
    try:
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' not found in '{area_name}'.{TerminalFormatter.RESET}")
            return None, None
        npc_code = npc_data.get("code")
        if not npc_code:
            print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' missing 'code'.{TerminalFormatter.RESET}")
            return None, None

        print(f"{TerminalFormatter.DIM}[CORE] NPC '{npc_data.get('name')}' (Code: {npc_code}) found.{TerminalFormatter.RESET}")

        # For summarization, you'd load summary here:
        # previous_summary = db.load_conversation(player_id, npc_code) # This would return summary string
        # For now, we are not using summary in system prompt directly in this step, but it's ready for when you do

        # Build system prompt (pass player_id and db if profile/gossips are active)
        system_prompt = build_system_prompt(npc_data, story, TerminalFormatter, player_id=player_id, db=db)
        # conversation_summary=previous_summary) # Add when summary is loaded

        chat_session = ChatSession_class(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)

        # --- NEW: Set player hint in session ---
        player_hint_from_data = npc_data.get('playerhint') # From NPC.txt (parsed by load.py)
        if not player_hint_from_data: # Fallback to a generic hint based on goal
            npc_goal = npc_data.get('goal')
            npc_needed = npc_data.get('needed_object')
            if npc_goal:
                player_hint_from_data = f"You might need to help them with their goal: '{npc_goal}'."
                if npc_needed: player_hint_from_data += f" It seems they require a '{npc_needed}'."
        chat_session.set_player_hint(player_hint_from_data) # Store it
        # --- END NEW ---

        print(f"{TerminalFormatter.DIM}[CORE] Chat Session ready (Model: {chat_session.get_model_name()}). Hint set.{TerminalFormatter.RESET}")

        # Load full conversation history for now
        print(f"{TerminalFormatter.DIM}[CORE] Loading full message history for Player '{player_id}' with {npc_code}...{TerminalFormatter.RESET}")
        db_conversation_history = db.load_conversation(player_id, npc_code) # This returns List[Dict] for now

        if db_conversation_history:
            for msg in db_conversation_history:
                role, content = msg.get("role"), msg.get("content")
                if role and content and role != "system": chat_session.add_message(role, content)
            print(f"{TerminalFormatter.DIM}[CORE] Loaded {len(chat_session.messages)} previous user/assistant messages.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.DIM}[CORE] No previous message history found for {npc_data.get('name')}.{TerminalFormatter.RESET}")

        return npc_data, chat_session
    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TerminalFormatter.RESET}")
        return None, None


def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
    # ... (Keep existing implementation as provided previously) ...
    name = npc_data.get('name', 'the figure')
    role = npc_data.get('role', '')
    hooks_text = npc_data.get('dialogue_hooks', '')
    hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()] if hooks_text else []

    if hooks:
        chosen_hook = random.choice(hooks)
        if not chosen_hook.startswith(("*","\"")):
            return f"*{name} looks at you and says,* \"{chosen_hook}\""
        else:
            return chosen_hook
    elif role:
        greetings = [
            f"*{name} the {role} regards you calmly.* What do you want?",
            f"*{name}, the {role}, looks up as you approach.* Yes?",
            f"*{name} gives a slight nod.* I am the {role} here. Speak.",
            f"You stand before {name}, the {role}.",
        ]
        return random.choice(greetings)
    else:
        return f"*{name} watches you approach, waiting for you to speak.*"


def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TerminalFormatter):
    """Prints the standard banner and opening line when a conversation starts."""
    # ... (Keep existing implementation as provided previously) ...
    print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_data.get('name', 'NPC').upper()} IN {area_name.upper()} {TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.DIM}Type '/exit' to leave this conversation, '/help' for other commands.{TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}\n")
    print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{npc_data['name']} > {TerminalFormatter.RESET}")
    opening_line = get_npc_opening_line(npc_data, TerminalFormatter)
    print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
    print()

def start_conversation_with_specific_npc(
        db, player_id: str, area_name: str, npc_name: str,
        model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """Prepares and starts a conversation with a SPECIFIC NPC, including printing the intro."""
    print(f"{TerminalFormatter.DIM}Attempting to start conversation with '{npc_name}' in '{area_name}'...{TerminalFormatter.RESET}")
    npc_data, new_session = load_and_prepare_conversation(
        db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TerminalFormatter
    )
    if npc_data and new_session:
        print_conversation_start_banner(npc_data, area_name, TerminalFormatter)
        return npc_data, new_session
    return None, None

def auto_start_default_npc_conversation(
        db, player_id: str, area_name: str, model_name: Optional[str],
        story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """Attempts to find a default NPC and initiate a conversation."""
    print(f"{TerminalFormatter.DIM}Searching for a default NPC in '{area_name}' to talk to...{TerminalFormatter.RESET}")
    default_npc_info = db.get_default_npc(area_name)
    if not default_npc_info:
        print(f"{TerminalFormatter.DIM}No default NPC found to automatically talk to in '{area_name}'. You can use /talk or /who.{TerminalFormatter.RESET}")
        return None, None
    default_npc_name = default_npc_info.get('name')
    if not default_npc_name:
        print(f"{TerminalFormatter.RED}Error: Default NPC data for '{area_name}' is missing a name.{TerminalFormatter.RESET}")
        return None, None
    return start_conversation_with_specific_npc(
        db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TerminalFormatter
    )

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
    # ... (Keep existing implementation) ...
    try:
        return db.list_npcs_by_area()
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}")
        return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
    # ... (Keep existing implementation) ...
    if not all_known_npcs: return []
    return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)