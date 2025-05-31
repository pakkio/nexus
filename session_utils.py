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

try:
  from terminal_formatter import TerminalFormatter
  from chat_manager import ChatSession
except ImportError:
  class TerminalFormatter:
    BRIGHT_CYAN = RED = YELLOW = GREEN = BLUE = MAGENTA = DIM = BOLD = RESET = ITALIC = ""
    BRIGHT_RED = BRIGHT_GREEN = BRIGHT_BLUE = BRIGHT_MAGENTA = BRIGHT_WHITE = ""
    BG_GREEN = BLACK = ""
    @staticmethod
    def get_terminal_width(): return 80
    @staticmethod
    def format_terminal_text(text, width=80): return text
  
  class ChatSession:
    def __init__(self, model_name): self.model_name = model_name; self.messages = []; self.system_prompt = None; self.player_hint = None
    def set_system_prompt(self, p): self.system_prompt = p
    def get_system_prompt(self): return self.system_prompt
    def set_player_hint(self, h): self.player_hint = h
    def add_message(self, r, c): self.messages.append({'role':r, 'content':c})
    def get_history(self): return ([{'role':'system', 'content':self.system_prompt}] if self.system_prompt else []) + self.messages

def get_npc_color(npc_name: str, TF: type) -> str: # TF è passato come tipo/classe
  """Returns a unique color for each NPC based on their name or role."""
  npc_name_lower = npc_name.lower()
  color_mappings = {
    'lyra': TF.BRIGHT_CYAN,
    'syra': TF.DIM,
    'elira': TF.GREEN,
    'boros': TF.YELLOW,
    'jorin': TF.BRIGHT_YELLOW,
    'garin': TF.RED,
    'mara': TF.CYAN,
    'cassian': TF.BLUE,
    'irenna': TF.MAGENTA,
    'theron': TF.BRIGHT_RED,
  }
  
  if npc_name_lower in color_mappings:
    return color_mappings[npc_name_lower]
  
  npc_hash = hashlib.md5(npc_name_lower.encode()).hexdigest()
  color_options = [
    TF.BRIGHT_GREEN, TF.BRIGHT_BLUE, TF.BRIGHT_MAGENTA,
    TF.BRIGHT_WHITE, TF.CYAN, TF.YELLOW,
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
  TF: type, # Passa TerminalFormatter come tipo/classe
  player_id: Optional[str] = None,
  db=None, # db può essere None se non usato per profili qui
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
  hooks = npc.get('dialogue_hooks', 'Standard dialogue') # Questo viene direttamente dal parser
  veil = npc.get('veil_connection', '')
  
  prompt_lines = [
    f"Sei {name}, un/una {role} nell'area di {area} nel mondo di Eldoria.",
    f"Motivazione: '{motivation}'. Obiettivo (cosa TU, l'NPC, vuoi ottenere): '{goal}'.",
    f"V.O. (Guida per l'azione del giocatore per aiutarti): \"{player_hint_for_npc_context}\"",
  ]
  
  if hooks: # Aggiungiamo una nota che ci sono dei ganci per l'ispirazione
    prompt_lines.append(f"Per ispirazione, considera questi stili/frasi chiave dal tuo personaggio: (alcune potrebbero essere contestuali, non usarle tutte alla cieca)\n{hooks[:300]}{'...' if len(hooks)>300 else ''}")
  
  if veil:
    prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto Importante): {veil}")
  
  effective_llm_wrapper_for_distill = llm_wrapper_func if llm_wrapper_func else llm_wrapper
  if player_profile and name.lower() != "lyra":
    if effective_llm_wrapper_for_distill and llm_model_name:
      distilled_insights = get_distilled_profile_insights_for_npc(
        player_profile, npc, story_context,
        effective_llm_wrapper_for_distill, llm_model_name, TF=TF
      )
      if distilled_insights:
        prompt_lines.append(f"\nSottile Consapevolezza del Cercatore (Adatta leggermente il tuo tono/approccio in base a questo): {distilled_insights}")
  
  elif player_profile and name.lower() == "lyra":
    profile_summary_parts_for_lyra = []
    core_traits = player_profile.get("core_traits")
    if isinstance(core_traits, dict) and core_traits:
      traits_summary = ", ".join([f"{k.capitalize()}: {v}/10" for k, v in core_traits.items()])
      profile_summary_parts_for_lyra.append(f"Tratti principali osservati: {traits_summary}.")
    
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
    "**LINGUA**: Parla SEMPRE in italiano se gli hook sono in inglese traducili. Se gli stili/frasi di ispirazione contengono inglese, TRADUCILI e adattali al tuo personaggio.",
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
  story: str, ChatSession_class: type, TF_class: type, # Passa le classi
  conversation_summary_for_lyra_context: Optional[str] = None,
  llm_wrapper_for_profile_distillation: Optional[Callable] = None
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
    
    player_profile = None
    if hasattr(db, 'load_player_profile'):
      player_profile = db.load_player_profile(player_id)
    if not player_profile: # Assicura che player_profile sia un dict
      player_profile = get_default_player_profile()
    
    system_prompt = build_system_prompt(
      npc_data, story, TF_class,
      player_id=player_id, db=db,
      conversation_summary_for_lyra=conversation_summary_for_lyra_context if npc_name.lower() == "lyra" else None,
      player_profile=player_profile,
      llm_wrapper_func=llm_wrapper_for_profile_distillation,
      llm_model_name=model_name
    )
    
    chat_session = ChatSession_class(model_name=model_name)
    chat_session.set_system_prompt(system_prompt)
    
    player_hint_from_data = npc_data.get('playerhint')
    if not player_hint_from_data: # Costruisci un hint di fallback se mancante
      npc_goal = npc_data.get('goal')
      npc_needed = npc_data.get('needed_object')
      if npc_goal:
        player_hint_from_data = f"Help them with: '{npc_goal}'."
        if npc_needed:
          player_hint_from_data += f" They need '{npc_needed}'."
    
    chat_session.set_player_hint(player_hint_from_data)
    
    # FIXED: Load conversation and handle break/resume markers properly
    db_conversation_history = db.load_conversation(player_id, npc_code)
    if db_conversation_history:
      conversation_was_interrupted = False
      
      # DEBUG: Print what we loaded from DB
      print(f"{TF_class.DIM}[DEBUG] Loaded {len(db_conversation_history)} messages from DB for {npc_name}{TF_class.RESET}")
      
      for msg in db_conversation_history:
        role, content = msg.get("role"), msg.get("content")
        if role and content is not None:
          # Check for break marker - KEEP it in history for visibility
          if role == "system" and content and "[CONVERSATION_BREAK:" in content:
            conversation_was_interrupted = True
            print(f"{TF_class.DIM}[DEBUG] Found BREAK marker: {content[:50]}...{TF_class.RESET}")
            chat_session.add_message(role, content)  # FIXED: Keep the break marker
          else:
            chat_session.add_message(role, content)
      
      # Add resume marker if conversation was interrupted
      if conversation_was_interrupted:
        resume_marker = "[CONVERSATION_RESUMED: Player returned after a break. Acknowledge the passage of time appropriately.]"
        chat_session.add_message("system", resume_marker)
        print(f"{TF_class.DIM}[DEBUG] Added RESUME marker{TF_class.RESET}")
      else:
        print(f"{TF_class.DIM}[DEBUG] No interruption detected{TF_class.RESET}")
    else:
      print(f"{TF_class.DIM}[DEBUG] No conversation history found for {npc_name}{TF_class.RESET}")
    
    return npc_data, chat_session
  except Exception as e:
    print(f"{TF_class.RED}❌ Error in load_and_prepare_conversation for {npc_name}: {e}{TF_class.RESET}")
    traceback.print_exc()
    return None, None

