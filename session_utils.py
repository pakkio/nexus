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
    # === [AGGIUNTA] Inserisci i due documenti come contesto ===
    mappa = game_session_state.get('mappa_personaggi_luoghi', '')
    percorso = game_session_state.get('percorso_narratore_tappe', '')
    context_intro = (
        f"CONTESTO STATICO:\n{mappa}\n\n"
        f"CONTESTO DINAMICO:\n{percorso}\n\n"
        f"ISTRUZIONI:\nRispondi coerentemente con la posizione attuale dei personaggi e la tappa raggiunta dal Cercatore. "
        f"Non anticipare eventi futuri e non spostare i personaggi in luoghi diversi da quelli previsti, a meno che la narrazione non lo richieda esplicitamente.\n\n"
    )
    # === [FINE AGGIUNTA] ===

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

    # Get greetings and conditional responses
    default_greeting = npc.get('default_greeting', '')
    repeat_greeting = npc.get('repeat_greeting', '')
    conditional_responses = npc.get('conditional_responses', '')

    # Get Second Life command options
    emotes = npc.get('emotes', '')
    animations = npc.get('animations', '')
    lookup_objects = npc.get('lookup', '')
    llsettext_capability = npc.get('llsettext', '')
    teleport_locations = npc.get('teleport', '')

    prompt_lines = [
        f"Sei {name}, un/una {role} nell'area di {area} nel mondo di Eldoria.",
        f"Motivazione: '{motivation}'. Obiettivo (cosa TU, l'NPC, vuoi ottenere): '{goal}'.",
        f"V.O. (Guida per l'azione del giocatore per aiutarti): \"{player_hint_for_npc_context}\"",
    ]
    if hooks:
        prompt_lines.append(f"Per ispirazione, considera questi stili/frasi chiave dal tuo personaggio: (alcune potrebbero essere contestuali, non usarle tutte alla cieca)\n{hooks[:300]}{'...' if len(hooks)>300 else ''}")
    if veil:
        prompt_lines.append(f"Collegamento al Velo (Tuo Background Segreto Importante): {veil}")

    # Add greetings and conditional responses for character-specific dialogue
    if default_greeting or repeat_greeting or conditional_responses:
        prompt_lines.append("\n" + "="*60)
        prompt_lines.append("REGOLE OBBLIGATORIE PER SALUTI E RISPOSTE")
        prompt_lines.append("="*60)
        prompt_lines.append("DEVI usare ESATTAMENTE questi saluti - NON modificarli, NON inventare saluti generici!")
        prompt_lines.append("")

        if default_greeting:
            prompt_lines.append(f"🔹 SALUTO INIZIALE (usa solo al primo messaggio, poi mai più):")
            prompt_lines.append(f'   "{default_greeting}"')
            prompt_lines.append("")
        # NOTE: Repeat_Greeting removed to prevent LLM from repeating it every message
        if conditional_responses:
            prompt_lines.append(f"🔹 RISPOSTE CONDIZIONALI (usa quando la situazione corrisponde):")
            prompt_lines.append(f"   {conditional_responses[:2000]}")
            prompt_lines.append("")

        prompt_lines.append("⚠️  REGOLA CRITICA SUL SALUTO:")
        prompt_lines.append("")
        prompt_lines.append("✅ USA il saluto sopra → SOLO SE questa è la tua PRIMA risposta della conversazione")
        prompt_lines.append("❌ NON usare MAI il saluto → Se hai già risposto anche solo una volta prima")
        prompt_lines.append("")
        prompt_lines.append("⚠️  ERRORE FATALE DA EVITARE:")
        prompt_lines.append("NON iniziare ogni risposta con 'Bentornato', 'Cercatore', o qualsiasi saluto!")
        prompt_lines.append("Dopo il primo messaggio, vai DIRETTO alla risposta senza saluti!")
        prompt_lines.append("")
        prompt_lines.append("ESEMPI:")
        prompt_lines.append("  ✅ Msg 1: 'Cercatore... il Velo si indebolisce...' [OK - primo messaggio]")
        prompt_lines.append("  ✅ Msg 2: 'Il Cristallo si trova nelle rovine...' [OK - nessun saluto]")
        prompt_lines.append("  ❌ Msg 2: 'Bentornato, Cercatore. Il Cristallo...' [ERRORE - saluto ripetuto!]")
        prompt_lines.append("")
        prompt_lines.append("="*60 + "\n")

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

    # REMOVED: Second Life command generation instructions for LLM
    # SL commands are now generated server-side via generate_sl_command_prefix() in chat_manager.py
    # The LLM no longer needs to generate [lookup=...;emote=...] commands in its responses

    # Add teleport instructions if NPC has teleport capability
    if teleport_locations:
        teleport_instructions = [
            "\n=== TELEPORT CAPABILITY ===",
            f"You have the ability to teleport players to: {teleport_locations}",
            "IMPORTANT: When the player asks to be teleported or agrees to teleportation:",
            "- You MUST add the tag [OFFER_TELEPORT] at the VERY END of your response",
            "- The tag must be EXACTLY [OFFER_TELEPORT] - no spaces, no variations",
            "- It triggers the actual teleport mechanism",
            "Example correct response: 'Certo, ti teletrasporto al mio teatro! [OFFER_TELEPORT]'",
            "Example when player says 'si' or 'teleportami': 'Perfetto, partiamo! [OFFER_TELEPORT]'",
            "CRITICAL: Without [OFFER_TELEPORT] tag, the teleport will NOT work!",
            "=== END TELEPORT ===\n"
        ]
        prompt_lines.extend(teleport_instructions)

    # Add enhanced world context for better NPC responses
    try:
        from enhanced_context_builder import EnhancedContextBuilder
        context_builder = EnhancedContextBuilder(game_session_state['db'])
        enhanced_context = context_builder.build_comprehensive_context(max_length=1500)
        prompt_lines.append(f"\n{enhanced_context}")
    except Exception as e:
        # Fallback if enhanced context fails
        print(f"Warning: Enhanced context failed: {e}")

    prompt_lines.extend([
        f"\nContesto Globale del Mondo (Eldoria): {story_context}",
        "",
        "=== REGOLE LINGUISTICHE CRITICHE ===",
        "**LINGUA OBBLIGATORIA**: Devi parlare ESCLUSIVAMENTE in ITALIANO per TUTTA la conversazione.",
        "NON usare MAI parole o frasi in inglese. Se il giocatore scrive in inglese, rispondi SEMPRE in italiano.",
        "Esempi CORRETTI: 'Benvenuto', 'Ciao', 'Dove', 'Chi', 'Cosa'",
        "Esempi VIETATI: 'Welcome', 'Hello', 'Where', 'Who', 'What'",
        "Se stai per scrivere una parola in inglese, FERMATI e traducila in italiano.",
        "=== FINE REGOLE LINGUISTICHE ===",
        "",
        "=== COMPORTAMENTO COME NPC ===",
        "Parla in modo appropriato al setting fantasy e al tuo ruolo. Mantieni il personaggio.",
        "Sii consapevole delle interazioni passate se riassunte sopra o nella cronologia della chat.",
        "",
        "**SII DIRETTO E UTILE**: Non essere troppo misterioso o criptico. Il giocatore ha bisogno di informazioni concrete.",
        "USA LE INFORMAZIONI GEOGRAFICHE E DI MISSIONE SOPRA per dare risposte specifiche e utili al giocatore.",
        "Se il giocatore chiede dove trovare qualcosa o qualcuno, usa il contesto geografico per rispondere PRECISAMENTE con nomi di aree.",
        "Se il giocatore chiede di oggetti o missioni, spiega CHIARAMENTE cosa serve, chi ce l'ha, e dove andare.",
        "Non essere eccessivamente cauto o sospettoso - il giocatore è il Cercatore e sta cercando di salvare il Velo.",
        "Puoi dare suggerimenti e indicazioni anche se il giocatore non ha ancora completato quest per te.",
        "",
        "⚠️ IMPORTANTE - NON MOSTRARE MAI AL GIOCATORE:",
        "- Note interne come 'V.O.:', 'AI_Behavior_Notes:', tag di sistema",
        "- Meta-istruzioni o suggerimenti per il game master",
        "- Informazioni tecniche o di debug",
        "- Output di comandi di sistema come 'Location:', 'Talking to:', 'Moving to', '(Hint for...)'",
        "- NON fingere mai di essere il sistema di gioco o generare messaggi di comando",
        "- NON dire cose come 'Elira ti informa Moving to...' o 'Location: ...' - sono comandi del sistema!",
        "Il giocatore vede SOLO il dialogo del personaggio, nient'altro!",
        "",
        "❌ VIETATO ASSOLUTAMENTE - Non generare MAI output che somigliano a comandi di sistema:",
        "- SBAGLIATO: 'Elira ti informa Moving to Forest...'",
        "- SBAGLIATO: 'Location: Sanctum of Whispers, Talking to: Lyra'",
        "- SBAGLIATO: 'Moving to City...', 'Saving conversation...'",
        "- SBAGLIATO: '[CONVERSATION_BREAK: Player left the conversation]' (tag di sistema interno)",
        "- SBAGLIATO: '[CONVERSATION_RESUMED: ...]' (tag di sistema interno)",
        "- SBAGLIATO: 'Puoi raggiungerla usando /go forest' (NON suggerire comandi /go, /talk, ecc.)",
        "✅ CORRETTO: 'Elira si trova nella Foresta, a sud del villaggio.'",
        "✅ CORRETTO: 'Vai alla Foresta e cerca Elira tra gli alberi antichi.'",
        "✅ CORRETTO: 'Troverai Mara nel Villaggio, vicino al mercato.'",
        "",
        "⚠️ IMMERSIONE: Parla sempre IN CHARACTER. NON menzionare MAI comandi come /go, /talk, /whereami.",
        "Se il giocatore chiede dove trovare qualcuno, dì SOLO il luogo (es. 'nella Foresta', 'in Città').",
        "Il giocatore sa già come muoversi - tu fornisci solo informazioni geografiche naturali.",
        "",
        "⚠️ IMPORTANTE: Se vedi tag come [CONVERSATION_BREAK] o [CONVERSATION_RESUMED] nella cronologia,",
        "questi sono SOLO per il sistema - NON menzionarli MAI, NON ripeterli MAI nelle tue risposte!",
        "Semplicemente riconosci che il tempo è passato e continua naturalmente il dialogo.",
        "",
        "COMPORTAMENTO IMPORTANTE: Sei un personaggio con le TUE motivazioni e obiettivi.",
        "INFORMAZIONI MAPPA QUEST - USA QUESTE INFORMAZIONI SEMPRE:",
        "1. Se hai un oggetto da dare: Dillo CHIARAMENTE cosa vuoi in cambio",
        "2. Se il giocatore chiede del tuo oggetto: Spiega ESATTAMENTE le condizioni",
        "3. Se il giocatore porta quello che chiedi: Dai il tuo oggetto IMMEDIATAMENTE",
        "4. Se non sai dove trovare un oggetto: Suggerisci di chiedere ad altri NPC specifici",
        "",
        "MAPPA OGGETTI PRINCIPALI (Condividi queste informazioni liberamente):",
        "- Pozione di Guarigione: da Mara (Village) per 50 crediti",
        "- Seme della Foresta: da Elira (Forest) in cambio di Pozione di Guarigione",
        "- Minerale di Ferro Antico: da Boros (Mountain) in cambio di Seme della Foresta",
        "- Trucioli di Ferro: da Garin (Village) in cambio di Minerale di Ferro Antico",
        "- Ciotola dell'Offerta Sacra: da Jorin (Tavern) in cambio di Trucioli di Ferro",
        "- Cristallo di Memoria Antica: da Syra (Ancient Ruins) in cambio di Ciotola Sacra",
        "- Pergamena della Saggezza: da Cassian (City) per 50 crediti",
        "",
        "⚠️ REGOLA CREDITI: Quando vendi oggetti per crediti, USA SEMPRE il formato [GIVEN_ITEMS: NomeOggetto, -X Credits]",
        "Il sistema controllerà AUTOMATICAMENTE se il giocatore ha abbastanza crediti. NON devi chiedere conferma.",
        "Se il player non ha crediti sufficienti, il sistema bloccherà la transazione automaticamente.",
        "",
        "⚠️ REGOLA INVENTORY HINT (MARA ONLY): Se sei MARA e il player dice 'non ho crediti/soldi', DEVI SEMPRE dire:",
        "   'Hai controllato il tuo inventario? A volte abbiamo risorse che dimentichiamo di avere. Prova con /inventory'",
        "   Questa è una regola PRIORITARIA E OBBLIGATORIA per Mara.",
        "RICONOSCIMENTO LINGUAGGIO NATURALE: Se il player dice QUALSIASI frase che indica volontà di pagare/comprare,",
        "  procedi IMMEDIATAMENTE con la vendita usando [GIVEN_ITEMS: item, -X Credits].",
        "  Esempi che indicano volontà di pagare:",
        "  - 'Ti do 50 crediti, mi vendi la pozione?'",
        "  - 'Voglio comprare la pozione'",
        "  - 'Ho i crediti, dammi la pozione'",
        "  - 'Ecco i soldi'",
        "  - Qualsiasi variazione che esprime intenzione di acquisto",
        "ESEMPIO CORRETTO: Il player dice 'ti do 50 crediti mi vendi la pozione?' →",
        "  Risposta: 'Certamente! Ecco la tua Pozione di Guarigione.'",
        "  [GIVEN_ITEMS: Pozione di Guarigione, -50 Credits]",
        "  (Il sistema controlla automaticamente i crediti e blocca se insufficienti)",
        "",
        "⚠️ REGOLA CRITICA: Non filosofeggiare eccessivamente! Sii PRATICO e DIRETTO.",
        "❌ EVITA frasi vaghe come 'Il vento sussurra antiche verità...'",
        "✅ USA frasi concrete come 'Portami una Pozione di Guarigione da Mara e ti darò il Seme.'",
        "",
        "Per DARE OGGETTI: dai oggetti/crediti quando il giocatore porta quello che chiedi.",
        "Per DARE INFORMAZIONI: sii generoso - condividi conoscenze, direzioni, e mappa oggetti liberamente.",
        "Ricorda: sei un alleato che vuole aiutare a salvare il Velo, non un ostacolo misterioso.",
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
        return f"*{name} dice,* \"{chosen_hook.strip()}\"" if not chosen_hook.startswith("*") else chosen_hook.strip()
    elif role:
        return random.choice([f"*{name}, {role}, ti osserva.* Cosa desideri?", f"*{name}, {role}, alza lo sguardo al tuo avvicinarsi.* Sì?"])
    else:
        return f"*{name} ti guarda in attesa.*"


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

def normalize_area_name(area_raw: str) -> str:
  """Normalize area name from NPC file format to display format.
  
  Handles cases like:
  - 'sanctumofwhispers' -> 'Sanctum of Whispers'  
  - 'ancientruins' -> 'Ancient Ruins'
  - 'village' -> 'Village'
  """
  if not area_raw:
    return ""
  
  area_clean = area_raw.strip()
  
  # If already properly formatted (has spaces/capitals), return as-is
  if ' ' in area_clean or area_clean != area_clean.lower():
    return area_clean
  
  # Convert known lowercase-concatenated names to proper format
  area_mappings = {
    'sanctumofwhispers': 'Sanctum of Whispers',
    'ancientruins': 'Ancient Ruins',
    'liminalvoid': 'Liminal Void',
    'nexusofpaths': 'Nexus of Paths',
    'village': 'Village',
    'tavern': 'Tavern',
    'forest': 'Forest',
    'mountain': 'Mountain',
    'city': 'City'
  }
  
  normalized = area_mappings.get(area_clean.lower())
  if normalized:
    return normalized
  
  # Fallback: capitalize first letter
  return area_clean.title()

def get_known_areas_from_list(all_known_npcs: List[Dict[str, Any]]) -> List[str]:
  if not all_known_npcs:
    return []
  
  areas = []
  for npc in all_known_npcs:
    area_raw = npc.get('area', '').strip()
    if area_raw:
      normalized_area = normalize_area_name(area_raw)
      if normalized_area not in areas:
        areas.append(normalized_area)
  
  return sorted(areas, key=str.lower)
