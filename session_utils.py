import random
import traceback
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable

try:
  from player_profile_manager import get_distilled_profile_insights_for_npc, get_default_player_profile
except ImportError:
  print("Warning (session_utils): player_profile_manager.py not found. Player profile insights for NPCs will be disabled.")
  def get_distilled_profile_insights_for_npc(player_profile, current_npc_data, story_context_summary, llm_wrapper_func, model_name, TF, game_state): # Added game_state
    return ""
  def get_default_player_profile():
    return {}

try:
  from llm_wrapper import llm_wrapper
except ImportError:
  print("Warning (session_utils): llm_wrapper.py not found. Profile distillation might fail if not provided explicitly.")
  def llm_wrapper(messages, model_name, stream, collect_stats, formatting_function=None, width=None):
    return "[LLM Fallback Response]", None

try:
  from terminal_formatter import TerminalFormatter
  from chat_manager import ChatSession
except ImportError:
  print("Error (session_utils): terminal_formatter.py or chat_manager.py not found. Using basic fallbacks.")
  class TerminalFormatter:
    BRIGHT_CYAN = RED = YELLOW = GREEN = BLUE = MAGENTA = DIM = BOLD = RESET = ITALIC = ""
    BRIGHT_RED = BRIGHT_GREEN = BRIGHT_BLUE = BRIGHT_MAGENTA = BRIGHT_WHITE = ""
    BG_GREEN = BLACK = ""
    @staticmethod
    def get_terminal_width(): return 80
    @staticmethod
    def format_terminal_text(text, width=80): return text
  class ChatSession:
    def __init__(self, model_name: Optional[str] = None, use_formatting: bool = True): # Added use_formatting
        self.model_name = model_name
        self.messages: List[Dict[str, str]] = []
        self.system_prompt: Optional[str] = None
        self.current_player_hint: Optional[str] = None
    def set_system_prompt(self, prompt: str): self.system_prompt = prompt
    def get_system_prompt(self) -> Optional[str]: return self.system_prompt
    def set_player_hint(self, hint: Optional[str]): self.current_player_hint = hint
    def add_message(self, role: str, content: str):
        if role == "system": return
        if self.messages and self.messages[-1].get('role') == role and self.messages[-1].get('content') == content: return
        if content is None: return
        self.messages.append({"role": role, "content": content})
    def get_history(self) -> List[Dict[str, str]]:
        full_history = []
        if self.system_prompt: full_history.append({"role": "system", "content": self.system_prompt})
        full_history.extend(self.messages)
        return full_history
    def ask(self, prompt: str, npc_name_placeholder: str, stream: bool, collect_stats: bool): # Added placeholder
        # Dummy ask for fallback
        return f"Response from {npc_name_placeholder} to: {prompt}", None


def get_npc_color(npc_name: str, TF: type) -> str:
  npc_name_lower = npc_name.lower()
  # Predefined colors for key NPCs, including potential guides
  color_mappings = {
    'lyra': TF.BRIGHT_CYAN, 'syra': TF.DIM, 'elira': TF.GREEN,
    'boros': TF.YELLOW, 'jorin': TF.BRIGHT_YELLOW, 'garin': TF.RED,
    'mara': TF.CYAN, 'cassian': TF.BLUE, 'irenna': TF.MAGENTA,
    'theron': TF.BRIGHT_RED,
    # Add more key NPCs or roles if they become guides
    'default_guide': TF.BRIGHT_MAGENTA # A generic color for guides not in list
  }
  if npc_name_lower in color_mappings:
    return color_mappings[npc_name_lower]

  npc_hash = hashlib.md5(npc_name_lower.encode()).hexdigest()
  color_options = [
    TF.BRIGHT_GREEN, TF.BRIGHT_BLUE, TF.BRIGHT_WHITE, # Keep bright options
    TF.CYAN, TF.YELLOW, TF.MAGENTA, # Standard options
  ]
  color_index = int(npc_hash, 16) % len(color_options)
  return color_options[color_index]

def _format_storyboard_for_prompt(story_text: str, max_length: int = 300) -> str:
  if not isinstance(story_text, str): return "[Invalid Storyboard Data]"
  if len(story_text) > max_length:
    truncated = story_text[:max_length].rsplit(' ', 1)[0]
    return truncated + "..."
  return story_text

