from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_listareas(state: Dict[str, Any]) -> HandlerResult:
  """Handler per il comando /listareas - mostra aree su una riga per copia-incolla."""
  TF = state['TerminalFormatter']
  db = state['db']
  
  _add_profile_action(state, "Used /listareas command")
  
  all_known_npcs = session_utils.refresh_known_npcs_list(db, TF)
  known_areas = session_utils.get_known_areas_from_list(all_known_npcs)
  
  if not known_areas:
    print(f"{TF.YELLOW}No known areas found.{TF.RESET}")
  else:
    # Crea una stringa con tutte le aree separate da virgole
    areas_string = ", ".join(known_areas)
    print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}Available Areas:{TF.RESET}")
    print(f"{TF.CYAN}{areas_string}{TF.RESET}")
    print(f"\n{TF.DIM}💡 Copy-paste ready format above{TF.RESET}")
  
  return {**state, 'status': 'ok', 'continue_loop': True}
