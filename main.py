# Path: main.py
# (Reviewing existing code - applying minor consistency checks)

import os
import sys
import argparse
import traceback

# --- Load Environment Variables FIRST ---
# Ensure utils loads dotenv early, before other imports might need env vars
try:
    from main_utils import load_environment_variables
    load_environment_variables() # Load .env before importing other modules
except ImportError as e:
    print(f"Warning: Could not import/run load_environment_variables from main_utils: {e}")
    print("Environment variables from .env might not be loaded.")

# --- Import Custom Components ---
# Use try-except for robustness, though these are essential
try:
    from terminal_formatter import TerminalFormatter
    from db_manager import DbManager
    from main_core import run_interaction_loop
    # main_utils already imported above for load_dotenv
    from main_utils import get_help_text # Example if needed directly here
except ImportError as e:
    # Fallback TerminalFormatter for initial error message if it's the one missing
    class TF: RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"; YELLOW = "\033[93m"; DIM = "\033[2m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; BRIGHT_CYAN = "\033[96m"; BG_BLUE = "\033[44m"; BRIGHT_WHITE = "\033[97m"; BG_GREEN = "\033[42m"; BLACK = "\033[30m";
    print(f"{TF.RED}Fatal Error: Could not import a required module in main.py: {e}{TF.RESET}")
    print("Please ensure db_manager.py, main_core.py, main_utils.py, and terminal_formatter.py are present.")
    sys.exit(1)


def main():
    # --- Argument Parsing ---
    # Use ArgumentDefaultsHelpFormatter to show default values in --help
    parser = argparse.ArgumentParser(
        description="Eldoria Dialogue System - An AI-Assisted Roleplaying CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Mockup/DB Mode
    parser.add_argument(
        "--mockup",
        action="store_true",
        help="Force using the mockup file system instead of a real database."
    )
    parser.add_argument(
        "--mockup-dir",
        default="database", # Default directory name if mockup is used
        help="Directory for the mockup file system."
    )
    # Note: Real DB connection is implicitly enabled if --mockup is NOT set
    # and DB environment variables are configured correctly (checked in DbManager).

    # Starting Position (Optional)
    parser.add_argument(
        "--area",
        default=None,
        help="Attempt to start in this area (case-insensitive). Requires valid area in data."
    )
    parser.add_argument(
        "--npc",
        default=None,
        help="Attempt to start talking to this NPC (case-insensitive). Requires --area and valid NPC in that area."
    )

    # LLM & Interaction Options
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENROUTER_DEFAULT_MODEL"), # Default from Env Var if set
        help="LLM model identifier to use (e.g., 'google/gemma-2-9b-it:free'). Overrides OPENROUTER_DEFAULT_MODEL env var."
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming responses from the LLM."
    )
    parser.add_argument(
        "--show-stats", # Changed from --no-stats to be opt-in
        action="store_true",
        help="Show LLM turn statistics automatically after each response."
    )
    parser.add_argument(
        "--player",
        default="Player1", # Default player identifier
        help="Identifier for the player." # Player ID is used for saving state
    )

    args = parser.parse_args()

    # --- Initial Setup & Welcome Message ---
    TF_main = TerminalFormatter # Use the successfully imported one
    print(f"\n{TF_main.BG_BLUE}{TF_main.BRIGHT_WHITE}{TF_main.BOLD} ELDORIA DIALOGUE SYSTEM {TF_main.RESET}")
    print(f"{TF_main.BRIGHT_CYAN}{'=' * 50}{TF_main.RESET}")

    # Determine effective settings
    USE_MOCKUP = args.mockup
    MOCKUP_DIR = args.mockup_dir
    USE_STREAM = not args.no_stream
    AUTO_SHOW_STATS = args.show_stats
    MODEL_NAME = args.model
    PLAYER_ID = args.player
    INITIAL_AREA = args.area
    INITIAL_NPC = args.npc if INITIAL_AREA else None

    if INITIAL_NPC and not INITIAL_AREA:
        print(f"{TF_main.YELLOW}Warning: --npc ('{INITIAL_NPC}') provided without --area. Ignoring starting NPC.{TF_main.RESET}")
        INITIAL_NPC = None

    if not TF_main.supports_ansi():
        print(f"{TF_main.YELLOW}Note: Terminal might not support ANSI formatting fully.{TF_main.RESET}")

    # --- Initialize DB Manager ---
    print(f"\n{TF_main.DIM}[INIT] Initializing DB Manager...{TF_main.RESET}")
    db = None
    try:
        db = DbManager(use_mockup=USE_MOCKUP, mockup_dir=MOCKUP_DIR)
        if not USE_MOCKUP and db.db_config and db.db_config.get('host'):
            print(f"{TF_main.DIM}Attempting test connection to real DB...{TF_main.RESET}")
            try:
                conn_test = db.connect()
                conn_test.close()
                print(f"{TF_main.GREEN}✅ Real DB connection test successful.{TF_main.RESET}")
            except Exception as conn_e:
                print(f"{TF_main.YELLOW}⚠️ Real DB connection test failed: {conn_e}{TF_main.RESET}")
                print(f"{TF_main.YELLOW}   Ensure DB is running and config (env vars) is correct.{TF_main.RESET}")
        else:
            print(f"{TF_main.GREEN}✅ DB Manager initialized ({'Mockup Mode' if USE_MOCKUP else 'Real DB Mode - Config Read'}).{TF_main.RESET}")

    except Exception as e:
        print(f"{TF_main.RED}❌ Fatal Error Initializing DB Manager: {e}{TF_main.RESET}")
        traceback.print_exc()
        sys.exit(1)

    # --- Load Storyboard ---
    print(f"\n{TF_main.DIM}[INIT] Loading storyboard...{TF_main.RESET}")
    story = ""
    try:
        story_data = db.get_storyboard()
        story = story_data.get("description", "[Storyboard description missing or failed to load]")
        print(f"{TF_main.DIM}✅ Story loaded ({len(story)} chars).{TF_main.RESET}")
    except Exception as e:
        print(f"{TF_main.RED}❌ Error loading storyboard via DbManager: {e}. Using default.{TF_main.RESET}")
        story = "[Default story due to loading error]"

    # --- Start Interaction Loop ---
    print(f"\n{TF_main.DIM}Starting interaction loop...{TF_main.RESET}")
    try:
        run_interaction_loop(
            db=db,
            story=story,
            initial_area=INITIAL_AREA,
            initial_npc_name=INITIAL_NPC,
            model_name=MODEL_NAME,
            use_stream=USE_STREAM,
            auto_show_stats=AUTO_SHOW_STATS,
            player_id=PLAYER_ID
        )
    except Exception as e:
        print(f"\n{TF_main.RED}❌ Critical Error during execution: {e}{TF_main.RESET}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        print(f"\n{TF_main.DIM}Application closing.{TF_main.RESET}")


if __name__ == "__main__":
    main()