def build_system_prompt(
    npc: Dict[str, Any],
    story: str,
    TF: type,
    game_session_state: Dict[str, Any], # MODIFIED: Pass full game state
    conversation_summary_for_guide_context: Optional[str] = None, # MODIFIED: Renamed
    llm_wrapper_func_for_distill: Optional[Callable] = None # MODIFIED: Renamed for clarity
) -> str:
    player_id = game_session_state['player_id']
    player_profile = game_session_state.get('player_profile_cache')
    model_name_for_distill = game_session_state.get('profile_analysis_model_name') or game_session_state.get('model_name')
    wise_guide_npc_name_from_state = game_session_state.get('wise_guide_npc_name')

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
    ]
    if hooks:
        prompt_lines.append(f"Per ispirazione, considera questi stili/frasi chiave dal tuo personaggio: (alcune potrebbero essere contestuali, non usarle tutte alla cieca)\n{hooks[:300]}{'...' if len(hooks)>300 else ''}")
    if veil:
        prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto Importante): {veil}")

    # NPC awareness of player profile (distilled insights)
    # MODIFIED: Check if current NPC is NOT the wise guide before adding distilled profile for regular NPCs
    if player_profile and name.lower() != (wise_guide_npc_name_from_state or "").lower():
        if llm_wrapper_func_for_distill and model_name_for_distill:
            distilled_insights = get_distilled_profile_insights_for_npc(
                player_profile, npc, story_context,
                llm_wrapper_func_for_distill, model_name_for_distill, TF, game_session_state
            )
            if distilled_insights:
                prompt_lines.append(f"\nSottile Consapevolezza del Cercatore (Adatta leggermente il tuo tono/approccio in base a questo): {distilled_insights}")

    # Special context for the Wise Guide NPC when in hint mode
    # MODIFIED: Check if current NPC IS the wise guide
    if name.lower() == (wise_guide_npc_name_from_state or "").lower():
        if player_profile: # Wise guide gets more direct profile info
            profile_summary_parts_for_guide = []
            core_traits = player_profile.get("core_traits")
            if isinstance(core_traits, dict) and core_traits:
                traits_summary = ", ".join([f"{k.capitalize()}: {v}/10" for k,v in core_traits.items()])
                profile_summary_parts_for_guide.append(f"Tratti principali osservati nel Cercatore: {traits_summary}.")
            # Add more profile aspects for the guide if needed (e.g., recent patterns)
            if profile_summary_parts_for_guide:
                prompt_lines.append(
                    f"\nCONSAPEVOLEZZA DEL CERCATORE PER TE, {name.upper()} (Usa queste informazioni per guidarlo meglio):\n"
                    f"{' '.join(profile_summary_parts_for_guide)}\n"
                )

        if conversation_summary_for_guide_context: # This is passed only when starting hint session
            prompt_lines.append(
                f"\nINFORMAZIONE CONTESTUALE AGGIUNTIVA PER TE, {name.upper()} (per /hint):\n"
                f"Il Cercatore (giocatore) stava parlando con un altro NPC prima di consultarti. Ecco un riassunto di quella interazione:\n"
                f"\"{conversation_summary_for_guide_context}\"\n"
                f"Usa questa informazione, insieme ai dettagli del giocatore e al suo profilo psicologico, per dare il tuo saggio consiglio."
            )

    prompt_lines.extend([
        f"\nContesto Globale del Mondo (Eldoria): {story_context}",
        "**LINGUA**: Parla SEMPRE in INGLESE a meno che il player indichi una lingua diversa. " 
        # ... (rest of the standard instructions remain same) ...
        "Parla in modo appropriato al setting fantasy e al tuo ruolo. Mantieni il personaggio.",
        "Sii consapevole delle interazioni passate se riassunte sopra o nella cronologia della chat.",
        "COMPORTAMENTO IMPORTANTE: Sei un personaggio con le TUE motivazioni e obiettivi.",
        "Non dare oggetti o crediti al giocatore a meno che non abbia VERAMENTE guadagnato la tua fiducia o completato un compito significativo per te.",
        "Se il giocatore chiede direttamente oggetti o aiuto, puoi essere cauto, richiedere prove della sua affidabilità, o proporre uno scambio equo.",
        "Ricorda: sei un essere vivente con i tuoi bisogni, non un distributore automatico di ricompense.",
        "\nISTRUZIONE IMPORTANTE PER QUANDO DAI OGGETTI O CREDITI AL GIOCATORE:",
        "Se nella tua risposta decidi di dare uno o più oggetti/crediti al giocatore, DEVI includere una riga speciale ALLA FINE della tua risposta testuale.",
        "IMPORTANTE: Dai oggetti/crediti SOLO se il giocatore ha VERAMENTE meritato la tua generosità attraverso azioni concrete.",
        "Questa riga DEVE essere ESATTAMENTE nel seguente formato, senza alcuna variazione: ",
        "[GIVEN_ITEMS: NomeOggetto1, Quantità Credits, NomeOggetto2, ...]",
        "Per i crediti, usa il formato 'X Credits' per dare crediti o '-X Credits' per farli pagare (es. '100 Credits' per dare, '-50 Credits' per far pagare). Separa i nomi degli oggetti/crediti con una virgola.",
        "Ogni nome di oggetto o quantità di crediti deve essere separato da una virgola.",
        "Se non dai nessun oggetto o credito, NON includere ASSOLUTAMENTE la riga [GIVEN_ITEMS:].",
        "Esempio di risposta CORRETTA in cui DAI oggetti e crediti DOPO che il giocatore ha completato un compito:",
        "NPC Dialogo: Eccellente! Hai dimostrato il tuo valore. Prendi questa Spada Leggendaria e questi 50 Credits per il disturbo.",
        "[GIVEN_ITEMS: Spada Leggendaria, 50 Credits]",
        "Esempio di risposta CORRETTA in cui VENDI un oggetto al giocatore:",
        "NPC Dialogo: Certo, posso venderti questa Pozione di Cura per 25 crediti. Ecco qui.",
        "[GIVEN_ITEMS: Pozione di Cura, -25 Credits]",
        "Esempio di risposta CORRETTA in cui NON DAI nulla perché il giocatore non ha fatto niente di speciale:",
        "NPC Dialogo: Hmm, non ti conosco abbastanza per fidarmi. Forse se mi portassi qualcosa che dimostra le tue intenzioni..."
    ])
    return "\n".join(prompt_lines)


