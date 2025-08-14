import json
import re
from typing import Dict, List, Any, Optional, Callable

try:
  from terminal_formatter import TerminalFormatter
  from llm_stats_tracker import get_global_stats_tracker
except ImportError:
  class TerminalFormatter:
    DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; ITALIC = ""

def get_available_commands() -> Dict[str, str]:
  """Restituisce un dizionario dei comandi disponibili con descrizioni."""
  return {
    '/exit': 'Esci dal gioco',
    '/quit': 'Esci dal gioco',
    '/help': 'Mostra i comandi disponibili',
    '/go <area>': 'Vai in una nuova area (es. taverna, villaggio, rovine)',
    '/areas': 'Elenca tutte le aree visitabili',
    '/listareas': 'Elenca aree su una riga per copia-incolla',
    '/talk <npc>': 'Parla con un NPC specifico',
    '/who': 'Mostra gli NPC nell\'area corrente',
    '/whereami': 'Mostra la tua posizione attuale',
    '/npcs': 'Elenca tutti gli NPC conosciuti',
    '/hint': 'Consulta Lyra per consigli',
    '/endhint': 'Termina la consultazione con Lyra',
    '/inventory': 'Mostra il tuo inventario',
    '/inv': 'Mostra il tuo inventario',
    '/give <item>': 'Dai un oggetto all\'NPC corrente',
    '/receive <item>': 'Chiedi esplicitamente un oggetto all\'NPC',
    '/profile': 'Mostra il tuo profilo psicologico',
    '/stats': 'Mostra statistiche dell\'ultima risposta',
    '/clear': 'Cancella la cronologia conversazione corrente',
    '/history': 'Mostra la cronologia in formato JSON',
    '/sussurri': 'Debug: controlla/attiva effetti decadimento memoria'
  }

def get_italian_area_mapping() -> Dict[str, str]:
  """Mapping italiano → inglese per le aree del gioco."""
  return {
    'taverna': 'Tavern',
    'tavern': 'Tavern',
    'santuario': 'Sanctum of Whispers',
    'sanctum': 'Sanctum of Whispers',
    'rovine': 'Ancient Ruins',
    'rovine antiche': 'Ancient Ruins',
    'antica': 'Ancient Ruins',
    'antiche': 'Ancient Ruins',
    'citta': 'City',
    'città': 'City',
    'city': 'City',
    'tribunale': 'City (Tribunal or Fortress)',
    'fortezza': 'City (Tribunal or Fortress)',
    'foresta': 'Forest',
    'forest': 'Forest',
    'bosco': 'Forest',
    'montagna': 'Mountain',
    'mountain': 'Mountain',
    'monte': 'Mountain',
    'villaggio': 'Village',
    'village': 'Village',
    'paese': 'Village'
  }

