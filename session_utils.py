# Path: session_utils.py
# Updated build_system_prompt for Credits in GIVEN_ITEMS example
# Minor update to save_current_conversation to filter system prompt before DB save
# Minor update to start_conversation_with_specific_npc for initial NPC line

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
    conversation_summary_for_lyra: Optional[str] = None # New for advanced /hint
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
        f"Sei {name}, un/una {role} nell'area di {area} nel mondo di Eldoria.",
        f"Motivazione: '{motivation}'. Obiettivo (cosa TU, l'NPC, vuoi ottenere): '{goal}'.",
        f"V.O. (Guida per l'azione del giocatore per aiutarti): \"{player_hint_for_npc_context}\"",
        f"Stile di dialogo suggerito (usa queste frasi o simili come ispirazione, ma sii naturale e varia le tue risposte): {hooks}.",
    ]
    if veil: prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto Importante): {veil}")

    if conversation_summary_for_lyra and name.lower() == "lyra": # Only add this context if building prompt for Lyra
        prompt_lines.append(
            f"\nINFORMAZIONE CONTESTUALE AGGIUNTIVA PER TE, LYRA:\n"
            f"Il Cercatore (giocatore) stava parlando con un altro NPC prima di consultarti. Ecco un riassunto di quella interazione:\n"
            f"\"{conversation_summary_for_lyra}\"\n"
            f"Usa questa informazione, insieme ai dettagli del giocatore che ti verranno forniti nel suo messaggio, per dare il tuo saggio consiglio."
        )

    # Example for future player profile integration (if db and player_id are provided)
    # if player_id and db and hasattr(db, 'load_player_profile'):
    #     player_profile = db.load_player_profile(player_id) # Assuming this method exists
    #     if player_profile and player_profile.get("known_deeds"):
    #         deeds = "; ".join(player_profile["known_deeds"][:3])
    #         prompt_lines.append(f"Azioni note di questo giocatore nel mondo: {deeds}")

    prompt_lines.extend([
        f"\nContesto Globale del Mondo (Eldoria): {story_context}",
        "Parla in modo appropriato al setting fantasy e al tuo ruolo. Mantieni il personaggio.",
        "Risposte tendenzialmente concise (2-4 frasi), a meno che non venga richiesto di elaborare o la situazione lo richieda.",
        "Sii consapevole delle interazioni passate se riassunte sopra o nella cronologia della chat.",
        "\nISTRUZIONE IMPORTANTE PER QUANDO DAI OGGETTI O CREDITI AL GIOCATORE:",
        "Se nella tua risposta decidi di dare uno o più oggetti/crediti al giocatore, DEVI includere una riga speciale ALLA FINE della tua risposta testuale.",
        "Questa riga DEVE essere ESATTAMENTE nel seguente formato, senza alcuna variazione: ",
        "[GIVEN_ITEMS: NomeOggetto1, Quantità Credits, NomeOggetto2, ...]",
        "Per i crediti, usa il formato 'X Credits' (es. '100 Credits'). Separa i nomi degli oggetti/crediti con una virgola.",
        "Ogni nome di oggetto o quantità di crediti deve essere separato da una virgola.",
        "Se non dai nessun oggetto o credito, NON includere ASSOLUTAMENTE la riga [GIVEN_ITEMS:].",
        "Esempio di risposta CORRETTA in cui DAI oggetti e crediti:",
        "NPC Dialogo: Ottimo lavoro! Prendi questa Spada Leggendaria e questi 50 Credits per il disturbo.",
        "[GIVEN_ITEMS: Spada Leggendaria, 50 Credits]",
        "Esempio di risposta CORRETTA in cui DAI solo un oggetto:",
        "NPC Dialogo: Ecco la Mappa Antica che cercavi.",
        "[GIVEN_ITEMS: Mappa Antica]",
        "Esempio di risposta CORRETTA in cui DAI solo crediti:",
        "NPC Dialogo: Ecco la tua ricompensa.",
        "[GIVEN_ITEMS: 100 Credits]",
        "Esempio di risposta CORRETTA in cui NON DAI nulla:",
        "NPC Dialogo: Non ho nulla per te al momento."
    ])
    return "\n".join(prompt_lines)