def save_current_conversation(db, player_id: str, current_npc: Optional[Dict[str, Any]], chat_session: Optional[ChatSession], TF_class: type):
  """
  FIXED: Save conversation with proper break markers that persist through save/load cycle.
  """
  if not current_npc or not chat_session:
    return
  
  npc_code = current_npc.get("code")
  if not npc_code or not player_id:
    return
  
  # Skip saving for special Lyra hint consultations
  if current_npc.get('name', '').lower() == 'lyra':
    system_p = chat_session.get_system_prompt()
    if system_p and "INFORMAZIONE CONTESTUALE AGGIUNTIVA" in system_p:
      return
  
  try:
    if chat_session.messages: # Save only if there are actual messages beyond system prompt
      # Add break marker to the session
      break_marker = "[CONVERSATION_BREAK: Player left the conversation]"
      chat_session.add_message("system", break_marker)
      print(f"{TF_class.DIM}[DEBUG] Added BREAK marker to session for {current_npc.get('name')}{TF_class.RESET}")
      
      # Get history including the break marker
      history_to_save = chat_session.get_history() # This includes the system prompt
      
      # FIXED: Filter out system prompts but KEEP conversation markers
      history_to_save_filtered = []
      for msg in history_to_save:
        if msg.get("role") == "system":
          content = msg.get("content", "")
          # Keep only conversation control markers, not the main system prompt
          if ("[CONVERSATION_BREAK:" in content or 
              "[CONVERSATION_RESUMED:" in content):
            history_to_save_filtered.append(msg)
            print(f"{TF_class.DIM}[DEBUG] Keeping marker: {content[:50]}...{TF_class.RESET}")
          # Skip the main system prompt and other system messages
        else:
          # Keep all user and assistant messages
          history_to_save_filtered.append(msg)
      
      print(f"{TF_class.DIM}[DEBUG] Saving {len(history_to_save_filtered)} messages to DB{TF_class.RESET}")
      
      if history_to_save_filtered: # Save only if there's actual user/assistant history
        db.save_conversation(player_id, npc_code, history_to_save_filtered)
  except Exception as e:
    print(f"{TF_class.YELLOW}Warning: Error saving conversation for NPC {npc_code}: {e}{TF_class.RESET}")


