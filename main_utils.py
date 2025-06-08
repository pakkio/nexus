import os
from typing import Dict, List, Any, Optional

try:
  from dotenv import load_dotenv as load_dotenv_file
except ImportError:
  def load_dotenv_file(): pass

try:
  from terminal_formatter import TerminalFormatter
except ImportError:
  class TerminalFormatter:
    DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN=""; BRIGHT_GREEN = ""; BRIGHT_MAGENTA = ""; ITALIC = "";
    @staticmethod
    def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
    @staticmethod
    def get_terminal_width(): return 80

def load_environment_variables():
  load_dotenv_file()

def get_nlp_command_config() -> Dict[str, Any]:
  return {
    'enabled': os.environ.get('NLP_COMMAND_INTERPRETATION_ENABLED', 'true').lower() == 'true',
    'confidence_threshold': float(os.environ.get('NLP_COMMAND_CONFIDENCE_THRESHOLD', '0.7')),
    'model_name': os.environ.get('NLP_COMMAND_MODEL'),
    'debug_mode': os.environ.get('NLP_COMMAND_DEBUG', 'false').lower() == 'true'
  }

def get_help_text(game_session_state: Optional[Dict[str, Any]] = None) -> str: # MODIFIED: Accept game_session_state
  """Generates the help text for user commands."""
  TF = TerminalFormatter # Assuming TF is always available or has a fallback

  wise_guide_name_for_help = "the Wise Guide"
  if game_session_state and game_session_state.get('wise_guide_npc_name'):
      wise_guide_name_for_help = game_session_state['wise_guide_npc_name']

  return f"""
{TF.YELLOW}{TF.BOLD}Available Commands:{TF.RESET}
 {TF.DIM}/exit{TF.RESET}                - Exit the application.
 {TF.DIM}/quit{TF.RESET}                - Alias for /exit.
 {TF.DIM}/help{TF.RESET}                - Show this help message.

{TF.BRIGHT_GREEN}Navigation & Interaction:{TF.RESET}
 {TF.DIM}/go <area_name_fragment>{TF.RESET} - Move to a new area (e.g., /go tav, /go ancient ruins).
 {TF.DIM}/areas{TF.RESET}               - List all visitable areas.
 {TF.DIM}/listareas{TF.RESET}           - List areas on one line (for copy-paste).
 {TF.DIM}/talk <npc_name|.>{TF.RESET} - Start talking to an NPC in the current area (e.g., /talk Jorin).
      '.' for a random NPC if available in area.
 {TF.DIM}/who{TF.RESET}                 - List NPCs in the current area.
 {TF.DIM}/whereami{TF.RESET}            - Show your current location and conversation partner.
 {TF.DIM}/npcs{TF.RESET}                - List all known NPCs by area.

{TF.BRIGHT_CYAN}Guidance & Information:{TF.RESET}
 {TF.DIM}/hint{TF.RESET}                - Consult {wise_guide_name_for_help} for guidance based on your current situation.
      (Temporarily switches context to {wise_guide_name_for_help}).
 {TF.DIM}/endhint{TF.RESET}             - End consultation with {wise_guide_name_for_help} and return to your previous interaction.
 {TF.DIM}/inventory{TF.RESET}           - Display your inventory and Credits.
 {TF.DIM}/inv{TF.RESET}                 - Alias for /inventory.
 {TF.DIM}/give <item_name>{TF.RESET}    - Give an item to the current NPC (e.g., /give Mystic Token).
 {TF.DIM}/give <amount> Credits{TF.RESET} - Give Credits to the current NPC (e.g., /give 50 Credits).
 {TF.DIM}/receive <item_name>{TF.RESET} - (Experimental) Attempt to explicitly take an item mentioned by the NPC.

{TF.BRIGHT_MAGENTA}Player Profile & Debug:{TF.RESET}
 {TF.DIM}/profile{TF.RESET}             - Show your current psychological profile.
 {TF.DIM}/profile_for_npc{TF.RESET}     - (Debug) Show distilled profile insights the current NPC has about you.

{TF.BRIGHT_MAGENTA}Session Management & Stats:{TF.RESET}
 {TF.DIM}/stats{TF.RESET}               - Show statistics for the last LLM response.
 {TF.DIM}/session_stats{TF.RESET}       - Show statistics for the current NPC conversation.
 {TF.DIM}/all_stats{TF.RESET}           - Show comprehensive statistics for all LLM types.
 {TF.DIM}/clear{TF.RESET}               - Clear current conversation history (in memory only).
 {TF.DIM}/history{TF.RESET}             - Show raw JSON history for the current conversation.

{TF.CYAN}{TF.BOLD}💡 Natural Language Commands:{TF.RESET}
You can also use natural language instead of explicit commands:
 {TF.DIM}"voglio andare alla taverna"{TF.RESET}  → {TF.DIM}/go tavern{TF.RESET}
 {TF.DIM}"cosa ho nell'inventario?"{TF.RESET}    → {TF.DIM}/inventory{TF.RESET}
 {TF.DIM}"chi c'è qui?"{TF.RESET}               → {TF.DIM}/who{TF.RESET}
 {TF.DIM}"aiuto"{TF.RESET}                      → {TF.DIM}/help{TF.RESET}
 {TF.DIM}"esco"{TF.RESET}                       → {TF.DIM}/exit{TF.RESET}
"""

def format_storyboard_for_prompt(story: str, max_length: int = 300) -> str:
  if not isinstance(story, str): return "[No Story]"
  return story[:max_length] + "..." if len(story) > max_length else story

def format_npcs_list(npcs_list: List[Dict[str, Any]]) -> str:
  if not npcs_list: return f"{TerminalFormatter.YELLOW}No NPCs found.{TerminalFormatter.RESET}"
  output = [f"\n{TerminalFormatter.YELLOW}{TerminalFormatter.BOLD}Known NPCs:{TerminalFormatter.RESET}"]
  current_area_display = None
  sorted_npcs = sorted(npcs_list, key=lambda x: (x.get('area', 'Unknown Area').lower(), x.get('name', 'Unknown NPC').lower()))
  for npc_info in sorted_npcs:
    area = npc_info.get('area', 'Unknown Area')
    name = npc_info.get('name', 'Unknown NPC')
    role = npc_info.get('role', 'Unknown Role')
    if area != current_area_display:
      if current_area_display is not None: output.append("")
      current_area_display = area
      output.append(f"{TerminalFormatter.BRIGHT_CYAN}{current_area_display}{TerminalFormatter.RESET}")
    output.append(f"  {TerminalFormatter.DIM}- {name} ({role}){TerminalFormatter.RESET}")
  return "\n".join(output)

if __name__ == "__main__":
  print(f"--- main_utils Tests ---")
  nlp_config_test = get_nlp_command_config()
  print(f"NLP Config: {nlp_config_test}")

  # Test help text with mock game state
  mock_state_for_help = {'wise_guide_npc_name': 'Oracle Eldrina', 'TerminalFormatter': TerminalFormatter}
  help_text_test_with_guide = get_help_text(mock_state_for_help)
  assert "Oracle Eldrina" in help_text_test_with_guide
  assert "/profile" in help_text_test_with_guide
  assert "/hint" in help_text_test_with_guide
  print("\n--- Help text with dynamic guide name ---")
  print(help_text_test_with_guide)

  help_text_test_no_guide = get_help_text({'TerminalFormatter': TerminalFormatter}) # No guide name in state
  assert "the Wise Guide" in help_text_test_no_guide # Default placeholder
  print("\n--- Help text with default guide name ---")
  print(help_text_test_no_guide)

  print("All basic tests in main_utils passed.")