def build_command_interpretation_prompt(user_input: str, current_context: Dict[str, Any]) -> List[Dict[str, str]]:
  """Costruisce il prompt per l'LLM di interpretazione comandi."""
  available_commands = get_available_commands()
  commands_text = "\n".join([f"- {cmd}: {desc}" for cmd, desc in available_commands.items()])
  
  current_area = current_context.get('current_area', 'Nessuna area')
  current_npc = current_context.get('current_npc', {}).get('name', 'Nessuno')
  in_lyra_mode = current_context.get('in_lyra_hint_mode', False)
  available_areas = current_context.get('available_areas', [])
  
  areas_text = ""
  if available_areas:
    areas_text = f"\nAREE DISPONIBILI NEL GIOCO:\n"
    for area in available_areas:
      areas_text += f"- {area}\n"
  
  italian_mapping = get_italian_area_mapping()
  areas_text += f"\nMAPPING ITALIANO → INGLESE (usa il nome inglese per /go):\n"
  for it_name, en_name in italian_mapping.items():
    if en_name in available_areas:
      areas_text += f"- '{it_name}' → '{en_name}'\n"

  system_prompt = f"""Sei un assistente intelligente che interpreta l'input del giocatore in un gioco di ruolo testuale.

Il tuo compito è determinare se l'input del giocatore è:
1. Un COMANDO implicito (che dovrebbe essere convertito in un comando esplicito)
2. DIALOGO diretto con l'NPC

COMANDI DISPONIBILI:
{commands_text}

CONTESTO ATTUALE:
- Area corrente: {current_area}
- NPC corrente: {current_npc}
- In consultazione Lyra: {in_lyra_mode}
{areas_text}

REGOLE DI INTERPRETAZIONE FONDAMENTALI:

**AZIONI AMBIENTALI (→ DIALOGO, NON COMANDI):**
- Se il giocatore vuole RACCOGLIERE/PRENDERE/PICK UP qualcosa dall'ambiente → DIALOGO
- "raccolgo la piaga", "prendo il campione", "pick it up", "la prendo" → DIALOGO
- "tocco l'oggetto", "esamino la ferita", "mi avvicino alla piaga" → DIALOGO
- Qualsiasi azione di interazione con oggetti ambientali → DIALOGO

**DARE OGGETTI AGLI NPC (→ COMANDO /give):**
- Se il giocatore vuole DARE/OFFRIRE qualcosa di SPECIFICO all'NPC → /give <item>
- "do la moneta a Jorin", "eccoti la moneta", "ti do la spada" → /give
- "offro 50 crediti", "ecco 100 Credits" → /give

**CHIEDERE/RICEVERE OGGETTI (→ DIALOGO o /receive):**
- "hai qualcosa da darmi?", "cosa mi puoi dare?" → DIALOGO (richiesta generica)
- "mi dai X?", "posso avere X?" → DIALOGO (richiesta specifica ma educata)
- "dammi X", "voglio X" → /receive X (richiesta diretta/imperativa)
- "ho bisogno di X" → DIALOGO (espressione di bisogno)

**MOVIMENTO E NAVIGAZIONE:**
- Se il giocatore vuole spostarsi/andare da qualche parte → /go <area_inglese>
- Se chiede chi c'è/persone/abitanti → /who
- Se chiede dove si trova/posizione → /whereami

**ALTRI COMANDI:**
- Se chiede aiuto/comandi/cosa può fare → /help
- Se vuole vedere l'inventario/oggetti/borsa/tasca → /inventory
- Se vuole uscire/andarsene/smettere → /exit
- Se vuole parlare con qualcuno di specifico → /talk <npc>
- Se chiede consigli/guida/suggerimenti → /hint
- Se chiede lista aree/elenca aree → /areas o /listareas

ESEMPI SPECIFICI:

**DIALOGO (NON comandi):**
- "raccolgo la piaga" → DIALOGO
- "prendo il campione per Lyra" → DIALOGO
- "hai qualcosa da darmi in cambio?" → DIALOGO
- "cosa mi puoi dare?" → DIALOGO
- "mi puoi aiutare con qualcosa?" → DIALOGO
- "ciao Jorin, come stai?" → DIALOGO
- "dimmi della tua famiglia" → DIALOGO
- "ho bisogno di una mappa" → DIALOGO

**COMANDI /give:**
- "do la moneta a questo NPC" → COMANDO: /give Rare Coin
- "eccoti la moneta rara" → COMANDO: /give Rare Coin
- "ti do 50 crediti" → COMANDO: /give 50 Credits
- "offro la spada in cambio" → COMANDO: /give Sword

**COMANDI /receive:**
- "dammi il diario" → COMANDO: /receive Diary
- "voglio quel libro" → COMANDO: /receive Book
- "passami la chiave" → COMANDO: /receive Key

**ALTRI COMANDI:**
- "vado in taverna" → COMANDO: /go Tavern
- "cosa ho con me?" → COMANDO: /inventory
- "chi c'è qui?" → COMANDO: /who
- "esco" → COMANDO: /exit

DISTINZIONI IMPORTANTI:
- "eccoti X" / "ti do X" = DARE (comando /give)
- "hai X?" / "cosa mi dai?" = CHIEDERE EDUCATAMENTE (dialogo)
- "dammi X" / "voglio X" = RICHIEDERE DIRETTAMENTE (comando /receive)
- "raccolgo X" / "prendo X" = RACCOGLIERE DALL'AMBIENTE (dialogo)

IMPORTANTE:
- Per /go usa SEMPRE il nome inglese dell'area dalla mappatura sopra
- Se l'input contiene nomi di luoghi italiani, convertili usando la mappatura
- Se non trovi corrispondenza esatta, usa l'area più simile disponibile
- RICORDA: raccogliere/prendere oggetti dall'ambiente = DIALOGO, non /give
- RICORDA: chiedere genericamente "hai qualcosa?" = DIALOGO, non comando

Rispondi SOLO con un oggetto JSON valido nel seguente formato:
{{
  "is_command": true/false,
  "inferred_command": "/comando args" o null,
  "confidence": 0.0-1.0,
  "reasoning": "breve spiegazione"
}}"""

  return [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Interpreta questo input del giocatore: \"{user_input}\""}
  ]

