# Path: main_core.py
# Refactored Version - Syntax Fix 2

import sys
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Import base components needed for setup
try:
    from terminal_formatter import TerminalFormatter
    from chat_manager import ChatSession, format_stats
    from db_manager import DbManager
    # Utilities needed directly here (or passed through state)
    from main_utils import format_storyboard_for_prompt
except ImportError as e:
    # Fallback for error message if TerminalFormatter itself is missing
    class TerminalFormatter:
        RED = ""; RESET = ""; BOLD = ""; YELLOW = ""; DIM = ""; MAGENTA = ""
        CYAN = ""; BRIGHT_CYAN = ""; BG_GREEN = ""; BLACK = ""; BRIGHT_MAGENTA = ""
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))
        @staticmethod
        def get_terminal_width(): return 80
    print(f"{TerminalFormatter.RED}Fatal Error: Could not import base modules in main_core.py: {e}{TerminalFormatter.RESET}")
    sys.exit(1)

# Import the new modules
try:
    import command_processor
    import session_utils
except ImportError as e:
    # Use previously defined/imported TerminalFormatter if available
    try:
        TF = TerminalFormatter
    except NameError:
        # Define minimal fallback if TerminalFormatter failed *and* was needed for this error msg
        class TF: # Corrected: Class definition on new line
            RED = ""; RESET = ""
    print(f"{TF.RED}Fatal Error: Could not import command_processor or session_utils: {e}{TF.RESET}")
    sys.exit(1)