def get_npc_opening_line(npc_data: Dict[str, Any], TF_class: type) -> str:
  name = npc_data.get('name', 'the figure')
  role = npc_data.get('role', '')
  hooks_text = npc_data.get('dialogue_hooks', '')
  
  candidate_hooks = []
  
  # Special handling for Lyra's initial hooks
  if npc_data.get('name', '').lower() == 'lyra':
    in_initial_section = False
    temp_initial_hooks = []
    for line_iter in hooks_text.splitlines():
      line_stripped_lower = line_iter.strip().lower()
      if line_stripped_lower.startswith("(iniziale):"):
        in_initial_section = True
        continue
      if in_initial_section and line_stripped_lower.startswith("(") and line_stripped_lower != "(iniziale):":
        in_initial_section = False
        break
      if in_initial_section:
        line_trimmed_for_hook = line_iter.strip()
        if line_trimmed_for_hook.startswith('- '):
          actual_hook_text = line_trimmed_for_hook[2:].strip().replace("\"", "")
          if actual_hook_text:
            temp_initial_hooks.append(actual_hook_text)
    
    if temp_initial_hooks:
      candidate_hooks = temp_initial_hooks # Use these if found
  
  # Fallback to general hooks if no specific ones found
  if not candidate_hooks and isinstance(hooks_text, str):
    potential_hooks_general = [h.strip() for h in hooks_text.split('\n') if h.strip()]
    lines_starting_with_dash = [
      h[2:].strip().replace("\"", "") for h in potential_hooks_general
      if h.startswith('- ')
    ]
    if lines_starting_with_dash:
      candidate_hooks = lines_starting_with_dash
    else:
      lines_with_quotes_not_headers = [
        h.strip().replace("\"", "") for h in potential_hooks_general
        if ('"' in h and not any(h.lower().startswith(kw) for kw in ["(iniziale):", "(dopo le prove):", "(durante la ricerca", "(verso il rituale):"]))
      ]
      if lines_with_quotes_not_headers:
        candidate_hooks = lines_with_quotes_not_headers
  
  if candidate_hooks:
    chosen_hook = random.choice(candidate_hooks)
    if not chosen_hook.startswith(("*")):
      return f"*{name} says,* \"{chosen_hook.strip()}\""
    else:
      return chosen_hook.strip()
  elif role:
    return random.choice([
      f"*{name} the {role} regards you.* What do you want?",
      f"*{name}, the {role}, looks up as you approach.* Yes?"
    ])
  else:
    return f"*{name} watches you expectantly.*"

