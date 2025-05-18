# Path: main.py
# MODIFIED: Added --profile-analysis-model argument

import os
import sys
import argparse
import traceback

# --- Load Environment Variables FIRST ---
try:
    from main_utils import load_environment_variables
    load_environment_variables()
except ImportError as e:
    print(f"Warning: Could not import/run load_environment_variables from main_utils: {e}")
    print("Environment variables from .env might not be loaded.")

# --- Import Custom Components ---
try:
    from terminal_formatter import TerminalFormatter
    from db_manager import DbManager
    from main_core import run_interaction_loop
    from main_utils import get_help_text
except ImportError as e:
    class TF: RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"; YELLOW = "\033[93m"; DIM = "\033[2m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; BRIGHT_CYAN = "\033[96m"; BG_BLUE = "\033[44m"; BRIGHT_WHITE = "\033[97m"; BG_GREEN = "\033[42m"; BLACK = "\033[30m";
    print(f"{TF.RED}Fatal Error: Could not import a required module in main.py: {e}{TF.RESET}")
    print("Please ensure db_manager.py, main_core.py, main_utils.py, and terminal_formatter.py are present.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Eldoria Dialogue System - An AI-Assisted Roleplaying CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Mockup/DB Mode
    parser.add_argument(
        "--mockup", action="store_true",
        help="Force using the mockup file system instead of a real database."
    )
    parser.add_argument(
        "--mockup-dir", default="database",
        help="Directory for the mockup file system."
    )

    # Starting Position
    parser.add_argument(
        "--area", default=None,
        help="Attempt to start in this area (case-insensitive)."
    )
    parser.add_argument(
        "--npc", default=None,
        help="Attempt to start talking to this NPC (case-insensitive). Requires --area."
    )

    # LLM & Interaction Options
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free"), # Added a common free default
        help="LLM model identifier for NPC dialogue. Overrides OPENROUTER_DEFAULT_MODEL env var."
    )
    parser.add_argument(
        "--profile-analysis-model", # NEW ARGUMENT
        default=os.environ.get("PROFILE_ANALYSIS_MODEL"), # Default from Env Var if set
        help="LLM model for psychological profile analysis. If not set, uses --model. (e.g., 'google/gemma-2-2b-it:free' for a lighter model)"
    )
    parser.add_argument(
        "--no-stream", action="store_true",
        help="Disable streaming responses from the LLM."
    )
    parser.add_argument(
        "--show-stats", action="store_true",
        help="Show LLM turn statistics automatically after each response."
    )
    parser.add_argument(
        "--player", default="Player1",
        help="Identifier for the player."
    )

    args = parser.parse_args()

    TF_main = TerminalFormatter
    print(f"\n{TF_main.BG_BLUE}{TF_main.BRIGHT_WHITE}{TF_main.BOLD} ELDORIA DIALOGUE SYSTEM {TF_main.RESET}")
    print(f"{TF_main.BRIGHT_CYAN}{'=' * 50}{TF_main.RESET}")

    USE_MOCKUP = args.mockup
    MOCKUP_DIR = args.mockup_dir
    USE_STREAM = not args.no_stream
    AUTO_SHOW_STATS = args.show_stats
    DIALOGUE_MODEL_NAME = args.model
    # Use specified profile analysis model, or fallback to dialogue model if not specified
    PROFILE_MODEL_NAME = args.profile_analysis_model if args.profile_analysis_model else DIALOGUE_MODEL_NAME
    PLAYER_ID = args.player
    INITIAL_AREA = args.area
    INITIAL_NPC = args.npc if INITIAL_AREA else None

    if INITIAL_NPC and not INITIAL_AREA:
        print(f"{TF_main.YELLOW}Warning: --npc ('{INITIAL_NPC}') provided without --area. Ignoring starting NPC.{TF_main.RESET}")
        INITIAL_NPC = None

    if not TF_main.supports_ansi():
        print(f"{TF_main.YELLOW}Note: Terminal might not support ANSI formatting fully.{TF_main.RESET}")

    print(f"\n{TF_main.DIM}[INIT] Initializing DB Manager...{TF_main.RESET}")
    db = None
    try:
        db = DbManager(use_mockup=USE_MOCKUP, mockup_dir=MOCKUP_DIR)
        if not USE_MOCKUP and db.db_config and db.db_config.get('host'):
            # print(f"{TF_main.DIM}Attempting test connection to real DB...{TF.RESET}")
            try:
                conn_test = db.connect()
                conn_test.close()
                # print(f"{TF_main.GREEN}✅ Real DB connection test successful.{TF_main.RESET}")
            except Exception as conn_e:
                print(f"{TF_main.YELLOW}⚠️ Real DB connection test failed: {conn_e}{TF_main.RESET}")
                print(f"{TF_main.YELLOW}   Ensure DB is running and config (env vars) is correct.{TF_main.RESET}")
        # else:
            # print(f"{TF_main.GREEN}✅ DB Manager initialized ({'Mockup Mode' if USE_MOCKUP else 'Real DB Mode - Config Read'}).{TF_main.RESET}")
        db.ensure_db_schema() # Ensure schema (including PlayerProfiles) is checked/created
    except Exception as e:
        print(f"{TF_main.RED}❌ Fatal Error Initializing DB Manager: {e}{TF_main.RESET}")
        traceback.print_exc()
        sys.exit(1)

    print(f"\n{TF_main.DIM}[INIT] Loading storyboard...{TF_main.RESET}")
    story = ""
    try:
        story_data = db.get_storyboard()
        story = story_data.get("description", "[Storyboard description missing or failed to load]")
        # print(f"{TF_main.DIM}✅ Story loaded ({len(story)} chars).{TF_main.RESET}")
    except Exception as e:
        print(f"{TF_main.RED}❌ Error loading storyboard via DbManager: {e}. Using default.{TF_main.RESET}")
        story = "[Default story due to loading error]"

    print(f"\n{TF_main.DIM}Starting interaction loop...{TF_main.RESET}")
    print(f"{TF_main.DIM}NPC Dialogue Model: {DIALOGUE_MODEL_NAME}{TF_main.RESET}")
    print(f"{TF_main.DIM}Profile Analysis Model: {PROFILE_MODEL_NAME}{TF_main.RESET}")
    try:
        run_interaction_loop(
            db=db,
            story=story,
            initial_area=INITIAL_AREA,
            initial_npc_name=INITIAL_NPC,
            model_name=DIALOGUE_MODEL_NAME, # For NPC dialogue
            profile_analysis_model_name=PROFILE_MODEL_NAME, # For profile analysis
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
