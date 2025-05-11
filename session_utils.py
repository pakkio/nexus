# Path: session_utils.py

import random
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Assuming these are available either via direct import in modules that use these utils,
# or passed as arguments if defined elsewhere.
# from terminal_formatter import TerminalFormatter
# from chat_manager import ChatSession # Class reference
# from db_manager import DbManager # Class reference
# from main_utils import format_storyboard_for_prompt


def build_system_prompt(npc: Dict[str, Any], story: str, TerminalFormatter) -> str:
    """Builds the system prompt for the LLM."""
    # Ensure this utility is available, e.g., from main_utils
    # For this example, assuming it's callable as format_storyboard_for_prompt
    try:
        from main_utils import format_storyboard_for_prompt
    except ImportError:
        # Fallback or raise error if main_utils is critical here
        def format_storyboard_for_prompt(s_text, max_length=300):
            if len(s_text) > max_length: return s_text[:max_length-3] + "..."
            return s_text
        print("Warning (session_utils): main_utils.format_storyboard_for_prompt not found, using basic fallback.")


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
        db, # DbManager instance
        player_id: str,
        current_npc: Optional[Dict[str, Any]],
        chat_session, # ChatSession instance
        TerminalFormatter
):
    """Saves the current conversation history."""
    if not current_npc or not chat_session:
        return

    npc_code = current_npc.get("code")
    if not npc_code:
        print(f"{TerminalFormatter.RED}⚠️ Error: Cannot save conversation, current NPC ({current_npc.get('name', 'Unknown')}) is missing a 'code'.{TerminalFormatter.RESET}")
        return

    if not player_id:
        print(f"{TerminalFormatter.RED}⚠️ Error: Cannot save conversation, player_id is missing.{TerminalFormatter.RESET}")
        return

    try:
        # Only save if there's more than just the system prompt, or if messages list is not empty
        if chat_session.messages: # Check if there are any user/assistant messages
            history_to_save = chat_session.get_history() # Gets system prompt + messages
            db.save_conversation(player_id, npc_code, history_to_save)
    except Exception as e:
        print(f"{TerminalFormatter.RED}⚠️ Error during saving conversation for {npc_code} (Player: {player_id}): {e}{TerminalFormatter.RESET}")
        # traceback.print_exc() # Uncomment for more detailed debug if needed


def load_and_prepare_conversation(
        db, # DbManager instance
        player_id: str,
        area_name: str,
        npc_name: str,
        model_name: Optional[str],
        story: str,
        ChatSession_class, # Pass ChatSession class reference
        TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]: # Returns (npc_data, chat_session_instance)
    """
    Loads specific NPC data and prepares a new ChatSession, loading history.
    This function NO LONGER prints the conversation start banner or opening line.
    """
    # print(f"{TerminalFormatter.DIM}[CORE] Loading data for NPC '{npc_name}' in '{area_name}'...{TerminalFormatter.RESET}") # Already printed by caller
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
        print(f"{TerminalFormatter.DIM}[CORE] Preparing system prompt...{TerminalFormatter.RESET}")
        system_prompt = build_system_prompt(npc_data, story, TerminalFormatter)

        print(f"{TerminalFormatter.DIM}[CORE] Initializing Chat Session...{TerminalFormatter.RESET}")
        chat_session = ChatSession_class(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)
        print(f"{TerminalFormatter.DIM}[CORE] Chat Session ready (Model: {chat_session.get_model_name()}).{TerminalFormatter.RESET}")

        print(f"{TerminalFormatter.DIM}[CORE] Loading history for Player '{player_id}' with {npc_code}...{TerminalFormatter.RESET}")
        db_conversation_history = db.load_conversation(player_id, npc_code)
        history_count = 0
        if db_conversation_history:
            # System prompt is set via set_system_prompt, add_message skips role 'system'
            # So, iterate and add only user/assistant messages from loaded history.
            # The history from DB might include a system message if saved that way previously.
            for msg in db_conversation_history:
                role = msg.get("role")
                content = msg.get("content")
                if role and content and role != "system": # Ensure ChatSession.add_message logic is respected
                    chat_session.add_message(role, content)
            history_count = len(chat_session.messages) # Count actual user/assistant messages added
            print(f"{TerminalFormatter.DIM}[CORE] Loaded {history_count} previous user/assistant messages.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.DIM}[CORE] No previous history found for Player '{player_id}' with {npc_data.get('name')}.{TerminalFormatter.RESET}")

        return npc_data, chat_session

    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error during conversation load/prepare for {npc_name} (Player: {player_id}): {e}{TerminalFormatter.RESET}")
        # traceback.print_exc() # Uncomment for more detailed debug if needed
        return None, None


