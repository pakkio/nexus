import random
import traceback
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable

try:
  from player_profile_manager import get_distilled_profile_insights_for_npc, get_default_player_profile
except ImportError:
  print("Warning (session_utils): player_profile_manager.py not found. Player profile insights for NPCs will be disabled.")
  def get_distilled_profile_insights_for_npc(player_profile, current_npc_data, story_context_summary, llm_wrapper_func, model_name, TF):
    return ""
  def get_default_player_profile():
    return {}

try:
  from llm_wrapper import llm_wrapper
except ImportError:
  print("Warning (session_utils): llm_wrapper.py not found. Profile distillation might fail if not provided explicitly.")
  def llm_wrapper(messages, model_name, stream, collect_stats, formatting_function=None, width=None):
    print("Warning: Fallback dummy llm_wrapper called in session_utils.")
    return "[LLM Fallback Response]", None

# FIXED: Color mapping for NPCs
def get_npc_color(npc_name: str, TerminalFormatter) -> str:
  """Returns a unique color for each NPC based on their name or role."""
  npc_name_lower = npc_name.lower()
  
  # Predefined mappings for important NPCs
  color_mappings = {
    'lyra': TerminalFormatter.BRIGHT_CYAN,      # Cyan for the wise oracle
    'syra': TerminalFormatter.DIM,              # Dim gray for the ancient spirit
    'elira': TerminalFormatter.GREEN,           # Green for the forest dweller
    'boros': TerminalFormatter.YELLOW,          # Yellow for the mountain warrior
    'jorin': TerminalFormatter.BRIGHT_YELLOW,   # Bright yellow for the tavern keeper
    'garin': TerminalFormatter.RED,             # Red for the blacksmith
    'mara': TerminalFormatter.CYAN,             # Cyan for the herbalist
    'cassian': TerminalFormatter.BLUE,          # Blue for the bureaucrat
    'irenna': TerminalFormatter.MAGENTA,        # Magenta for the resistance leader
    'theron': TerminalFormatter.BRIGHT_RED,     # Bright red for the antagonist
  }
  
  # Try exact match first
  if npc_name_lower in color_mappings:
    return color_mappings[npc_name_lower]
  
  # Fall back to hash-based color for unknown NPCs
  npc_hash = hashlib.md5(npc_name_lower.encode()).hexdigest()
  color_options = [
    TerminalFormatter.BRIGHT_GREEN,
    TerminalFormatter.BRIGHT_BLUE,
    TerminalFormatter.BRIGHT_MAGENTA,
    TerminalFormatter.BRIGHT_WHITE,
    TerminalFormatter.CYAN,
    TerminalFormatter.YELLOW,
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
    TerminalFormatter,
    player_id: Optional[str] = None,
    db=None,
    conversation_summary_for_lyra: Optional[str] = None,
    player_profile: Optional[Dict[str, Any]] = None,
    llm_wrapper_func: Optional[Callable] = None,
    llm_model_name: Optional[str] = None
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

  if veil: 
    prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto Importante): {veil}")

  effective_llm_wrapper_for_distill = llm_wrapper_func if llm_wrapper_func else llm_wrapper
  
  if player_profile and name.lower() != "lyra":
    if effective_llm_wrapper_for_distill and llm_model_name:
      distilled_insights = get_distilled_profile_insights_for_npc(
        player_profile,
        npc,
        story_context,
        effective_llm_wrapper_for_distill,
        llm_model_name,
        TF=TerminalFormatter
      )
      if distilled_insights:
        prompt_lines.append(f"\nSottile Consapevolezza del Cercatore (Adatta leggermente il tuo tono/approccio in base a questo): {distilled_insights}")
  elif player_profile and name.lower() == "lyra":
    profile_summary_parts_for_lyra = []
    core_traits = player_profile.get("core_traits")
    if isinstance(core_traits, dict) and core_traits:
      traits_summary = ", ".join([f"{k.capitalize()}: {v}/10" for k, v in core_traits.items()])
      profile_summary_parts_for_lyra.append(f"Tratti principali osservati: {traits_summary}.")
    elif isinstance(core_traits, list) and core_traits:
      profile_summary_parts_for_lyra.append(f"Tratti dominanti osservati: {', '.join(core_traits)}.")
    
    if player_profile.get("interaction_style_summary"):
      profile_summary_parts_for_lyra.append(f"Stile di interazione: {player_profile['interaction_style_summary']}.")
    if player_profile.get("veil_perception"):
      profile_summary_parts_for_lyra.append(f"Percezione del Velo: {player_profile['veil_perception'].replace('_', ' ')}.")
    if player_profile.get("decision_patterns"):
      patterns_str = ", ".join([p.replace('_', ' ') for p in player_profile.get("decision_patterns", [])])
      if patterns_str: 
        profile_summary_parts_for_lyra.append(f"Schemi decisionali notati: {patterns_str}.")
    
    if profile_summary_parts_for_lyra:
      prompt_lines.append(
        f"\nCONSAPEVOLEZZA DEL CERCATORE PER TE, LYRA (Usa queste informazioni per guidarlo meglio):\n"
        f"{' '.join(profile_summary_parts_for_lyra)}\n"
      )

  if conversation_summary_for_lyra and name.lower() == "lyra":
    prompt_lines.append(
      f"\nINFORMAZIONE CONTESTUALE AGGIUNTIVA PER TE, LYRA (per /hint):\n"
      f"Il Cercatore (giocatore) stava parlando con un altro NPC prima di consultarti. Ecco un riassunto di quella interazione:\n"
      f"\"{conversation_summary_for_lyra}\"\n"
      f"Usa questa informazione, insieme ai dettagli del giocatore e al suo profilo psicologico, per dare il tuo saggio consiglio."
    )

  prompt_lines.extend([
    f"\nContesto Globale del Mondo (Eldoria): {story_context}",
    "Parla in modo appropriato al setting fantasy e al tuo ruolo. Mantieni il personaggio.",
    "Risposte tendenzialmente concise (2-4 frasi), a meno che non venga richiesto di elaborare o la situazione lo richieda.",
    "Sii consapevole delle interazioni passate se riassunte sopra o nella cronologia della chat.",
    "",
    # FIXED: Make NPCs less generous and more realistic
    "COMPORTAMENTO IMPORTANTE: Sei un personaggio con le TUE motivazioni e obiettivi.",
    "Non dare oggetti o crediti al giocatore a meno che non abbia VERAMENTE guadagnato la tua fiducia o completato un compito significativo per te.",
    "Se il giocatore chiede direttamente oggetti o aiuto, puoi essere cauto, richiedere prove della sua affidabilità, o proporre uno scambio equo.",
    "Ricorda: sei un essere vivente con i tuoi bisogni, non un distributore automatico di ricompense.",
    "",
    "\nISTRUZIONE IMPORTANTE PER QUANDO DAI OGGETTI O CREDITI AL GIOCATORE:",
    "Se nella tua risposta decidi di dare uno o più oggetti/crediti al giocatore, DEVI includere una riga speciale ALLA FINE della tua risposta testuale.",
    "IMPORTANTE: Dai oggetti/crediti SOLO se il giocatore ha VERAMENTE meritato la tua generosità attraverso azioni concrete.",
    "Questa riga DEVE essere ESATTAMENTE nel seguente formato, senza alcuna variazione: ",
    "[GIVEN_ITEMS: NomeOggetto1, Quantità Credits, NomeOggetto2, ...]",
    "Per i crediti, usa il formato 'X Credits' (es. '100 Credits'). Separa i nomi degli oggetti/crediti con una virgola.",
    "Ogni nome di oggetto o quantità di crediti deve essere separato da una virgola.",
    "Se non dai nessun oggetto o credito, NON includere ASSOLUTAMENTE la riga [GIVEN_ITEMS:].",
    "Esempio di risposta CORRETTA in cui DAI oggetti e crediti DOPO che il giocatore ha completato un compito:",
    "NPC Dialogo: Eccellente! Hai dimostrato il tuo valore. Prendi questa Spada Leggendaria e questi 50 Credits per il disturbo.",
    "[GIVEN_ITEMS: Spada Leggendaria, 50 Credits]",
    "Esempio di risposta CORRETTA in cui NON DAI nulla perché il giocatore non ha fatto niente di speciale:",
    "NPC Dialogo: Hmm, non ti conosco abbastanza per fidarmi. Forse se mi portassi qualcosa che dimostra le tue intenzioni..."
  ])

  return "\n".join(prompt_lines)