def print_conversation_start_banner(npc_data: Dict[str, Any], area_name: str, TF_class: type):
  npc_name_display = npc_data.get('name', 'NPC').upper()
  npc_color_code = get_npc_color(npc_data.get('name', 'NPC'), TF_class)
  
  banner_line1_content = f" NOW TALKING TO {npc_color_code}{npc_name_display}{TF_class.RESET}{TF_class.BG_GREEN}{TF_class.BLACK}{TF_class.BOLD} IN {area_name.upper()} "
  banner_line1 = f"{TF_class.BG_GREEN}{TF_class.BLACK}{TF_class.BOLD}{banner_line1_content}{TF_class.RESET}"
  
  print(f"\n{banner_line1}")
  print(f"{TF_class.DIM}Type '/exit' to leave, '/help' for commands, '/hint' for guidance.{TF_class.RESET}")
  
  is_lyra_hint_consultation = False
  if npc_data.get('name','').lower() == 'lyra':
    pass
  
  if not is_lyra_hint_consultation: # Print separator if not special Lyra consultation
    print(f"{TF_class.BRIGHT_CYAN}{'=' * 60}{TF_class.RESET}\n")

def start_conversation_with_specific_npc(
  db, player_id: str, area_name: str, npc_name: str,
  model_name: Optional[str], story: str, ChatSession_class: type, TF_class: type,
  llm_wrapper_for_profile_distillation: Optional[Callable] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[ChatSession]]:
  npc_data, new_session = load_and_prepare_conversation(
    db, player_id, area_name, npc_name, model_name, story, ChatSession_class, TF_class,
    llm_wrapper_for_profile_distillation=llm_wrapper_for_profile_distillation
  )
  
  if npc_data and new_session:
    print_conversation_start_banner(npc_data, area_name, TF_class)
    
    npc_color_code = get_npc_color(npc_data.get('name', 'NPC'), TF_class)
    
    if not new_session.messages: # Only if history (excluding system) is empty
      opening_line = get_npc_opening_line(npc_data, TF_class)
      print(f"{TF_class.BOLD}{npc_color_code}{npc_data['name']} > {TF_class.RESET}")
      print(TF_class.format_terminal_text(opening_line, width=TF_class.get_terminal_width()))
      new_session.add_message("assistant", opening_line) # Add to history
      print()
    elif new_session.messages: # If there's history (user/assistant)
      print(f"{TF_class.DIM}--- Continuing conversation with {npc_data['name']} ---{TF_class.RESET}")
      last_msg = new_session.messages[-1]
      role_display = "You" if last_msg['role'] == 'user' else npc_data.get('name', 'NPC')
      color_to_use = TF_class.GREEN if last_msg['role'] == 'user' else npc_color_code
      print(f"{TF_class.BOLD}{color_to_use}{role_display} > {TF_class.RESET}")
      print(TF_class.format_terminal_text(last_msg['content']))
      print()
    
    return npc_data, new_session
  
  return None, None

# Aggiungi questa funzione di debug per controllare cosa c'è nel DB
def debug_conversation_storage(db, player_id: str, npc_code: str, TF_class: type):
  """Debug function to see what's actually stored in the database."""
  try:
    stored_conversation = db.load_conversation(player_id, npc_code)
    print(f"{TF_class.YELLOW}[DEBUG] DB Storage for {npc_code}:{TF_class.RESET}")
    if stored_conversation:
      for i, msg in enumerate(stored_conversation):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100] + ("..." if len(msg.get("content", "")) > 100 else "")
        print(f"{TF_class.DIM}  {i}: {role} - {content}{TF_class.RESET}")
    else:
      print(f"{TF_class.DIM}  No stored conversation found{TF_class.RESET}")
  except Exception as e:
    print(f"{TF_class.RED}[DEBUG] Error checking storage: {e}{TF_class.RESET}")

def auto_start_default_npc_conversation(
  db, player_id: str, area_name: str, model_name: Optional[str],
  story: str, ChatSession_class: type, TF_class: type,
  llm_wrapper_for_profile_distillation: Optional[Callable] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[ChatSession]]:
  default_npc_info = db.get_default_npc(area_name)
  if not default_npc_info:
    return None, None
  
  default_npc_name = default_npc_info.get('name')
  if not default_npc_name:
    return None, None
  
  return start_conversation_with_specific_npc(
    db, player_id, area_name, default_npc_name, model_name, story, ChatSession_class, TF_class,
    llm_wrapper_for_profile_distillation=llm_wrapper_for_profile_distillation
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