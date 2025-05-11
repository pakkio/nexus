# Path: session_utils.py
# Updated build_system_prompt for Credits in GIVEN_ITEMS example

import random
import traceback 
from typing import Dict, List, Any, Optional, Tuple

def _format_storyboard_for_prompt(story_text: str, max_length: int = 300) -> str:
    if not isinstance(story_text, str): return "[Invalid Storyboard Data]"
    if len(story_text) > max_length:
        truncated = story_text[:max_length].rsplit(' ', 1)[0] 
        return truncated + "..."
    return story_text

def build_system_prompt(
    npc: Dict[str, Any], 
    story: str, 
    TerminalFormatter, 
    player_id: Optional[str] = None, 
    db=None, 
    conversation_summary: Optional[str] = None 
) -> str:
    story_context = _format_storyboard_for_prompt(story)
    name = npc.get('name', 'Unknown NPC')
    role = npc.get('role', 'Unknown Role')
    area = npc.get('area', 'Unknown Area')
    motivation = npc.get('motivation', 'None specified')
    goal = npc.get('goal', 'achieve their objectives')
    player_hint_for_npc_context = npc.get('playerhint', f"The player might try to help you achieve your goal: '{goal}'.")
    hooks = npc.get('dialogue_hooks', 'Standard dialogue')
    veil = npc.get('veil_connection', '')

    prompt_lines = [
        f"Sei {name}, un/una {role} nell'area di {area}.",
        f"Motivazione: '{motivation}'. Obiettivo (cosa TU, l'NPC, vuoi ottenere): '{goal}'.",
        f"V.O. (Guida per l'azione del giocatore per aiutarti): \"{player_hint_for_npc_context}\"",
        f"Stile di dialogo suggerito (usa queste frasi o simili come ispirazione): {hooks}.",
    ]
    if veil: prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto): {veil}")
    
    if conversation_summary:
        prompt_lines.append(f"Riassunto delle tue interazioni precedenti con questo giocatore: {conversation_summary}")
    
    # Example for future profile integration
    # if player_id and db and hasattr(db, 'load_player_profile'): 
    #     player_profile = db.load_player_profile(player_id)
    #     if player_profile and player_profile.get("rumors"):
    #         rumor_list = player_profile["rumors"]
    #         if rumor_list:
    #             gossips = "; ".join(rumor_list[:3]) + ("..." if len(rumor_list) > 3 else "")
    #             prompt_lines.append(f"Voci che girano su questo giocatore: {gossips}")

    prompt_lines.extend([
        f"Contesto Globale del Mondo: {story_context}",
        "Parla in modo appropriato al setting e al tuo ruolo. Mantieni il personaggio.",
        "Risposte tendenzialmente concise (2-4 frasi), a meno che non venga richiesto di elaborare.",
        "ISTRUZIONE IMPORTANTE PER QUANDO DAI OGGETTI O CREDITI:",
        "Se nella tua risposta decidi di dare uno o più oggetti/crediti al giocatore, DEVI includere una riga speciale ALLA FINE della tua risposta testuale.",
        "Questa riga DEVE essere ESATTAMENTE nel seguente formato: ",
        "[GIVEN_ITEMS: NomeOggetto1, Quantità Credits, NomeOggetto2, ...]",
        "Per i crediti, usa il formato 'X Credits' (es. '100 Credits'). Separa i nomi degli oggetti/crediti con una virgola.",
        "Se non dai nessun oggetto o credito, NON includere ASSOLUTAMENTE la riga [GIVEN_ITEMS:].",
        "Esempio di risposta CORRETTA in cui DAI oggetti e crediti:",
        "NPC Dialogo: Ottimo lavoro! Prendi questa Spada Leggendaria e questi 50 Credits per il disturbo.",
        "[GIVEN_ITEMS: Spada Leggendaria, 50 Credits]",
        "Esempio di risposta CORRETTA in cui DAI solo crediti:",
        "NPC Dialogo: Ecco la tua ricompensa.",
        "[GIVEN_ITEMS: 100 Credits]",
        "Esempio di risposta CORRETTA in cui NON DAI nulla:",
        "NPC Dialogo: Non ho nulla per te al momento."
    ])
    return "\n".join(prompt_lines)

