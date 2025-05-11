# Path: main_core.py

import sys
import json # Though not directly used here now, often useful
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Import base components needed for setup
try:
    from terminal_formatter import TerminalFormatter
    from chat_manager import ChatSession, format_stats
    from db_manager import DbManager
    from main_utils import format_storyboard_for_prompt # Assuming this utility is used
except ImportError as e:
    # Basic fallback for TerminalFormatter if it's the one missing for the error message
    class TerminalFormatter: RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""; CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = "";
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import base modules in main_core.py: {e}{TerminalFormatter.RESET}")
    sys.exit(1)

# Import the new modules/functions
try:
    import command_processor
    import session_utils # This now contains the conversation starting logic
except ImportError as e:
    TF = TerminalFormatter # Use previously defined or imported
    print(f"{TF.RED}Fatal Error: Could not import command_processor or session_utils: {e}{TF.RESET}")
    sys.exit(1)


def run_interaction_loop(
        db: DbManager,
        story: str,
        initial_area: Optional[str],
        initial_npc_name: Optional[str], # Specific NPC to talk to via --npc
        model_name: Optional[str],
        use_stream: bool,
        auto_show_stats: bool,
        player_id: str
):
    """Runs the main user interaction loop, delegating command processing."""

    current_area: Optional[str] = None
    current_npc: Optional[Dict[str, Any]] = None
    chat_session: Optional[ChatSession] = None # This will be a ChatSession instance

    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)

    # --- Initial Area and NPC Setup ---
    if initial_area:
        print(f"{TerminalFormatter.DIM}Validating initial area '{initial_area}'...{TerminalFormatter.RESET}")
        initial_area_prefix = initial_area.lower()
        area_matches = [area for area in known_areas if area.lower().startswith(initial_area_prefix)]

        if len(area_matches) == 1:
            current_area = area_matches[0]
            print(f"{TerminalFormatter.GREEN}Initial area set to: {current_area}{TerminalFormatter.RESET}")

            if initial_npc_name: # Player specified --npc
                print(f"{TerminalFormatter.DIM}Attempting to start with specified NPC: '{initial_npc_name}'...{TerminalFormatter.RESET}")
                # Use the specific NPC starter from session_utils
                npc_data, session = session_utils.start_conversation_with_specific_npc(
                    db, player_id, current_area, initial_npc_name, model_name, story, ChatSession, TerminalFormatter
                )
                if npc_data and session:
                    current_npc = npc_data
                    chat_session = session
                else:
                    print(f"{TerminalFormatter.YELLOW}⚠️ Could not start conversation with specified NPC '{initial_npc_name}'. You can use /talk.{TerminalFormatter.RESET}")
            else: # No specific --npc, try default NPC for the area
                default_npc_data, default_session = session_utils.auto_start_default_npc_conversation(
                    db, player_id, current_area, model_name, story, ChatSession, TerminalFormatter
                )
                if default_npc_data and default_session:
                    current_npc = default_npc_data
                    chat_session = default_session
                # auto_start_default_npc_conversation prints its own status/failure messages

        elif len(area_matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area prefix '{initial_area}' is ambiguous. Matches:{TerminalFormatter.RESET}")
            for area_match in sorted(area_matches): print(f"  - {area_match}")
            print(f"{TerminalFormatter.YELLOW}Please restart with a more specific --area or use /go later.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' not found or has no NPCs.{TerminalFormatter.RESET}")
            if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(known_areas)}{TerminalFormatter.RESET}")

    elif initial_npc_name and not initial_area: # --npc specified but --area is not
        print(f"\n{TerminalFormatter.YELLOW}Warning: --npc ('{initial_npc_name}') provided without --area. Cannot start specific NPC conversation. Use /go first.{TerminalFormatter.RESET}")


    if not current_area: # No valid starting area determined
        print(f"\n{TerminalFormatter.YELLOW}No starting area. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.YELLOW} to begin.{TerminalFormatter.RESET}")


    # ===========================
    # --- Main Interaction Loop ---
    # ===========================
    while True:
        try:
            prompt_prefix = ""
            if current_npc and current_npc.get('name'):
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}Tu ({current_npc['name']}) > {TerminalFormatter.RESET}"
            elif current_area:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}Tu ({current_area}) > {TerminalFormatter.RESET}"
            else:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.BRIGHT_MAGENTA}Tu (Nowhere) > {TerminalFormatter.RESET}"

            user_input = input(prompt_prefix).strip()

            current_game_state = {
                'db': db, 'story': story,
                'current_area': current_area, 'current_npc': current_npc,
                'chat_session': chat_session, 'model_name': model_name,
                'use_stream': use_stream, 'auto_show_stats': auto_show_stats,
                'player_id': player_id,
                'ChatSession': ChatSession, # Pass the class, not an instance here for command_processor
                'TerminalFormatter': TerminalFormatter,
                'format_stats': format_stats,
            }

            handler_result = command_processor.process_input_revised(user_input, current_game_state)

            if handler_result.get('status') == 'exit':
                break

            # Update state from handler_result
            current_area = handler_result.get('current_area', current_area)
            current_npc = handler_result.get('current_npc', current_npc) # This will be updated by handle_go/handle_talk
            chat_session = handler_result.get('chat_session', chat_session)

            # If after a command (like /go that didn't auto-start), we are in an area but not talking,
            # and the user didn't just try to /talk (which would have its own feedback).
            # This condition is mostly handled by handle_go now, but as a fallback:
            if current_area and not current_npc and not user_input.lower().startswith(("/talk", "/go")):
                # Check if the last command might have intentionally left current_npc as None
                # For now, assume if current_npc is None and we are in an area, it's okay to prompt.
                # The prompt_prefix will guide the user. handle_go now manages the auto-talk.
                pass # auto_start_default_npc_conversation is now primarily triggered by handle_go or initial setup

        except KeyboardInterrupt:
            print(f"\n{TerminalFormatter.DIM}Interruption detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break
        except EOFError:
            print(f"\n{TerminalFormatter.DIM}EOF detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break
        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Unexpected Error in Main Loop: {type(e).__name__} - {e}{TerminalFormatter.RESET}")
            # traceback.print_exc() # Uncomment for detailed debugging
            # Consider saving conversation here too
            # session_utils.save_current_conversation(db, player_id, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}An error occurred. Attempting to continue... (Restart may be needed){TerminalFormatter.RESET}")

    # --- End of Session Cleanup ---
    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    if chat_session and current_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Final stats for ({current_npc.get('name', 'N/A')}):{TerminalFormatter.RESET}")
        print(chat_session.format_session_stats())
    else:
        print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")