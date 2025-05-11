# Path: main_utils.py

import os
from typing import Dict, List, Any

# --- Environment Loading ---
try:
    # Use a different alias if 'load_dotenv' name is used elsewhere
    from dotenv import load_dotenv as load_dotenv_file
    # print("main_utils: dotenv found.") # Optional debug print
except ImportError:
    print("Warning (main_utils): python-dotenv not found. .env file will not be loaded.")
    def load_dotenv_file(): # type: ignore # Define dummy function
        pass

# --- Terminal Formatter ---
# Assuming TerminalFormatter is available, either imported globally or defined/imported here
try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("Warning (main_utils): terminal_formatter not found. Using basic fallback formatting.")
    class TerminalFormatter: # Basic Fallback
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN="" # Add more if needed
        # Basic placeholder methods or replicate basic ANSI codes if essential

# --- Environment Loading Function ---
def load_environment_variables():
    """Loads environment variables from a .env file if python-dotenv is installed."""
    print(f"{TerminalFormatter.DIM}Attempting to load environment variables from .env...{TerminalFormatter.RESET}")
    loaded = load_dotenv_file()
    if loaded:
        print(f"{TerminalFormatter.DIM}Environment variables loaded successfully.{TerminalFormatter.RESET}")
    # else:
    # print(f"{TerminalFormatter.DIM}.env file not found or dotenv package missing.{TerminalFormatter.RESET}")

# --- Help Text ---
def get_help_text() -> str:
    """Generates the help text for user commands."""
    # Use TerminalFormatter for colors if available
    YELLOW = TerminalFormatter.YELLOW
    DIM = TerminalFormatter.DIM
    RESET = TerminalFormatter.RESET
    BOLD = TerminalFormatter.BOLD

    return f"""
{YELLOW}{BOLD}Available Commands:{RESET}
 {DIM}/exit{RESET}          - Exit the application (saves current conversation).
 {DIM}/help{RESET}          - Show this help message.
 {DIM}/go <area_name>{RESET} - Move to a new area (e.g., /go Tavern, /go "City Market").
 {DIM}/talk <npc_name>{RESET} - Start talking to an NPC in the current area (e.g., /talk Jorin).
 {DIM}/who{RESET}           - List NPCs available in the current area.
 {DIM}/whereami{RESET}      - Show your current area and who you're talking to.
 {DIM}/npcs{RESET}          - List all known NPCs grouped by area.
 {DIM}/stats{RESET}         - Show statistics for the last LLM response.
 {DIM}/session_stats{RESET} - Show aggregated statistics for the current NPC conversation.
 {DIM}/clear{RESET}         - Clear the conversation history with the current NPC (in memory).
 {DIM}/history{RESET}       - Show the raw JSON history for the current conversation.
"""

# --- Storyboard Formatting Utility ---
def format_storyboard_for_prompt(story: str, max_length: int = 300) -> str:
    """Truncates and formats the storyboard for inclusion in prompts."""
    if not isinstance(story, str): # Basic type check
        return "[Invalid Storyboard Data]"
    if len(story) > max_length:
        # Truncate cleanly at a word boundary near the max_length if possible
        truncated = story[:max_length].rsplit(' ', 1)[0]
        return truncated + "..."
    return story

# --- NPC Listing Formatting Utility ---
def format_npcs_list(npcs_list: List[Dict[str, Any]]) -> str:
    """Formats the list of NPCs grouped by area for the /npcs command."""
    if not npcs_list:
        return f"{TerminalFormatter.YELLOW}No NPCs found in the loaded data.{TerminalFormatter.RESET}"

    output = [f"\n{TerminalFormatter.YELLOW}{TerminalFormatter.BOLD}Known NPCs:{TerminalFormatter.RESET}"]
    current_area = None # Use None to handle first area correctly

    # Sort list by area, then name (case-insensitive)
    # Assumes list_npcs_by_area already sorted, but sorting here ensures it
    sorted_npcs = sorted(npcs_list, key=lambda x: (x.get('area', 'Unknown').lower(), x.get('name', 'Unknown').lower()))

    for npc_info in sorted_npcs:
        area = npc_info.get('area', 'Unknown Area')
        name = npc_info.get('name', 'Unknown NPC')
        role = npc_info.get('role', 'Unknown Role') # Provide default role

        # Check if area changed
        if area != current_area:
            # Add a newline before new area except for the very first one
            if current_area is not None:
                output.append("") # Add space between areas
            current_area = area
            output.append(f"{TerminalFormatter.BRIGHT_CYAN}{current_area}{TerminalFormatter.RESET}") # Use a different color for area name

        # Add NPC info (use dim for less emphasis)
        output.append(f"  {TerminalFormatter.DIM}- {name} ({role}){TerminalFormatter.RESET}")

    return "\n".join(output)