def load_and_prepare_conversation(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str],
    story: str, ChatSession_class, TerminalFormatter,
    conversation_summary_for_lyra_context: Optional[str] = None,
    llm_wrapper_for_profile_distillation: Optional[Callable] = None
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

    player_profile = None
    if hasattr(db, 'load_player_profile'):
      player_profile = db.load_player_profile(player_id)
    if not player_profile:
      player_profile = get_default_player_profile()

    system_prompt = build_system_prompt(
      npc_data, story, TerminalFormatter,
      player_id=player_id, db=db,
      conversation_summary_for_lyra=conversation_summary_for_lyra_context if npc_name.lower() == "lyra" else None,
      player_profile=player_profile,
      llm_wrapper_func=llm_wrapper_for_profile_distillation,
      llm_model_name=model_name
    )

    chat_session = ChatSession_class(model_name=model_name)
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

    db_conversation_history = db.load_conversation(player_id, npc_code)
    if db_conversation_history:
      for msg in db_conversation_history:
        role, content = msg.get("role"), msg.get("content")
        if role and content is not None: 
          chat_session.add_message(role, content)

    return npc_data, chat_session
  except Exception as e:
    print(f"{TerminalFormatter.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TerminalFormatter.RESET}")
    traceback.print_exc()
    return None, None