def load_and_prepare_conversation(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str],
    story: str, ChatSession_class: type, TF_class: type,
    game_session_state: Dict[str, Any], # MODIFIED: Pass full game state
    conversation_summary_for_guide_context: Optional[str] = None, # MODIFIED: Renamed
    llm_wrapper_for_profile_distillation_func: Optional[Callable] = None, # MODIFIED: Renamed
    model_type: str = "dialogue" # NEW: Model type for stats tracking
) -> Tuple[Optional[Dict[str, Any]], Optional[ChatSession]]:
    try:
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"{TF_class.RED}❌ NPC '{npc_name}' not found in '{area_name}'.{TF_class.RESET}")
            return None, None

        npc_code = npc_data.get("code")
        if not npc_code:
            print(f"{TF_class.RED}❌ NPC '{npc_name}' missing 'code'.{TF_class.RESET}")
            return None, None

        # System prompt is now built using game_session_state
        system_prompt = build_system_prompt(
            npc_data, story, TF_class,
            game_session_state=game_session_state, # Pass state
            conversation_summary_for_guide_context=conversation_summary_for_guide_context,
            llm_wrapper_func_for_distill=llm_wrapper_for_profile_distillation_func
        )

        chat_session = ChatSession_class(model_name=model_name, model_type=model_type)
        chat_session.set_system_prompt(system_prompt)

        player_hint_from_data = npc_data.get('playerhint')
        if not player_hint_from_data:
            npc_goal = npc_data.get('goal')
            npc_needed = npc_data.get('needed_object')
            if npc_goal:
                player_hint_from_data = f"Help them with: '{npc_goal}'."
                if npc_needed:
                    player_hint_from_data += f" They need '{npc_needed}'."
        chat_session.set_player_hint(player_hint_from_data)

        # Load conversation history
        db_conversation_history = db.load_conversation(player_id, npc_code)
        if db_conversation_history:
            # print(f"{TF_class.DIM}[DEBUG] Loaded {len(db_conversation_history)} messages from DB for {npc_name}{TF_class.RESET}") # Verbose
            for msg in db_conversation_history:
                role, content = msg.get("role"), msg.get("content")
                if role and content is not None:
                    chat_session.add_message(role, content)

            # Handle conversation resumption
            if chat_session.messages:
                last_loaded_message = chat_session.messages[-1]
                if last_loaded_message.get("role") == "user" and \
                   last_loaded_message.get("content", "").startswith("[CONVERSATION_BREAK:"):
                    # print(f"{TF_class.DIM}[DEBUG] Found BREAK marker for {npc_name}. Adding RESUME.{TF_class.RESET}") # Verbose
                    resume_marker = "[CONVERSATION_RESUMED: Player returned after a break. Acknowledge the passage of time appropriately.]"
                    chat_session.add_message("user", resume_marker)
        # else:
            # print(f"{TF_class.DIM}[DEBUG] No conversation history found for {npc_name}{TF_class.RESET}") # Verbose

        return npc_data, chat_session
    except Exception as e:
        print(f"{TF_class.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TF_class.RESET}")
        traceback.print_exc()
        return None, None