def load_and_prepare_conversation(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    try:
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data: # ... (error handling) ...
            print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' not found in '{area_name}'.{TerminalFormatter.RESET}")
            return None, None
        npc_code = npc_data.get("code") # ... (error handling for code) ...
        if not npc_code: print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' missing 'code'.{TerminalFormatter.RESET}"); return None, None

        # print(f"{TerminalFormatter.DIM}[CORE] NPC '{npc_data.get('name')}' (Code: {npc_code}) found.{TerminalFormatter.RESET}") # Less verbose
        
        # For summarization feature (currently db.load_conversation returns full history)
        # previous_summary = db.load_conversation(player_id, npc_code) # This would return summary string
        # For now, build_system_prompt might not use the summary yet if load_conversation isn't updated for it.
        
        system_prompt = build_system_prompt(npc_data, story, TerminalFormatter, player_id=player_id, db=db) # Pass player_id, db
                                            
        chat_session = ChatSession_class(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)
        
        player_hint_from_data = npc_data.get('playerhint') 
        if not player_hint_from_data: 
            npc_goal = npc_data.get('goal'); npc_needed = npc_data.get('needed_object')
            if npc_goal:
                player_hint_from_data = f"Help them with: '{npc_goal}'."
                if npc_needed: player_hint_from_data += f" They need '{npc_needed}'."
        chat_session.set_player_hint(player_hint_from_data) 
        # print(f"{TerminalFormatter.DIM}[CORE] Chat Session ready. Hint set.{TerminalFormatter.RESET}") # Less verbose

        # print(f"{TerminalFormatter.DIM}[CORE] Loading message history for Player '{player_id}' with {npc_code}...{TerminalFormatter.RESET}") # Less verbose
        db_conversation_history = db.load_conversation(player_id, npc_code) # Returns List[Dict]
        
        if db_conversation_history: 
            for msg in db_conversation_history:
                role, content = msg.get("role"), msg.get("content")
                if role and content and role != "system": chat_session.add_message(role, content)
            # print(f"{TerminalFormatter.DIM}[CORE] Loaded {len(chat_session.messages)} previous messages.{TerminalFormatter.RESET}") # Less verbose
        # else: print(f"{TerminalFormatter.DIM}[CORE] No previous history for {npc_data.get('name')}.{TerminalFormatter.RESET}")
            
        return npc_data, chat_session
    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TerminalFormatter.RESET}")
        return None, None

def save_current_conversation( db, player_id: str, current_npc: Optional[Dict[str, Any]], chat_session, TerminalFormatter):
    # ... (keep existing implementation) ...
    if not current_npc or not chat_session: return
    npc_code = current_npc.get("code")
    if not npc_code or not player_id: return
    try:
        if chat_session.messages: 
            history_to_save = chat_session.get_history()
            db.save_conversation(player_id, npc_code, history_to_save) 
    except Exception as e: print(f"Err saving convo for {npc_code}: {e}")


def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
    # ... (keep existing implementation) ...
    name = npc_data.get('name', 'the figure'); role = npc_data.get('role', '')
    hooks_text = npc_data.get('dialogue_hooks', ''); hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()] if hooks_text else []
    if hooks:
        chosen_hook = random.choice(hooks)
        if not chosen_hook.startswith(("*","\"")): return f"*{name} says,* \"{chosen_hook}\""
        else: return chosen_hook
    elif role: return random.choice([f"*{name} the {role} regards you.* What?", f"*{name}, the {role}, looks up.* Yes?"])
    else: return f"*{name} watches you.*"


def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TerminalFormatter):
    # ... (keep existing implementation) ...
    print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_data.get('name', 'NPC').upper()} IN {area_name.upper()} {TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.DIM}Type '/exit' to leave, '/help' for commands.{TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}\n")
    print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{npc_data['name']} > {TerminalFormatter.RESET}")
    opening_line = get_npc_opening_line(npc_data, TerminalFormatter)
    print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
    print()

def start_conversation_with_specific_npc(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    # ... (keep existing implementation) ...
    # print(f"{TerminalFormatter.DIM}Attempting to start conversation with '{npc_name}'...{TerminalFormatter.RESET}") # Less verbose
    npc_data, new_session = load_and_prepare_conversation(
        db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TerminalFormatter )
    if npc_data and new_session:
        print_conversation_start_banner(npc_data, area_name, TerminalFormatter)
        return npc_data, new_session
    return None, None

def auto_start_default_npc_conversation(
    db, player_id: str, area_name: str, model_name: Optional[str],
    story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    # ... (keep existing implementation) ...
    # print(f"{TerminalFormatter.DIM}Searching for default NPC in '{area_name}'...{TerminalFormatter.RESET}") # Less verbose
    default_npc_info = db.get_default_npc(area_name)
    if not default_npc_info:
        print(f"{TerminalFormatter.DIM}No default NPC in '{area_name}'. Use /talk or /who.{TerminalFormatter.RESET}")
        return None, None
    default_npc_name = default_npc_info.get('name')
    if not default_npc_name: return None, None # Error already printed by get_default if malformed
    return start_conversation_with_specific_npc(
        db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TerminalFormatter )

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
    # ... (keep existing implementation) ...
    try: return db.list_npcs_by_area()
    except Exception as e: print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}"); return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
    # ... (keep existing implementation) ...
    if not all_known_npcs: return []
    return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)