def load_and_prepare_conversation(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter,
    # Optional parameter for Lyra's special context when initiating hint mode
    conversation_summary_for_lyra_context: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    try:
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' not found in '{area_name}'.{TerminalFormatter.RESET}")
            return None, None
        npc_code = npc_data.get("code")
        if not npc_code:
            print(f"{TerminalFormatter.RED}❌ NPC '{npc_name}' missing 'code'.{TerminalFormatter.RESET}")
            return None, None

        system_prompt = build_system_prompt(
            npc_data, story, TerminalFormatter,
            player_id=player_id, db=db,
            conversation_summary_for_lyra=conversation_summary_for_lyra_context if npc_name.lower() == "lyra" else None
        )

        chat_session = ChatSession_class(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)

        player_hint_from_data = npc_data.get('playerhint')
        if not player_hint_from_data:
            npc_goal = npc_data.get('goal'); npc_needed = npc_data.get('needed_object')
            if npc_goal:
                player_hint_from_data = f"Help them with: '{npc_goal}'."
                if npc_needed: player_hint_from_data += f" They need '{npc_needed}'."
        chat_session.set_player_hint(player_hint_from_data)

        db_conversation_history = db.load_conversation(player_id, npc_code) # Returns List[Dict] (without system prompt)

        if db_conversation_history:
            for msg in db_conversation_history: # Already filtered, no system prompt from DB
                role, content = msg.get("role"), msg.get("content")
                if role and content: chat_session.add_message(role, content)

        return npc_data, chat_session
    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        return None, None

def save_current_conversation( db, player_id: str, current_npc: Optional[Dict[str, Any]], chat_session, TerminalFormatter):
    if not current_npc or not chat_session: return
    npc_code = current_npc.get("code")
    if not npc_code or not player_id: return

    # Do not save Lyra's special hint consultations to her regular conversation log
    if current_npc.get('name', '').lower() == 'lyra' and chat_session.get_system_prompt() and "INFORMAZIONE CONTESTUALE AGGIUNTIVA" in chat_session.get_system_prompt():
        # print(f"{TerminalFormatter.DIM}Skipping save for Lyra's special consultation session.{TerminalFormatter.RESET}")
        return

    try:
        if chat_session.messages: # Only save if there are non-system messages
            history_to_save = chat_session.get_history() # Includes system prompt if set
            # Filter out system prompt before saving to DB, as it's dynamically generated on load
            history_to_save_filtered = [msg for msg in history_to_save if msg.get("role") != "system"]
            if history_to_save_filtered: # Only save if there's actual dialogue
                db.save_conversation(player_id, npc_code, history_to_save_filtered)
    except Exception as e: print(f"Err saving convo for {npc_code}: {e}")


def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
    name = npc_data.get('name', 'the figure'); role = npc_data.get('role', '')
    hooks_text = npc_data.get('dialogue_hooks', '');

    # Split hooks carefully, handling multi-line hook definitions if any
    # Assuming hooks are newline separated and each line starting with '-' is a hook item
    # Or if it's a single block of text, it's one hook.
    # The current parser in load.py seems to join them with \n if they are listed with -.
    hooks = []
    if isinstance(hooks_text, str):
        potential_hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()]
        # Filter further if some lines are not actual hooks but descriptions
        hooks = [h for h in potential_hooks if h.startswith('- ') or '"' in h or not any(h.lower().startswith(kw) for kw in ["(iniziale):", "(dopo le prove):"])]
        # A simpler way if hooks are always distinct lines:
        # hooks = [h.strip() for h in hooks_text.splitlines() if h.strip() and (h.startswith("- ") or '"' in h) ]
        # For Lyra, her hooks are complex and sectioned. Pick from the first section for an opener.
        if npc_data.get('name', '').lower() == 'lyra' and "(iniziale):" in hooks_text.lower():
            try:
                initial_section = hooks_text.lower().split("(iniziale):")[1].split("\n(")[0]
                hooks = [h.strip() for h in initial_section.splitlines() if h.strip().startswith('- ')]
                if hooks: hooks = [h[2:] for h in hooks] # Remove "- "
            except Exception:
                hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()] # fallback

    if hooks:
        chosen_hook = random.choice(hooks).replace("\"", "") # Clean quotes
        if not chosen_hook.startswith(("*")): return f"*{name} says,* \"{chosen_hook}\""
        else: return chosen_hook # If hook is already formatted like *...*
    elif role: return random.choice([f"*{name} the {role} regards you.* What do you want?", f"*{name}, the {role}, looks up as you approach.* Yes?"])
    else: return f"*{name} watches you expectantly.*"


def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TerminalFormatter):
    print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_data.get('name', 'NPC').upper()} IN {area_name.upper()} {TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.DIM}Type '/exit' to leave, '/help' for commands, '/hint' for guidance.{TerminalFormatter.RESET}")
    if npc_data.get('name','').lower() != 'lyra' or not ("INFORMAZIONE CONTESTUALE AGGIUNTIVA" in (npc_data.get('system_prompt_debug_field_if_needed',''))): # Avoid for Lyra hint mode start
        print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 60}{TerminalFormatter.RESET}\n")


def start_conversation_with_specific_npc(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    npc_data, new_session = load_and_prepare_conversation(
        db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TerminalFormatter )

    if npc_data and new_session:
        print_conversation_start_banner(npc_data, area_name, TerminalFormatter)
        # If there's no history, present an opening line from the NPC
        # This is only if the conversation is truly new (no loaded DB history)
        if not new_session.messages:
             opening_line = get_npc_opening_line(npc_data, TerminalFormatter)
             print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{npc_data['name']} > {TerminalFormatter.RESET}")
             print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
             new_session.add_message("assistant", opening_line) # Add to history so it's not lost and for LLM context
             print()
        elif new_session.messages: # If there is history, show the last thing said for context
            print(f"{TerminalFormatter.DIM}--- Continuing conversation with {npc_data['name']} ---{TerminalFormatter.RESET}")
            last_msg = new_session.messages[-1]
            role_display = "You" if last_msg['role'] == 'user' else npc_data.get('name', 'NPC')
            color = TerminalFormatter.GREEN if last_msg['role'] == 'user' else TerminalFormatter.MAGENTA
            print(f"{TerminalFormatter.BOLD}{color}{role_display} > {TerminalFormatter.RESET}")
            print(TerminalFormatter.format_terminal_text(last_msg['content']))
            print()

        return npc_data, new_session
    return None, None

def auto_start_default_npc_conversation(
    db, player_id: str, area_name: str, model_name: Optional[str],
    story: str, ChatSession_class, TerminalFormatter
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    default_npc_info = db.get_default_npc(area_name)
    if not default_npc_info:
        # This message is now printed by main_core if no NPC is auto-started.
        # print(f"{TerminalFormatter.DIM}No default NPC in '{area_name}'. Use /talk or /who.{TerminalFormatter.RESET}")
        return None, None
    default_npc_name = default_npc_info.get('name')
    if not default_npc_name: return None, None
    return start_conversation_with_specific_npc(
        db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TerminalFormatter )

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
    try: return db.list_npcs_by_area()
    except Exception as e: print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}"); return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
    if not all_known_npcs: return []
    return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)