def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
    """Generates a simple opening line for an NPC."""
    name = npc_data.get('name', 'the figure')
    role = npc_data.get('role', '')
    hooks_text = npc_data.get('dialogue_hooks', '')
    hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()] if hooks_text else []

    if hooks:
        chosen_hook = random.choice(hooks)
        # Ensure quotes if not already an action or fully quoted
        if not chosen_hook.startswith(("*","\"")): # Simple check, can be made more robust
            return f"*{name} looks at you and says,* \"{chosen_hook}\""
        else:
            return chosen_hook # Assume it's pre-formatted (e.g., "*An action*" or "\"A direct quote\"")
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

# --- NEW/MODIFIED FUNCTIONS for Auto-Talk ---
def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TerminalFormatter):
    """Prints the standard banner and opening line when a conversation starts."""
    print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_data.get('name', 'NPC').upper()} IN {area_name.upper()} {TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.DIM}Type '/exit' to leave this conversation, '/help' for other commands.{TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}\n")
    print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{npc_data['name']} > {TerminalFormatter.RESET}")
    opening_line = get_npc_opening_line(npc_data, TerminalFormatter)
    print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
    print()

def start_conversation_with_specific_npc(
        db, # DbManager instance
        player_id: str,
        area_name: str,
        npc_name: str, # Specific NPC name
        model_name: Optional[str],
        story: str,
        ChatSession_class, # Pass ChatSession class reference
        TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """
    Prepares and starts a conversation with a SPECIFIC NPC, including printing the intro.
    """
    print(f"{TerminalFormatter.DIM}Attempting to start conversation with '{npc_name}' in '{area_name}'...{TerminalFormatter.RESET}")
    npc_data, new_session = load_and_prepare_conversation(
        db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TerminalFormatter
    )

    if npc_data and new_session:
        print_conversation_start_banner(npc_data, area_name, TerminalFormatter)
        return npc_data, new_session
    else:
        # load_and_prepare_conversation would have printed errors if NPC not found or other issues.
        return None, None


def auto_start_default_npc_conversation(
        db, # DbManager instance
        player_id: str,
        area_name: str,
        model_name: Optional[str],
        story: str,
        ChatSession_class, # Pass ChatSession class reference
        TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """
    Attempts to find a default NPC in the area and initiate a conversation, including printing greetings.
    """
    print(f"{TerminalFormatter.DIM}Searching for a default NPC in '{area_name}' to talk to...{TerminalFormatter.RESET}")
    default_npc_info = db.get_default_npc(area_name)

    if not default_npc_info:
        # This message is now more context-specific for auto-start
        print(f"{TerminalFormatter.DIM}No default NPC found to automatically talk to in '{area_name}'. You can use /talk or /who.{TerminalFormatter.RESET}")
        return None, None

    default_npc_name = default_npc_info.get('name')
    if not default_npc_name: # Should ideally not happen if get_default_npc returns valid data
        print(f"{TerminalFormatter.RED}Error: Default NPC data for '{area_name}' is missing a name.{TerminalFormatter.RESET}")
        return None, None

    # Use the specific NPC conversation starter
    return start_conversation_with_specific_npc(
        db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TerminalFormatter
    )
# --- END NEW/MODIFIED FUNCTIONS ---

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
    """Fetches the list of all NPCs from the database/mockup."""
    try:
        return db.list_npcs_by_area()
    except Exception as e:
        print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}")
        return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
    """Derives unique area names from the provided NPC list."""
    if not all_known_npcs: return []
    return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)