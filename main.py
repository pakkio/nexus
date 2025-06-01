from dotenv import load_dotenv
load_dotenv()
import os
import sys
import argparse
import traceback

try:
  from main_utils import load_environment_variables
  load_environment_variables()
except ImportError as e:
  print(f"Warning: Could not import/run load_environment_variables from main_utils: {e}")
  print("Environment variables from .env might not be loaded.")

try:
  from terminal_formatter import TerminalFormatter
  from db_manager import DbManager
  from main_core import run_interaction_loop
  from main_utils import get_help_text
  from wise_guide_selector import get_wise_guide_npc_name # MODIFIED: Import wise guide selector
except ImportError as e:
  class TF: RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"; YELLOW = "\033[93m"; DIM = "\033[2m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; BRIGHT_CYAN = "\033[96m"; BG_BLUE = "\033[44m"; BRIGHT_WHITE = "\033[97m"; BG_GREEN = "\033[42m"; BLACK = "\033[30m";
  print(f"{TF.RED}Fatal Error: Could not import a required module in main.py: {e}{TF.RESET}")
  print("Please ensure all dependencies like wise_guide_selector.py are present.")
  sys.exit(1)

def main():
  parser = argparse.ArgumentParser(
    description="Eldoria Dialogue System - An AI-Assisted Roleplaying CLI",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument(
    "--mockup", action="store_true",
    help="Force using the mockup file system instead of a real database."
  )
  parser.add_argument(
    "--mockup-dir", default="database",
    help="Directory for the mockup file system."
  )
  parser.add_argument(
    "--area", default="Sanctum of Whispers", # Default start, could be overridden by wise guide logic if --npc is not set
    help="Attempt to start in this area (case-insensitive)."
  )
  parser.add_argument(
    # MODIFIED: Default NPC is None, can be set by wise guide or explicit --npc
    "--npc", default=None,
    help="Attempt to start talking to this NPC (case-insensitive). Overrides wise guide as starting NPC. Requires --area."
  )
  parser.add_argument(
    "--model",
    default=os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free"),
    help="LLM model identifier for NPC dialogue. Overrides OPENROUTER_DEFAULT_MODEL env var."
  )
  parser.add_argument(
    "--profile-analysis-model",
    default=os.environ.get("PROFILE_ANALYSIS_MODEL"),
    help="LLM model for psychological profile analysis. If not set, uses --model."
  )
  parser.add_argument(
    "--guide-selection-model", # NEW: Model for wise guide selection
    default=os.environ.get("GUIDE_SELECTION_MODEL", "openai/gpt-4.1-nano"), # Default to a smaller model for this task
    help="LLM model for selecting the wise guide. If not set, uses a default (e.g., gemma-2-2b-it:free)."
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
    "--debug", action="store_true",
    help="Enable verbose debug output including profile updates."
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
  DEBUG_MODE = args.debug
  DIALOGUE_MODEL_NAME = args.model
  PROFILE_MODEL_NAME = args.profile_analysis_model if args.profile_analysis_model else DIALOGUE_MODEL_NAME
  GUIDE_SELECTION_MODEL_NAME = args.guide_selection_model # NEW
  PLAYER_ID = args.player
  INITIAL_AREA = args.area
  # INITIAL_NPC will be determined after wise_guide selection if not explicitly set by user

  if not TF_main.supports_ansi():
    print(f"{TF_main.YELLOW}Note: Terminal might not support ANSI formatting fully.{TF_main.RESET}")

  print(f"\n{TF_main.DIM}[INIT] Initializing DB Manager...{TF_main.RESET}")
  db = None
  try:
    db = DbManager(use_mockup=USE_MOCKUP, mockup_dir=MOCKUP_DIR)
    if not USE_MOCKUP and db.db_config and db.db_config.get('host'):
      try:
        conn_test = db.connect()
        conn_test.close()
      except Exception as conn_e:
        print(f"{TF_main.YELLOW}⚠️ Real DB connection test failed: {conn_e}{TF_main.RESET}")
        print(f"{TF_main.YELLOW}   Ensure DB is running and config (env vars) is correct.{TF_main.RESET}")
    db.ensure_db_schema()
  except Exception as e:
    print(f"{TF_main.RED}❌ Fatal Error Initializing DB Manager: {e}{TF_main.RESET}")
    traceback.print_exc()
    sys.exit(1)

  print(f"\n{TF_main.DIM}[INIT] Loading storyboard...{TF_main.RESET}")
  story = ""
  try:
    story_data = db.get_storyboard()
    story = story_data.get("description", "[Storyboard description missing or failed to load]")
  except Exception as e:
    print(f"{TF_main.RED}❌ Error loading storyboard via DbManager: {e}. Using default.{TF_main.RESET}")
    story = "[Default story due to loading error]"

  # MODIFIED: Determine wise guide
  print(f"\n{TF_main.DIM}[INIT] Determining wise guide for the story...{TF_main.RESET}")
  wise_guide_npc_name = get_wise_guide_npc_name(story, db, GUIDE_SELECTION_MODEL_NAME)
  if wise_guide_npc_name:
    print(f"{TF_main.BRIGHT_GREEN}[INIT] Wise guide for this story: {wise_guide_npc_name}{TF_main.RESET}")
  else:
    print(f"{TF_main.YELLOW}[INIT] No specific wise guide determined by LLM. /hint might be limited.{TF_main.RESET}")

  # MODIFIED: Determine initial NPC based on args and wise guide
  INITIAL_NPC = args.npc # User's explicit choice takes precedence
  if INITIAL_NPC and not INITIAL_AREA: # User specified NPC but not area
    print(f"{TF_main.YELLOW}Warning: --npc ('{INITIAL_NPC}') provided without --area. Ignoring starting NPC.{TF_main.RESET}")
    INITIAL_NPC = None
  elif not INITIAL_NPC and wise_guide_npc_name: # No explicit NPC, but wise guide found
    # We could default to starting with the wise guide, or require player to /talk
    # For now, let's keep --area and --npc as primary starting points. Wise guide is for /hint.
    # If you want to default start with wise_guide: INITIAL_NPC = wise_guide_npc_name
    print(f"{TF_main.DIM}[INIT] Player will start in '{INITIAL_AREA}'. To talk to wise guide '{wise_guide_npc_name}', use /talk command if not starting there.{TF_main.RESET}")
    pass


  print(f"\n{TF_main.DIM}Starting interaction loop...{TF_main.RESET}")
  print(f"{TF_main.DIM}NPC Dialogue Model: {DIALOGUE_MODEL_NAME}{TF_main.RESET}")
  print(f"{TF_main.DIM}Profile Analysis Model: {PROFILE_MODEL_NAME}{TF_main.RESET}")
  print(f"{TF_main.DIM}Wise Guide Selection Model: {GUIDE_SELECTION_MODEL_NAME}{TF_main.RESET}")
  if DEBUG_MODE:
    print(f"{TF_main.YELLOW}Debug mode enabled - verbose profiling output active{TF_main.RESET}")

  try:
    run_interaction_loop(
      db=db,
      story=story,
      initial_area=INITIAL_AREA,
      initial_npc_name=INITIAL_NPC,
      model_name=DIALOGUE_MODEL_NAME,
      profile_analysis_model_name=PROFILE_MODEL_NAME,
      use_stream=USE_STREAM,
      auto_show_stats=AUTO_SHOW_STATS,
      debug_mode=DEBUG_MODE,
      player_id=PLAYER_ID,
      wise_guide_npc_name=wise_guide_npc_name # MODIFIED: Pass wise guide name
    )
  except Exception as e:
    print(f"\n{TF_main.RED}❌ Critical Error during execution: {e}{TF_main.RESET}")
    traceback.print_exc()
    sys.exit(1)
  finally:
    print(f"\n{TF_main.DIM}Application closing.{TF_main.RESET}")

if __name__ == "__main__":
  main()