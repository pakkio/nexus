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
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import a required module in main.py: {e}{TerminalFormatter.RESET}")
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
        help="Identifier for the player (currently unused)."
    )

    args = parser.parse_args()

    # --- Initial Setup & Welcome Message ---
    print(f"\n{TerminalFormatter.BG_BLUE}{TerminalFormatter.BRIGHT_WHITE}{TerminalFormatter.BOLD} ELDORIA DIALOGUE SYSTEM {TerminalFormatter.RESET}")
    print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")

    # Determine effective settings
    # Mockup mode is default unless DB connection is viable & requested implicitly/explicitly
    # DbManager's __init__ handles the logic of checking env vars if args.mockup is False
    USE_MOCKUP = args.mockup # Force mockup if flag is set
    MOCKUP_DIR = args.mockup_dir
    USE_STREAM = not args.no_stream
    AUTO_SHOW_STATS = args.show_stats # Use the positive flag
    MODEL_NAME = args.model # Pass along the potentially None value
    PLAYER_ID = args.player
    INITIAL_AREA = args.area
    # Only set initial NPC if initial area is also provided
    INITIAL_NPC = args.npc if INITIAL_AREA else None

    if INITIAL_NPC and not INITIAL_AREA:
        # This case is now handled better in run_interaction_loop, but good to keep maybe
        print(f"{TerminalFormatter.YELLOW}Warning: --npc ('{INITIAL_NPC}') provided without --area. Ignoring starting NPC.{TerminalFormatter.RESET}")
        INITIAL_NPC = None

    # Check ANSI support for user info
    if not TerminalFormatter.supports_ansi():
        print(f"{TerminalFormatter.YELLOW}Note: Terminal might not support ANSI formatting fully.{TerminalFormatter.RESET}")

    # --- Initialize DB Manager ---
    print(f"\n{TerminalFormatter.DIM}[INIT] Initializing DB Manager...{TerminalFormatter.RESET}")
    db = None # Initialize db to None
    try:
        # Pass use_mockup explicitly, DbManager handles config loading from env if not mockup
        db = DbManager(use_mockup=USE_MOCKUP, mockup_dir=MOCKUP_DIR)
        # Optional: Perform a quick connection test if *not* in mockup mode
        if not USE_MOCKUP and db.db_config and db.db_config.get('host'):
            print(f"{TerminalFormatter.DIM}Attempting test connection to real DB...{TerminalFormatter.RESET}")
            try:
                conn_test = db.connect() # Should raise error if connection fails
                conn_test.close()
                print(f"{TerminalFormatter.GREEN}✅ Real DB connection test successful.{TerminalFormatter.RESET}")
            except Exception as conn_e:
                print(f"{TerminalFormatter.YELLOW}⚠️ Real DB connection test failed: {conn_e}{TerminalFormatter.RESET}")
                print(f"{TerminalFormatter.YELLOW}   Ensure DB is running and config (env vars) is correct.{TerminalFormatter.RESET}")
                # Decide if this should be fatal? Maybe not, allow app to start but DB ops will fail later.
        else:
            print(f"{TerminalFormatter.GREEN}✅ DB Manager initialized ({'Mockup Mode' if USE_MOCKUP else 'Real DB Mode - Config Read'}).{TerminalFormatter.RESET}")

    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Fatal Error Initializing DB Manager: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        sys.exit(1)

    # --- Load Storyboard ---
    print(f"\n{TerminalFormatter.DIM}[INIT] Loading storyboard...{TerminalFormatter.RESET}")
    story = "" # Initialize story
    try:
        story_data = db.get_storyboard() # Returns dict
        story = story_data.get("description", "[Storyboard description missing or failed to load]")
        print(f"{TerminalFormatter.DIM}✅ Story loaded ({len(story)} chars).{TerminalFormatter.RESET}")
    except Exception as e:
        print(f"{TerminalFormatter.RED}❌ Error loading storyboard via DbManager: {e}. Using default.{TerminalFormatter.RESET}")
        story = "[Default story due to loading error]" # Fallback story

    # --- Start Interaction Loop ---
    print(f"\n{TerminalFormatter.DIM}Starting interaction loop...{TerminalFormatter.RESET}")
    try:
        run_interaction_loop(
            db=db,
            story=story,
            initial_area=INITIAL_AREA,
            initial_npc_name=INITIAL_NPC,
            model_name=MODEL_NAME, # Pass model name from args/env
            use_stream=USE_STREAM,
            auto_show_stats=AUTO_SHOW_STATS,
            player_id=PLAYER_ID
        )
    except Exception as e:
        # Catch critical errors during the main loop execution
        print(f"\n{TerminalFormatter.RED}❌ Critical Error during execution: {e}{TerminalFormatter.RESET}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Optional: Add any final cleanup here if needed
        print(f"\n{TerminalFormatter.DIM}Application closing.{TerminalFormatter.RESET}")


if __name__ == "__main__":
    main()
