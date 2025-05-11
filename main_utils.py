# Path: main_utils.py

import os
from typing import Dict, List, Any

# --- Environment Loading ---
try:
    from dotenv import load_dotenv as load_dotenv_file
except ImportError:
    print("Warning (main_utils): python-dotenv not found. .env file will not be loaded.")
    def load_dotenv_file(): pass 

# --- Terminal Formatter ---
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (main_utils): terminal_formatter not found. Using basic fallback formatting.")
    class TerminalFormatter: 
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN=""; BRIGHT_GREEN = ""; BRIGHT_MAGENTA = "";
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width(): return 80


def load_environment_variables():
    """Loads environment variables from a .env file if python-dotenv is installed."""
    # print(f"{TerminalFormatter.DIM}Attempting to load environment variables from .env...{TerminalFormatter.RESET}") # Can be noisy
    loaded = load_dotenv_file()
    # if loaded: print(f"{TerminalFormatter.DIM}Environment variables loaded successfully.{TerminalFormatter.RESET}")


def get_help_text() -> str:
    """Generates the help text for user commands."""
    TF = TerminalFormatter # Use an alias for brevity
    return f"""
{TF.YELLOW}{TF.BOLD}Available Commands:{TF.RESET}
 {TF.DIM}/exit{TF.RESET}                - Exit the application (saves current conversation).
 {TF.DIM}/quit{TF.RESET}                - Alias for /exit.
 {TF.DIM}/help{TF.RESET}                - Show this help message.
 {TF.DIM}/go <area_name>{TF.RESET}      - Move to a new area (e.g., /go Tavern). (Supports partial matching)
 {TF.DIM}/talk <npc_name|.>{TF.RESET} - Start talking to an NPC in the current area (e.g., /talk Jorin).
                        Use '.' for a random NPC in the area. (Supports partial matching)
 {TF.DIM}/who{TF.RESET}                 - List NPCs available in the current area.
 {TF.DIM}/whereami{TF.RESET}            - Show your current area and who you're talking to.
 {TF.DIM}/npcs{TF.RESET}                - List all known NPCs grouped by area.
 {TF.DIM}/stats{TF.RESET}               - Show statistics for the last LLM response.
 {TF.DIM}/session_stats{TF.RESET}       - Show aggregated statistics for the current NPC conversation.
 {TF.DIM}/clear{TF.RESET}               - Clear the conversation history with the current NPC (in memory).
 {TF.DIM}/history{TF.RESET}             - Show the raw JSON history for the current conversation.
 {TF.DIM}/hint{TF.RESET}                - Get a hint related to your current conversation/NPC.
 {TF.DIM}/inventory{TF.RESET}           - Display your current inventory.
 {TF.DIM}/inv{TF.RESET}                 - Alias for /inventory.
 {TF.DIM}/give <item_name>{TF.RESET}    - Give an item from your inventory to the current NPC. 
                        (e.g., /give Rival's Ledger) 
"""
# {TF.DIM}/profile{TF.RESET}             - View your player profile and known rumors. (Future)

def format_storyboard_for_prompt(story: str, max_length: int = 300) -> str:
    """Truncates and formats the storyboard for inclusion in prompts."""
    if not isinstance(story, str): return "[Invalid Storyboard Data]"
    if len(story) > max_length:
        truncated = story[:max_length].rsplit(' ', 1)[0] # Try to cut at a word boundary
        return truncated + "..."
    return story

def format_npcs_list(npcs_list: List[Dict[str, Any]]) -> str:
    """Formats the list of NPCs grouped by area for the /npcs command."""
    if not npcs_list:
        return f"{TerminalFormatter.YELLOW}No NPCs found in the loaded data.{TerminalFormatter.RESET}"

    output = [f"\n{TerminalFormatter.YELLOW}{TerminalFormatter.BOLD}Known NPCs:{TerminalFormatter.RESET}"]
    current_area_display = None 

    sorted_npcs = sorted(npcs_list, key=lambda x: (x.get('area', 'Unknown').lower(), x.get('name', 'Unknown').lower()))

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
    print(f"--- Running Minimal main_utils Tests ---")
    test_errors = []

    print("\nTesting load_environment_variables()...")
    try:
        load_environment_variables()
        print("  load_environment_variables() executed.")
    except Exception as e:
        print(f"  Error during load_environment_variables(): {e}"); test_errors.append("load_env")

    print("\nTesting get_help_text()...")
    try:
        help_text = get_help_text()
        print(f"  Generated help text (length: {len(help_text)} chars)")
        assert "/inventory" in help_text # Check for new command
        assert "/give <item_name>" in help_text # Check for new command
        print("  Help text content seems OK.")
    except Exception as e:
        print(f"  Error during get_help_text(): {e}"); test_errors.append("get_help")

    print("\nTesting format_storyboard_for_prompt()...")
    try:
        short_story = "This is a short story."
        long_story = "This is a very long story that definitely needs to be truncated because it exceeds the default maximum length quite significantly. We need to see the ellipsis."
        max_len = 50 
        formatted_short = format_storyboard_for_prompt(short_story, max_length=max_len)
        assert formatted_short == short_story
        formatted_long = format_storyboard_for_prompt(long_story, max_length=max_len)
        assert formatted_long.endswith("...") and len(formatted_long) <= max_len + 3
        formatted_none = format_storyboard_for_prompt(None, max_length=max_len) # type: ignore
        assert formatted_none == "[Invalid Storyboard Data]"
        print("  Storyboard formatting seems OK.")
    except Exception as e:
        print(f"  Error during format_storyboard_for_prompt(): {e}"); test_errors.append("format_story")

    print("\nTesting format_npcs_list()...")
    try:
        empty_list = []
        single_npc = [{"area": "Tavern", "name": "Bob", "role": "Barkeeper"}]
        multi_npc = [
            {"area": "City", "name": "Guard Anna", "role": "Guard"},
            {"area": "Forest", "name": "Elara", "role": "Druid"},
            {"area": "City", "name": "Merchant Zed", "role": "Trader"},
        ]
        formatted_empty = format_npcs_list(empty_list)
        assert "No NPCs found" in formatted_empty
        formatted_single = format_npcs_list(single_npc)
        assert "Tavern" in formatted_single and "Bob (Barkeeper)" in formatted_single
        formatted_multi = format_npcs_list(multi_npc)
        assert "City" in formatted_multi and "Forest" in formatted_multi
        assert formatted_multi.find("Guard Anna") < formatted_multi.find("Merchant Zed")
        print("  NPC list formatting seems OK.")
    except Exception as e:
        print(f"  Error during format_npcs_list(): {e}"); test_errors.append("format_npcs")

    print("\n--- main_utils Tests Summary ---")
    if not test_errors:
        print(f"{TerminalFormatter.GREEN}All minimal tests PASSED.{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.RED}Some tests FAILED: {', '.join(test_errors)}{TerminalFormatter.RESET}")