def run_interaction_loop(
        db: DbManager,
        story: str,
        initial_area: Optional[str],
        initial_npc_name: Optional[str],
        model_name: Optional[str],
        use_stream: bool,
        auto_show_stats: bool,
        player_id: str # Currently unused, placeholder
):
    """Runs the main user interaction loop, delegating command processing."""

    # --- Initialize State ---
    current_area: Optional[str] = None
    current_npc: Optional[Dict[str, Any]] = None
    chat_session: Optional[ChatSession] = None

    # Fetch initial full NPC list (used for area validation etc.)
    # Note: `refresh_known_npcs_list` now resides in session_utils
    all_known_npcs = session_utils.refresh_known_npcs_list(db, TerminalFormatter)
    known_areas = session_utils.get_known_areas_from_list(all_known_npcs)

    # --- Validate Initial Area (using partial matching) ---
    if initial_area:
        print(f"{TerminalFormatter.DIM}Validating initial area '{initial_area}'...{TerminalFormatter.RESET}")
        initial_area_prefix = initial_area.lower()
        matches = [area for area in known_areas if area.lower().startswith(initial_area_prefix)]
        if len(matches) == 1:
            current_area = matches[0]
            print(f"{TerminalFormatter.GREEN}Initial area set to: {current_area}{TerminalFormatter.RESET}")
        elif len(matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area prefix '{initial_area}' is ambiguous. Matches:{TerminalFormatter.RESET}")
            for area_match in sorted(matches): print(f"  - {area_match}")
            print(f"{TerminalFormatter.YELLOW}Please restart with a more specific --area or use /go later.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial area '{initial_area}' not found or has no NPCs.{TerminalFormatter.RESET}")
            if known_areas: print(f"{TerminalFormatter.DIM}Known areas: {', '.join(known_areas)}{TerminalFormatter.RESET}")

    if not current_area and not initial_area:
        print(f"\n{TerminalFormatter.YELLOW}No starting area specified. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.YELLOW} to begin.{TerminalFormatter.RESET}")
    elif not current_area and initial_area:
        print(f"\n{TerminalFormatter.YELLOW}Could not set initial area. Use {TerminalFormatter.BOLD}/go <area_name_or_prefix>{TerminalFormatter.YELLOW} to begin.{TerminalFormatter.RESET}")

    # --- Initial NPC Setup (using partial matching) ---
    if initial_npc_name and current_area:
        print(f"{TerminalFormatter.DIM}Attempting initial conversation with '{initial_npc_name}' in '{current_area}'...{TerminalFormatter.RESET}")
        initial_npc_prefix = initial_npc_name.lower()
        npcs_in_initial_area = [n for n in all_known_npcs if n.get('area','').lower() == current_area.lower()]
        matches = [n for n in npcs_in_initial_area if n.get('name','').lower().startswith(initial_npc_prefix)]

        if len(matches) == 1:
            matched_npc_info = matches[0]
            correct_npc_name = matched_npc_info['name']
            print(f"{TerminalFormatter.DIM}Unique initial NPC match: {correct_npc_name}{TerminalFormatter.RESET}")
            # Use the utility function to load
            # Pass ChatSession class reference needed by the util function
            npc_data, session = session_utils.load_and_prepare_conversation(
                db, current_area, correct_npc_name, model_name, story, ChatSession, TerminalFormatter
            )
            if npc_data and session:
                current_npc = npc_data
                chat_session = session
                # Print intro (moved here from handler as it's part of initial setup)
                print(f"\n{TerminalFormatter.BG_GREEN}{TerminalFormatter.BLACK}{TerminalFormatter.BOLD} PARLANDO CON {current_npc.get('name', 'NPC').upper()} IN {current_area.upper()} {TerminalFormatter.RESET}")
                print(f"{TerminalFormatter.DIM}Digita '/exit' per uscire, '/help' per i comandi.{TerminalFormatter.RESET}")
                print(f"{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}\n")
                print(f"{TerminalFormatter.BOLD}{TerminalFormatter.MAGENTA}{current_npc['name']} > {TerminalFormatter.RESET}")
                opening_line = session_utils.get_npc_opening_line(current_npc, TerminalFormatter)
                print(TerminalFormatter.format_terminal_text(opening_line, width=TerminalFormatter.get_terminal_width()))
                print()
            else:
                print(f"{TerminalFormatter.YELLOW}⚠️ Failed to load conversation data for initial NPC {correct_npc_name}.{TerminalFormatter.RESET}")
        elif len(matches) > 1:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial NPC prefix '{initial_npc_name}' is ambiguous in {current_area}. Matches:{TerminalFormatter.RESET}")
            for npc_match in sorted(matches, key=lambda x: x['name']): print(f"  - {npc_match.get('name')}")
            print(f"{TerminalFormatter.YELLOW}Please restart with a more specific --npc or use /talk later.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.YELLOW}⚠️ Initial NPC '{initial_npc_name}' not found in area '{current_area}'. Use /talk later.{TerminalFormatter.RESET}")

    elif initial_npc_name and not current_area:
        print(f"\n{TerminalFormatter.YELLOW}Warning: Initial NPC specified ({initial_npc_name}) but the initial area was invalid or ambiguous. Use /go and /talk.{TerminalFormatter.RESET}")

    # ===========================
    # --- Main Interaction Loop ---
    # ===========================
    while True:
        try:
            # Determine prompt prefix
            if current_npc:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.GREEN}Tu ({current_npc['name']}) > {TerminalFormatter.RESET}"
            elif current_area:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}Tu ({current_area}) > {TerminalFormatter.RESET}"
            else:
                prompt_prefix = f"\n{TerminalFormatter.BOLD}{TerminalFormatter.CYAN}Tu (Nowhere) > {TerminalFormatter.RESET}"

            user_input = input(prompt_prefix).strip()

            # Prepare current state to pass to handlers
            current_state = {
                'db': db,
                'story': story,
                'current_area': current_area,
                'current_npc': current_npc,
                'chat_session': chat_session,
                'model_name': model_name,
                'use_stream': use_stream,
                'auto_show_stats': auto_show_stats,
                'player_id': player_id,
                # Pass class/function references needed by handlers/utils
                'ChatSession': ChatSession, # Pass the actual ChatSession class
                'TerminalFormatter': TerminalFormatter, # Pass the actual TerminalFormatter class/instance
                'format_stats': format_stats, # Pass the format_stats function
            }

            # Process input using the command processor
            # Using the revised version which handles args/state passing better
            handler_result = command_processor.process_input_revised(user_input, current_state)

            # Update state based on handler result
            if handler_result.get('status') == 'exit':
                break # Exit loop

            # Update mutable state variables if they were changed by a handler
            # Use .get(key, default) to avoid errors if key is missing
            current_area = handler_result.get('current_area', current_area)
            current_npc = handler_result.get('current_npc', current_npc)
            chat_session = handler_result.get('chat_session', chat_session)

            # Check if loop should continue (default is True unless exit)
            if not handler_result.get('continue_loop', True):
                # This might be used by a future command that needs to break differently
                break

        # --- Main Loop Exception Handling ---
        except KeyboardInterrupt:
            print(f"\n{TerminalFormatter.DIM}Interruption detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            # Need db, current_npc, chat_session - access directly or get from last state
            session_utils.save_current_conversation(db, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break
        except EOFError:
            print(f"\n{TerminalFormatter.DIM}EOF detected. Saving last conversation (if active)...{TerminalFormatter.RESET}")
            session_utils.save_current_conversation(db, current_npc, chat_session, TerminalFormatter)
            print(f"{TerminalFormatter.YELLOW}\nExiting.{TerminalFormatter.RESET}")
            break
        except Exception as e:
            print(f"\n{TerminalFormatter.RED}❌ Unexpected Error in Main Loop: {e}{TerminalFormatter.RESET}")
            traceback.print_exc()
            # session_utils.save_current_conversation(db, current_npc, chat_session, TerminalFormatter) # Optional save
            print(f"{TerminalFormatter.YELLOW}Attempting to continue... (Restart may be needed){TerminalFormatter.RESET}")

    # --- End of Session Cleanup ---
    print(f"\n{TerminalFormatter.BRIGHT_CYAN}{'=' * 50}{TerminalFormatter.RESET}")
    if chat_session and current_npc:
        print(f"{TerminalFormatter.YELLOW}Session terminated. Final stats for ({current_npc.get('name', 'N/A')}):{TerminalFormatter.RESET}")
        print(chat_session.format_session_stats())
    else:
        print(f"{TerminalFormatter.YELLOW}Session terminated.{TerminalFormatter.RESET}")