def interpret_user_intent(
  user_input: str,
  game_state: Dict[str, Any],
  llm_wrapper_func: Callable,
  model_name: str,
  confidence_threshold: float = 0.7
) -> Dict[str, Any]:
  """
  Usa l'LLM per interpretare l'intent dell'utente.
  Returns:
  {
    'is_command': bool,
    'inferred_command': str o None,
    'confidence': float,
    'original_input': str,
    'reasoning': str
  }
  """
  TF = game_state.get('TerminalFormatter', TerminalFormatter)
  
  context = {
    'current_area': game_state.get('current_area'),
    'current_npc': game_state.get('current_npc'),
    'in_lyra_hint_mode': game_state.get('in_lyra_hint_mode', False),
    'available_areas': game_state.get('available_areas', [])
  }
  
  messages = build_command_interpretation_prompt(user_input, context)
  
  try:
    response_text, stats = llm_wrapper_func(
      messages=messages,
      model_name=model_name,
      stream=False,  # Non vogliamo streaming per questo
      collect_stats=True
    )
    
    # Record stats for command interpretation
    if stats:
      try:
        stats_tracker = get_global_stats_tracker()
        stats_tracker.record_call(model_name, "command_interpretation", stats)
      except Exception as e:
        print(f"{TF.DIM}Warning: Could not record command interpretation LLM stats: {e}{TF.RESET}")
    
    if stats and stats.get("error"):
      print(f"{TF.YELLOW}Warning: LLM error in command interpretation: {stats['error']}{TF.RESET}")
      return _fallback_interpretation(user_input, game_state)
    
    try:
      cleaned_response = response_text.strip()
      
      # Handle various response formats
      if cleaned_response.startswith("```json"):
        cleaned_response = re.sub(r"```json\s*", "", cleaned_response)
      if cleaned_response.endswith("```"):
        cleaned_response = re.sub(r"\s*```$", "", cleaned_response)
      
      # Handle cases where LLM returns empty or whitespace-only responses
      if not cleaned_response or cleaned_response.isspace():
        print(f"{TF.YELLOW}Warning: Empty LLM response for command interpretation{TF.RESET}")
        return _fallback_interpretation(user_input, game_state)
      
      # Try to extract JSON from response if it's embedded in text
      json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
      if json_match:
        cleaned_response = json_match.group(0)
      
      try:
        interpretation = json.loads(cleaned_response)
      except json.JSONDecodeError as json_err:
        # Try to fix common JSON issues
        try:
          # Fix single quotes to double quotes
          fixed_response = cleaned_response.replace("'", '"')
          interpretation = json.loads(fixed_response)
        except json.JSONDecodeError:
          # Try to parse partial JSON
          try:
            # Extract key-value pairs manually for simple cases
            if "is_command" in cleaned_response and "confidence" in cleaned_response:
              interpretation = _extract_json_manually(cleaned_response)
            else:
              raise json_err
          except:
            raise json_err
      
      if not isinstance(interpretation, dict):
        raise ValueError("Response is not a dict")
      
      required_fields = ['is_command', 'confidence']
      for field in required_fields:
        if field not in interpretation:
          raise ValueError(f"Missing required field: {field}")
      
      interpretation['original_input'] = user_input
      if 'reasoning' not in interpretation:
        interpretation['reasoning'] = "No reasoning provided"
      if 'inferred_command' not in interpretation:
        interpretation['inferred_command'] = None
      
      return interpretation
      
    except (json.JSONDecodeError, ValueError) as e:
      print(f"{TF.YELLOW}Warning: Could not parse LLM response for command interpretation: {e}{TF.RESET}")
      print(f"{TF.DIM}LLM Response was: {response_text[:200]}...{TF.RESET}")
      return _fallback_interpretation(user_input, game_state)
    
  except Exception as e:
    print(f"{TF.RED}Error during command interpretation: {e}{TF.RESET}")
    return _fallback_interpretation(user_input, game_state)