def save_current_conversation(db, player_id: str, current_npc: Optional[Dict[str, Any]], chat_session, TerminalFormatter):
  if not current_npc or not chat_session: 
    return
  npc_code = current_npc.get("code")
  if not npc_code or not player_id: 
    return
  if current_npc.get('name', '').lower() == 'lyra' and chat_session.get_system_prompt() and "INFORMAZIONE CONTESTUALE AGGIUNTIVA" in chat_session.get_system_prompt():
    return
  try:
    if chat_session.messages:
      history_to_save = chat_session.get_history()
      history_to_save_filtered = [msg for msg in history_to_save if msg.get("role") != "system"]
      if history_to_save_filtered:
        db.save_conversation(player_id, npc_code, history_to_save_filtered)
  except Exception as e: 
    print(f"Err saving convo for {npc_code}: {e}")

def get_npc_opening_line(npc_data: Dict[str, Any], TerminalFormatter) -> str:
  name = npc_data.get('name', 'the figure')
  role = npc_data.get('role', '')
  hooks_text = npc_data.get('dialogue_hooks', '')
  
  hooks = []
  if isinstance(hooks_text, str):
    potential_hooks = [h.strip() for h in hooks_text.split('\n') if h.strip()]
    hooks = [h for h in potential_hooks if h.startswith('- ') or '"' in h or not any(h.lower().startswith(kw) for kw in ["(iniziale):", "(dopo le prove):"])]
    
    if npc_data.get('name', '').lower() == 'lyra' and "(iniziale):" in hooks_text.lower():
      try:
        initial_section = hooks_text.lower().split("(iniziale):")[1].split("\n(")[0]
        hooks_from_section = [h.strip() for h in initial_section.splitlines() if h.strip().startswith('- ')]
        if hooks_from_section: 
          hooks = [h[2:] for h in hooks_from_section]
      except Exception:
        hooks = [h.strip() for h in hooks_text.split('\n') if h.strip() and (h.startswith("- ") or '"' in h) ]

  if hooks:
    chosen_hook = random.choice(hooks).replace("\"", "")
    if not chosen_hook.startswith(("*")): 
      return f"*{name} says,* \"{chosen_hook}\""
    else: 
      return chosen_hook
  elif role: 
    return random.choice([
      f"*{name} the {role} regards you.* What do you want?", 
      f"*{name}, the {role}, looks up as you approach.* Yes?"
    ])
  else: 
    return f"*{name} watches you expectantly.*"

