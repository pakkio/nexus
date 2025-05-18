# Path: main_utils.py
# Updated help text for Credits and /endhint
# MODIFIED: Added /areas to help text

import os
from typing import Dict, List, Any

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


def get_help_text() -> str:
    """Generates the help text for user commands."""
    TF = TerminalFormatter # Ensure TerminalFormatter is defined or imported
    return f"""
{TF.YELLOW}{TF.BOLD}Available Commands:{TF.RESET}
 {TF.DIM}/exit{TF.RESET}                - Exit the application.
 {TF.DIM}/quit{TF.RESET}                - Alias for /exit.
 {TF.DIM}/help{TF.RESET}                - Show this help message.

{TF.BRIGHT_GREEN}Navigation & Interaction:{TF.RESET}
 {TF.DIM}/go <area_name_fragment>{TF.RESET} - Move to a new area (e.g., /go tav, /go ancient ruins).
 {TF.DIM}/areas{TF.RESET}               - List all visitable areas.
 {TF.DIM}/talk <npc_name|.>{TF.RESET} - Start talking to an NPC in the current area (e.g., /talk Jorin).
                        '.' for a random NPC.
 {TF.DIM}/who{TF.RESET}                 - List NPCs in the current area.
 {TF.DIM}/whereami{TF.RESET}            - Show your current location and conversation partner.
 {TF.DIM}/npcs{TF.RESET}                - List all known NPCs by area.

{TF.BRIGHT_CYAN}Guidance & Information:{TF.RESET}
 {TF.DIM}/hint{TF.RESET}                - Consult Lyra for guidance based on your current situation.
                        (Temporarily switches context to Lyra).
 {TF.DIM}/endhint{TF.RESET}             - End consultation with Lyra and return to your previous interaction.
 {TF.DIM}/inventory{TF.RESET}           - Display your inventory and Credits.
 {TF.DIM}/inv{TF.RESET}                 - Alias for /inventory.
 {TF.DIM}/give <item_name>{TF.RESET}    - Give an item to the current NPC (e.g., /give Mystic Token).
 {TF.DIM}/give <amount> Credits{TF.RESET} - Give Credits to the current NPC (e.g., /give 50 Credits).

{TF.BRIGHT_MAGENTA}Session Management & Stats:{TF.RESET}
 {TF.DIM}/stats{TF.RESET}               - Show statistics for the last LLM response.
 {TF.DIM}/session_stats{TF.RESET}       - Show statistics for the current NPC conversation.
 {TF.DIM}/clear{TF.RESET}               - Clear current conversation history (in memory only).
 {TF.DIM}/history{TF.RESET}             - Show raw JSON history for the current conversation.
"""

def format_storyboard_for_prompt(story: str, max_length: int = 300) -> str:
    if not isinstance(story, str): return "[No Story]"
    return story[:max_length] + "..." if len(story) > max_length else story

def format_npcs_list(npcs_list: List[Dict[str, Any]]) -> str:
    if not npcs_list: return f"{TerminalFormatter.YELLOW}No NPCs found.{TerminalFormatter.RESET}"
    output = [f"\n{TerminalFormatter.YELLOW}{TerminalFormatter.BOLD}Known NPCs:{TerminalFormatter.RESET}"]
    current_area_display = None
    sorted_npcs = sorted(npcs_list, key=lambda x: (x.get('area', 'Unknown').lower(), x.get('name', 'Unknown').lower()))
    for npc_info in sorted_npcs:
        area = npc_info.get('area', 'Unknown Area'); name = npc_info.get('name', 'Unknown NPC'); role = npc_info.get('role', 'Unknown Role')
        if area != current_area_display:
            if current_area_display is not None: output.append("")
            current_area_display = area; output.append(f"{TerminalFormatter.BRIGHT_CYAN}{current_area_display}{TerminalFormatter.RESET}")
        output.append(f"  {TerminalFormatter.DIM}- {name} ({role}){TerminalFormatter.RESET}")
    return "\n".join(output)


if __name__ == "__main__":
    print(f"--- main_utils Tests ---")
    help_text_test = get_help_text()
    assert "/give <amount> Credits" in help_text_test
    assert "/endhint" in help_text_test
    assert "/areas" in help_text_test # MODIFIED: Test for /areas in help
    print("Help text includes credits, endhint, and areas commands. All basic tests passed.")