def _extract_json_manually(text: str) -> Dict[str, Any]:
  """Extract JSON fields manually from malformed response."""
  result = {}
  
  # Extract is_command
  is_command_match = re.search(r'"?is_command"?\s*:\s*([^,}\s]+)', text, re.IGNORECASE)
  if is_command_match:
    value = is_command_match.group(1).strip().strip('"').lower()
    result['is_command'] = value in ['true', '1', 'yes']
  else:
    result['is_command'] = False
  
  # Extract confidence
  confidence_match = re.search(r'"?confidence"?\s*:\s*([0-9.]+)', text, re.IGNORECASE)
  if confidence_match:
    try:
      result['confidence'] = float(confidence_match.group(1))
    except ValueError:
      result['confidence'] = 0.5
  else:
    result['confidence'] = 0.5
  
  # Extract reasoning if present
  reasoning_match = re.search(r'"?reasoning"?\s*:\s*"([^"]*)"', text, re.IGNORECASE)
  if reasoning_match:
    result['reasoning'] = reasoning_match.group(1)
  
  return result

def _fallback_interpretation(user_input: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
  """Interpretazione di fallback basata su regole semplici con aree disponibili."""
  input_lower = user_input.lower().strip()
  available_areas = game_state.get('available_areas', [])
  italian_mapping = get_italian_area_mapping()
  
  # Parole chiave per raccogliere (DIALOGO, non comando)
  collect_keywords = ['raccolgo', 'prendo', 'pick up', 'pick it up', 'la raccolgo', 'la prendo', 'lo raccolgo', 'lo prendo']
  
  # Parole chiave per dare (COMANDO /give)
  give_keywords = ['eccoti', 'ti do', 'do il', 'do la', 'offro', 'regalo', 'consegno']
  
  # Parole chiave per ricevere/chiedere educatamente (DIALOGO)
  ask_keywords = ['hai qualcosa', 'cosa mi', 'mi puoi dare', 'mi dai', 'cosa hai']
  
  # Parole chiave per richiedere direttamente (COMANDO /receive)
  demand_keywords = ['dammi', 'voglio', 'passami', 'devo avere']
  
  # Parole chiave per movimento
  movement_keywords = ['vai', 'andiamo', 'porta', 'spostarsi', 'andare', 'vado']
  
  inventory_keywords = ['inventario', 'oggetti', 'borsa', 'cosa ho', 'tasca']
  who_keywords = ['chi c\'è', 'chi è qui', 'persone', 'abitanti']
  help_keywords = ['aiuto', 'help', 'comandi', 'cosa posso fare']
  exit_keywords = ['esci', 'esco', 'uscire', 'fine', 'basta']
  areas_keywords = ['aree', 'liste', 'elenca', 'lista aree']
  
  # Controlla se è un'azione di raccolta (dovrebbe essere DIALOGO)
  for keyword in collect_keywords:
    if keyword in input_lower:
      return {
        'is_command': False,
        'inferred_command': None,
        'confidence': 0.9,
        'original_input': user_input,
        'reasoning': f'Fallback: detected collection action "{keyword}" - should be dialogue'
      }
  
  # Controlla se è una richiesta diretta (dovrebbe essere COMANDO /receive)
  for keyword in demand_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/receive item',  # Generico, sarà raffinato
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': f'Fallback: detected demand "{keyword}" - /receive command'
      }
  
  # Controlla se è una richiesta educata (dovrebbe essere DIALOGO)
  for keyword in ask_keywords:
    if keyword in input_lower:
      return {
        'is_command': False,
        'inferred_command': None,
        'confidence': 0.9,
        'original_input': user_input,
        'reasoning': f'Fallback: detected polite request "{keyword}" - should be dialogue'
      }
  
  # Controlla se è un'azione di dare (dovrebbe essere COMANDO /give)
  for keyword in give_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/give item',  # Generico, sarà raffinato dal sistema
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': f'Fallback: detected give action "{keyword}"'
      }
  
  # Controlla movimento
  for keyword in movement_keywords:
    if keyword in input_lower:
      for it_area, en_area in italian_mapping.items():
        if it_area in input_lower and en_area in available_areas:
          return {
            'is_command': True,
            'inferred_command': f'/go {en_area}',
            'confidence': 0.8,
            'original_input': user_input,
            'reasoning': f'Fallback: detected movement to {en_area}'
          }
      return {
        'is_command': True,
        'inferred_command': '/areas',
        'confidence': 0.6,
        'original_input': user_input,
        'reasoning': 'Fallback: detected movement intent, showing areas'
      }
  
  for keyword in inventory_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/inventory',
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': 'Fallback: detected inventory intent'
      }
  
  for keyword in who_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/who',
        'confidence': 0.7,
        'original_input': user_input,
        'reasoning': 'Fallback: detected who intent'
      }
  
  for keyword in areas_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/areas',
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': 'Fallback: detected areas listing intent'
      }
  
  for keyword in help_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/help',
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': 'Fallback: detected help intent'
      }
  
  for keyword in exit_keywords:
    if keyword in input_lower:
      return {
        'is_command': True,
        'inferred_command': '/exit',
        'confidence': 0.8,
        'original_input': user_input,
        'reasoning': 'Fallback: detected exit intent'
      }
  
  # Default: dialogo
  return {
    'is_command': False,
    'inferred_command': None,
    'confidence': 0.9,
    'original_input': user_input,
    'reasoning': 'Fallback: default to dialogue'
  }

