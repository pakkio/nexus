# Path: session_utils.py

import random
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Assuming these are imported in the main modules or passed if needed
# If not, import them here. For simplicity, assume they are available where called.
# from terminal_formatter import TerminalFormatter
# from chat_manager import ChatSession
# from db_manager import DbManager
# from main_utils import format_storyboard_for_prompt


# --- Renamed Helper Functions (Removed leading underscore) ---

def build_system_prompt(npc: Dict[str, Any], story: str, TerminalFormatter) -> str:
    """Builds the system prompt for the LLM."""
    # Import or expect TerminalFormatter passed if needed within function scope
    from main_utils import format_storyboard_for_prompt # Ensure util is available

    story_context = format_storyboard_for_prompt(story)
    name = npc.get('name', 'Unknown NPC')
    role = npc.get('role', 'Unknown Role')
    area = npc.get('area', 'Unknown Area')
    motivation = npc.get('motivation', 'None specified')
    goal = npc.get('goal', 'None specified')
    hooks = npc.get('dialogue_hooks', 'Standard dialogue')
    veil = npc.get('veil_connection', '')

    prompt_lines = [
        f"Sei {name}, un/una {role} nell'area di {area}.",
        f"Motivazione: '{motivation}'. Obiettivo: '{goal}'.",
        f"Stile di dialogo suggerito: {hooks}.",
    ]
    if veil:
        prompt_lines.append(f"Collegamento al Velo (Background Segreto): {veil}")

    prompt_lines.extend([
        f"Contesto Globale: {story_context}",
        "Parla in modo appropriato al setting (fantasy/sci-fi/ecc. come descritto nel contesto globale e nel tuo ruolo).",
        "Mantieni il personaggio. Risposte tendenzialmente brevi (2-4 frasi) a meno che non venga richiesto di elaborare."
    ])
    return "\n".join(prompt_lines)


def save_current_conversation(
        db, # Pass DbManager instance
        current_npc: Optional[Dict[str, Any]],
        chat_session, # Pass ChatSession instance
        TerminalFormatter
):
    """Saves the current conversation history to the database/mockup if possible."""
    if not current_npc or not chat_session:
        return

    npc_code = current_npc.get("code")
    if not npc_code:
        print(f"{TerminalFormatter.RED}⚠️ Error: Cannot save conversation, current NPC ({current_npc.get('name', 'Unknown')}) is missing a 'code'.{TerminalFormatter.RESET}")
        return

    try:
        history_to_save = chat_session.get_history()
        if len(history_to_save) > 1:
            db.save_conversation(npc_code, history_to_save)
    except Exception as e:
        print(f"{TerminalFormatter.RED}⚠️ Error during saving conversation for {npc_code}: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()


def load_and_prepare_conversation(
        db, # Pass DbManager instance
        area_name: str,
        npc_name: str,
        model_name: Optional[str],
        story: str,
        ChatSession, # Pass ChatSession class
        TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]: # Return type includes ChatSession instance
    """
    Loads specific NPC data and prepares a new ChatSession, loading history.
    """
    print(f"{TerminalFormatter.DIM}[CORE] Loading data for NPC '{npc_name}' in '{area_name}'...{TerminalFormatter.RESET}")
    try:
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"{TerminalFormatter.RED}❌ ERROR: NPC '{npc_name}' data not found in area '{area_name}'.{TerminalFormatter.RESET}")
            return None, None

        npc_code = npc_data.get("code")
        if not npc_code:
            print(f"{TerminalFormatter.RED}❌ ERROR: NPC '{npc_name}' data is missing a 'code'.{TerminalFormatter.RESET}")
            return None, None

        print(f"{TerminalFormatter.DIM}[CORE] NPC '{npc_data.get('name')}' (Code: {npc_code}) found.{TerminalFormatter.RESET}")

        # Prepare System Prompt using the function in this module
        print(f"{TerminalFormatter.DIM}[CORE] Preparing system prompt...{TerminalFormatter.RESET}")
        system_prompt = build_system_prompt(npc_data, story, TerminalFormatter)

        # Initialize Chat Session
        print(f"{TerminalFormatter.DIM}[CORE] Initializing Chat Session...{TerminalFormatter.RESET}")
        chat_session = ChatSession(model_name=model_name) # Use passed class
        chat_session.set_system_prompt(system_prompt)
        print(f"{TerminalFormatter.DIM}[CORE] Chat Session ready (Model: {chat_session.get_model_name()}).{TerminalFormatter.RESET}")

        # Load previous conversation history
        print(f"{TerminalFormatter.DIM}[CORE] Loading history for {npc_code}...{TerminalFormatter.RESET}")
        db_conversation_history = db.load_conversation(npc_code)
        history_count = 0
        if db_conversation_history:
            start_index = 1 if db_conversation_history[0].get("role") == "system" else 0
            for msg in db_conversation_history[start_index:]:
                role = msg.get("role")
                content = msg.get("content")
                if role and content:
                    chat_session.add_message(role, content)
            history_count = sum(1 for msg in chat_session.messages if msg.get("role") in ["user", "assistant"])
            print(f"{TerminalFormatter.DIM}[CORE] Loaded {history_count} previous user/assistant messages.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.DIM}[CORE] No previous history found for {npc_data.get('name')}.{TerminalFormatter.RESET}")

        return npc_data, chat_session

    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error during conversation load/prepare for {npc_name}: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        return None, None


def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
    """Generates a simple opening line for an NPC."""
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


# --- NPC List Management ---
# These functions now operate on the passed list `all_known_npcs`
# They are kept separate as they relate to NPC/Area data handling

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
    """Fetches the list of all NPCs from the database/mockup."""
    try:
        return db.list_npcs_by_area()
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}")
        return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
    """Derives unique area names from the provided NPC list."""
    return sorted(list({n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip()}), key=str.lower)