def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TerminalFormatter):
  npc_name = npc_data.get('name', 'NPC').upper()
  # FIXED: Use NPC-specific color for banner
  npc_color = get_npc_color(npc_data.get('name', 'NPC'), TerminalFormatter)
  
  print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} NOW TALKING TO {npc_color}{npc_name}{TerminalFormatter.RESET}{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} IN {area_name.upper()} {TerminalFormatter.RESET}")
  print(f"{TerminalFormatter.DIM}Type '/exit' to leave, '/help' for commands, '/hint' for guidance.{TerminalFormatter.RESET}")
  if npc_data.get('name','').lower() != 'lyra' or not ("INFORMAZIONE CONTESTUALE AGGIUNTIVA" in (npc_data.get('system_prompt_debug_field_if_needed',''))):
    print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 60}{TerminalFormatter.RESET}\n")

def start_conversation_with_specific_npc(
    db, player_id: str, area_name: str, npc_name: str,
    model_name: Optional[str], story: str, ChatSession_class, TerminalFormatter,
    llm_wrapper_for_profile_distillation: Optional[Callable] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
  npc_data, new_session = load_and_prepare_conversation(
    db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TerminalFormatter,
    llm_wrapper_for_profile_distillation=llm_wrapper_for_profile_distillation
  )
  
  if npc_data and new_session:
    print_conversation_start_banner(npc_data, area_name, TerminalFormatter)
    
    # FIXED: Use NPC-specific color for dialogue
    npc_color = get_npc_color(npc_data.get('name', 'NPC'), TerminalFormatter)
    
    if not new_session.messages:
      opening_line = get_npc_opening_line(npc_data, TerminalFormatter)
      print(f"{TerminalFormatter.BOLD}{npc_color}{npc_data['name']} > {TerminalFormatter.RESET}")
      print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
      new_session.add_message("assistant", opening_line)
      print()
    elif new_session.messages:
      print(f"{TerminalFormatter.DIM}--- Continuing conversation with {npc_data['name']} ---{TerminalFormatter.RESET}")
      last_msg = new_session.messages[-1]
      role_display = "You" if last_msg['role'] == 'user' else npc_data.get('name', 'NPC')
      color = TerminalFormatter.GREEN if last_msg['role'] == 'user' else npc_color
      print(f"{TerminalFormatter.BOLD}{color}{role_display} > {TerminalFormatter.RESET}")
      print(TerminalFormatter.format_terminal_text(last_msg['content']))
      print()
    
    return npc_data, new_session
  return None, None

def auto_start_default_npc_conversation(
    db, player_id: str, area_name: str, model_name: Optional[str],
    story: str, ChatSession_class, TerminalFormatter,
    llm_wrapper_for_profile_distillation: Optional[Callable] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
  default_npc_info = db.get_default_npc(area_name)
  if not default_npc_info:
    return None, None
  
  default_npc_name = default_npc_info.get('name')
  if not default_npc_name: 
    return None, None
  
  return start_conversation_with_specific_npc(
    db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TerminalFormatter,
    llm_wrapper_for_profile_distillation=llm_wrapper_for_profile_distillation
  )

def refresh_known_npcs_list(db, TerminalFormatter) -> List[Dict[str, Any]]:
  try: 
    return db.list_npcs_by_area()
  except Exception as e: 
    print(f"{TerminalFormatter.RED}Error refreshing NPC list: {e}{TerminalFormatter.RESET}")
    return []

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
  if not all_known_npcs: 
    return []
  return sorted(list(set(n.get('area', '').strip() for n in all_known_npcs if n.get('area', '').strip())), key=str.lower)