if __name__ == "__main__":
  print("--- Command Interpreter Test ---")
  
  def mock_llm(messages, model_name, stream, collect_stats):
    return '{"is_command": true, "inferred_command": "/go Tavern", "confidence": 0.9}', {}
  
  test_state = {
    'current_area': 'Sanctum of Whispers',
    'current_npc': {'name': 'Lyra'},
    'in_lyra_hint_mode': False,
    'available_areas': ['Ancient Ruins', 'City', 'Forest', 'Mountain', 'Sanctum of Whispers', 'Tavern', 'Village']
  }
  
  # Test casi specifici per give/receive
  test_cases = [
    "vado in taverna",                    # Dovrebbe essere COMANDO /go
    "raccolgo la piaga",                  # Dovrebbe essere DIALOGO
    "eccoti la moneta rara",              # Dovrebbe essere COMANDO /give
    "hai qualcosa da darmi in cambio?",   # Dovrebbe essere DIALOGO
    "dammi il diario",                    # Dovrebbe essere COMANDO /receive
    "cosa mi puoi dare?",                 # Dovrebbe essere DIALOGO
    "voglio quel libro",                  # Dovrebbe essere COMANDO /receive
    "cosa ho nell'inventario"             # Dovrebbe essere COMANDO /inventory
  ]
  
  for test_input in test_cases:
    result = interpret_user_intent(test_input, test_state, mock_llm, "test-model")
    command_type = "COMANDO" if result['is_command'] else "DIALOGO"
    inferred = result.get('inferred_command', 'None')
    print(f"'{test_input}' → {command_type} ({inferred}) - {result['reasoning']}")
  
  print("--- Test Completed ---")