def save_current_conversation(db, player_id: str, current_npc: Optional[Dict[str, Any]],
                              chat_session: Optional[ChatSession], TF_class: type,
                              game_session_state: Dict[str, Any]): # MODIFIED: Added game_session_state
    if not current_npc or not chat_session:
        return

    npc_code = current_npc.get("code")
    if not npc_code or not player_id:
        return

    # MODIFIED: Do not save conversation if it's with the wise guide AND in hint mode
    is_guide_conversation_in_hint_mode = False
    if game_session_state.get('in_hint_mode', False):
        wise_guide_name = game_session_state.get('wise_guide_npc_name')
        if wise_guide_name and current_npc.get('name', '').lower() == wise_guide_name.lower():
            is_guide_conversation_in_hint_mode = True

    if is_guide_conversation_in_hint_mode:
        # print(f"{TF_class.DIM}[DEBUG] Skipping save for hint consultation with {current_npc.get('name')}.{TF_class.RESET}") # Verbose
        return

    try:
        if chat_session.messages:
            break_marker = "[CONVERSATION_BREAK: Player left the conversation]"
            # Avoid adding duplicate break markers if one is already last
            if not (chat_session.messages[-1].get("role") == "user" and chat_session.messages[-1].get("content") == break_marker):
                chat_session.add_message("user", break_marker)
                # print(f"{TF_class.DIM}[DEBUG] Added BREAK marker to session for {current_npc.get('name')}{TF_class.RESET}") # Verbose

            history_to_save_to_db = chat_session.messages
            # print(f"{TF_class.DIM}[DEBUG] Saving {len(history_to_save_to_db)} messages to DB for {npc_code}{TF_class.RESET}") # Verbose
            db.save_conversation(player_id, npc_code, history_to_save_to_db)
        # else:
            # print(f"{TF_class.DIM}[DEBUG] No messages in session for {current_npc.get('name')}, skipping save.{TF_class.RESET}") # Verbose
    except Exception as e:
        print(f"{TF_class.YELLOW}Warning: Error saving conversation for NPC {npc_code}: {e}{TF_class.RESET}")
        traceback.print_exc()