# You could add more utility functions here as needed,
# e.g., input cleaning, validation helpers, etc.
# ===========================================
# Minimal main_utils Test Block
# ===========================================
if __name__ == "__main__":
    print(f"--- Running Minimal main_utils Tests ---")
    test_errors = []

    # --- Test load_environment_variables ---
    print("\nTesting load_environment_variables()...")
    try:
        # Call it mainly to check for runtime errors
        load_environment_variables()
        print("  load_environment_variables() executed without crashing.")
    except Exception as e:
        print(f"  Error during load_environment_variables(): {e}")
        test_errors.append("load_environment_variables")

    # --- Test get_help_text ---
    print("\nTesting get_help_text()...")
    try:
        help_text = get_help_text()
        print(f"  Generated help text (length: {len(help_text)} chars)")
        # Basic checks
        assert "/exit" in help_text
        assert "/go <area_name>" in help_text
        assert "/talk <npc_name>" in help_text
        assert "/whereami" in help_text
        print("  Help text content seems OK.")
    except Exception as e:
        print(f"  Error during get_help_text(): {e}")
        test_errors.append("get_help_text")

    # --- Test format_storyboard_for_prompt ---
    print("\nTesting format_storyboard_for_prompt()...")
    try:
        short_story = "This is a short story."
        long_story = "This is a very long story that definitely needs to be truncated because it exceeds the default maximum length quite significantly. We need to see the ellipsis."
        max_len = 50 # Use a shorter length for easier testing

        formatted_short = format_storyboard_for_prompt(short_story, max_length=max_len)
        print(f"  Short story formatted: '{formatted_short}'")
        assert formatted_short == short_story

        formatted_long = format_storyboard_for_prompt(long_story, max_length=max_len)
        print(f"  Long story formatted (max={max_len}): '{formatted_long}'")
        assert formatted_long.endswith("...")
        assert len(formatted_long) <= max_len + 3 # Allow for ellipsis

        formatted_none = format_storyboard_for_prompt(None, max_length=max_len)
        print(f"  None input formatted: '{formatted_none}'")
        assert formatted_none == "[Invalid Storyboard Data]"

        print("  Storyboard formatting seems OK.")
    except Exception as e:
        print(f"  Error during format_storyboard_for_prompt(): {e}")
        test_errors.append("format_storyboard_for_prompt")


    # --- Test format_npcs_list ---
    print("\nTesting format_npcs_list()...")
    try:
        # Sample data
        empty_list = []
        single_npc = [{"area": "Tavern", "name": "Bob", "role": "Barkeeper"}]
        multi_npc = [
            {"area": "City", "name": "Guard Anna", "role": "Guard"},
            {"area": "Forest", "name": "Elara", "role": "Druid"},
            {"area": "City", "name": "Merchant Zed", "role": "Trader"},
            {"area": "Forest", "name": "Grognak", "role": "Hermit"}, # Ensure sorting works
            {"area": "Unknown Area", "name": "Ghost", "role": "Spirit"},
        ]

        print("\n  --- Empty List ---")
        formatted_empty = format_npcs_list(empty_list)
        print(formatted_empty)
        assert "No NPCs found" in formatted_empty

        print("\n  --- Single NPC ---")
        formatted_single = format_npcs_list(single_npc)
        print(formatted_single)
        assert "Tavern" in formatted_single
        assert "Bob (Barkeeper)" in formatted_single

        print("\n  --- Multi NPC ---")
        formatted_multi = format_npcs_list(multi_npc)
        print(formatted_multi)
        # Check if areas are present (uses bright cyan potentially)
        assert "City" in formatted_multi
        assert "Forest" in formatted_multi
        assert "Unknown Area" in formatted_multi
        # Check if NPCs are present
        assert "Guard Anna (Guard)" in formatted_multi
        assert "Merchant Zed (Trader)" in formatted_multi
        assert "Elara (Druid)" in formatted_multi
        assert "Grognak (Hermit)" in formatted_multi
        # Check sorting (Anna before Zed, Elara before Grognak)
        assert formatted_multi.find("Guard Anna") < formatted_multi.find("Merchant Zed")
        assert formatted_multi.find("Elara") < formatted_multi.find("Grognak")

        print("  NPC list formatting seems OK.")
    except Exception as e:
        print(f"  Error during format_npcs_list(): {e}")
        import traceback
        traceback.print_exc() # Print full traceback for list formatting errors
        test_errors.append("format_npcs_list")

    # --- Final Result ---
    print("\n--- main_utils Tests Summary ---")
    if not test_errors:
        print(f"{TerminalFormatter.GREEN}All minimal tests PASSED.{TerminalFormatter.RESET}")
    else:
        print(f"{TerminalFormatter.RED}Some tests FAILED: {', '.join(test_errors)}{TerminalFormatter.RESET}")