def get_npc_opening_line(npc_data: Dict[str, Any], TF_class: type, game_session_state: Dict[str, Any]) -> str: # MODIFIED: Added game_session_state
    name = npc_data.get('name', 'the figure')
    role = npc_data.get('role', '')
    hooks_text = npc_data.get('dialogue_hooks', '')
    candidate_hooks = []

    # MODIFIED: Check if this NPC is the wise guide and if we are in hint mode
    is_wise_guide_consultation = False
    if game_session_state.get('in_hint_mode', False):
        wise_guide_name = game_session_state.get('wise_guide_npc_name')
        if wise_guide_name and name.lower() == wise_guide_name.lower():
            is_wise_guide_consultation = True

    if is_wise_guide_consultation:
        # The actual "question" to the guide is generated by build_initial_guide_prompt
        # and sent via chat_session.ask(). So, no specific "opening line" here from hooks.
        # The guide's first response comes from the LLM.
        # However, the banner is printed before this.
        # This function is called if new_session.messages is empty.
        # For hint mode, the initial prompt IS the first user message.
        # So this function might not even be called if `ask` is done first.
        # If it IS called, it means the guide session is truly new and no prompt sent yet.
        # Let's return a generic "Guide is waiting" type message, or rely on the banner.
        return f"*{name} awaits your query, Seeker.*"


    # Regular NPC opening line logic
    # (Copied existing Lyra-specific hook parsing, can be generalized if needed)
    if name.lower() == 'lyra' and not is_wise_guide_consultation: # Original Lyra behavior if she's not the active guide for a hint
        in_initial_section = False
        temp_initial_hooks = []
        for line_iter in hooks_text.splitlines():
            line_stripped_lower = line_iter.strip().lower()
            if line_stripped_lower.startswith("(iniziale):"): in_initial_section = True; continue
            if in_initial_section and line_stripped_lower.startswith("(") and line_stripped_lower != "(iniziale):": in_initial_section = False; break
            if in_initial_section:
                line_trimmed_for_hook = line_iter.strip()
                if line_trimmed_for_hook.startswith('- '):
                    actual_hook_text = line_trimmed_for_hook[2:].strip().replace("\"", "")
                    if actual_hook_text: temp_initial_hooks.append(actual_hook_text)
        if temp_initial_hooks: candidate_hooks = temp_initial_hooks

    if not candidate_hooks and isinstance(hooks_text, str): # General hook parsing
        potential_hooks_general = [h.strip() for h in hooks_text.split('\n') if h.strip()]
        lines_starting_with_dash = [
            h[2:].strip().replace("\"", "") for h in potential_hooks_general if h.startswith('- ')
        ]
        if lines_starting_with_dash:
            candidate_hooks = lines_starting_with_dash
        else:
            lines_with_quotes_not_headers = [
                h.strip().replace("\"", "") for h in potential_hooks_general
                if ('"' in h and not any(h.lower().startswith(kw) for kw in ["(iniziale):", "(dopo", "(durante", "(verso"]))
            ]
            if lines_with_quotes_not_headers: candidate_hooks = lines_with_quotes_not_headers

    if candidate_hooks:
        chosen_hook = random.choice(candidate_hooks)
        return f"*{name} says,* \"{chosen_hook.strip()}\"" if not chosen_hook.startswith("*") else chosen_hook.strip()
    elif role:
        return random.choice([f"*{name} the {role} regards you.* What do you want?", f"*{name}, the {role}, looks up as you approach.* Yes?"])
    else:
        return f"*{name} watches you expectantly.*"


def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TF_class: type, game_session_state: Dict[str, Any]): # MODIFIED: Added game_session_state
    npc_name_display = npc_data.get('name', 'NPC').upper()
    npc_color_code = get_npc_color(npc_data.get('name', 'NPC'), TF_class)

    header_text = f" NOW TALKING TO {npc_color_code}{npc_name_display}{TF_class.RESET}{TF_class.BG_GREEN}{TF_class.BLACK}{TF_class.BOLD} IN {area_name.upper()} "

    # MODIFIED: Special banner for hint mode
    is_guide_consultation = False
    if game_session_state.get('in_hint_mode', False):
        wise_guide_name = game_session_state.get('wise_guide_npc_name')
        if wise_guide_name and npc_data.get('name', '').lower() == wise_guide_name.lower():
            is_guide_consultation = True
            guide_banner_name = wise_guide_name.upper()
            header_text = f" CONSULTING WITH {npc_color_code}{guide_banner_name}{TF_class.RESET}{TF_class.BG_BLUE}{TF_class.BRIGHT_WHITE}{TF_class.BOLD} (WISE GUIDE) "
            banner_line1 = f"{TF_class.BG_BLUE}{TF_class.BRIGHT_WHITE}{TF_class.BOLD}{header_text}{TF_class.RESET}"
            print(f"\n{banner_line1}")
            print(f"{TF_class.DIM}Ask your questions. Type '/endhint' to return to your previous conversation.{TF_class.RESET}")
            # No further separator for guide consultation to make it feel immediate
            return # Skip regular banner for guide

    banner_line1 = f"{TF_class.BG_GREEN}{TF_class.BLACK}{TF_class.BOLD}{header_text}{TF_class.RESET}"
    print(f"\n{banner_line1}")
    print(f"{TF_class.DIM}Type '/exit' to leave, '/help' for commands. Use '/hint' for guidance from {game_session_state.get('wise_guide_npc_name', 'the Guide')}.{TF_class.RESET}")
    print(f"{TF_class.BRIGHT_CYAN}{'=' * 60}{TF_class.RESET}\n")


def start_conversation_with_specific_npc(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class: type, TF_class: type,
    game_session_state: Dict[str, Any], # MODIFIED: Pass full game state
    conversation_summary_for_guide_context: Optional[str] = None, # MODIFIED: Renamed
    llm_wrapper_for_profile_distillation: Optional[Callable] = None,
    model_type: str = "dialogue" # NEW: Model type for stats tracking
) -> Tuple[Optional[Dict[str, Any]], Optional[ChatSession]]:

    npc_data, new_session = load_and_prepare_conversation(
        db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TF_class,
        game_session_state=game_session_state, # Pass state
        conversation_summary_for_guide_context=conversation_summary_for_guide_context,
        llm_wrapper_for_profile_distillation_func=llm_wrapper_for_profile_distillation, # Pass renamed
        model_type=model_type # NEW: Pass model type
    )

    if npc_data and new_session:
        print_conversation_start_banner(npc_data, area_name, TF_class, game_session_state) # MODIFIED: Pass state
        npc_color_code = get_npc_color(npc_data.get('name', 'NPC'), TF_class)

        # MODIFIED: Opening line logic is now conditional on not being in hint mode's initial prompt
        # For hint mode, the initial prompt IS the first "user" message, and the guide's response is awaited.
        # For regular NPCs, if no history, they give an opening line.
        is_guide_consultation_initial_prompt = False
        if game_session_state.get('in_hint_mode', False):
            wise_guide_name = game_session_state.get('wise_guide_npc_name')
            if wise_guide_name and npc_name.lower() == wise_guide_name.lower() and not new_session.messages:
                is_guide_consultation_initial_prompt = True # This state means the initial prompt is about to be sent by handle_hint

        if not new_session.messages and not is_guide_consultation_initial_prompt:
            opening_line = get_npc_opening_line(npc_data, TF_class, game_session_state) # MODIFIED: Pass state
            print(f"{TF_class.BOLD}{npc_color_code}{npc_data['name']} > {TF_class.RESET}")
            print(TF_class.format_terminal_text(opening_line, width=TF_class.get_terminal_width()))
            new_session.add_message("assistant", opening_line)
            print()
        elif new_session.messages: # If there's history
            # print(f"{TF_class.DIM}--- Continuing conversation with {npc_data['name']} ---{TF_class.RESET}") # Verbose
            last_msg = new_session.messages[-1]
            # Avoid reprinting the resume marker if it's the last message
            if not (last_msg['role'] == 'user' and last_msg['content'].startswith("[CONVERSATION_RESUMED:")):
                role_display = "You" if last_msg['role'] == 'user' else npc_data.get('name', 'NPC')
                color_to_use = TF_class.GREEN if last_msg['role'] == 'user' else npc_color_code
                print(f"{TF_class.BOLD}{color_to_use}{role_display} > {TF_class.RESET}")
                print(TF_class.format_terminal_text(last_msg['content']))
                print()
        return npc_data, new_session
    return None, None


def auto_start_default_npc_conversation(
    db, player_id: str, area_name: str, model_name: Optional[str],
    story: str, ChatSession_class: type, TF_class: type,
    game_session_state: Dict[str, Any], # MODIFIED: Pass full state
    llm_wrapper_for_profile_distillation: Optional[Callable] = None,
    model_type: str = "dialogue" # NEW: Model type for stats tracking
) -> Tuple[Optional[Dict[str, Any]], Optional[ChatSession]]:
    default_npc_info = db.get_default_npc(area_name)
    if not default_npc_info:
        return None, None
    default_npc_name = default_npc_info.get('name')
    if not default_npc_name:
        return None, None

    return start_conversation_with_specific_npc(
        db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TF_class,
        game_session_state=game_session_state, # Pass state
        llm_wrapper_for_profile_distillation=llm_wrapper_for_profile_distillation,
        model_type=model_type # NEW: Pass model type
    )

def refresh_known_npcs_list(db, TF_class: type) -> List[Dict[str, Any]]:
  try:
    return db.list_npcs_by_area()
  except Exception as e:
    print(f"{TF_class.RED}Error refreshing NPC list: {e}{TF_class.RESET}")
    return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
  if not all_known_npcs:
    return []
  return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)
