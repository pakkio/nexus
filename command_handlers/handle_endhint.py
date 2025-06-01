# command_handlers/handle_endhint.py
from typing import Dict, Any

try:
    # Assuming session_utils is in the Python path or structured correctly
    from session_utils import save_current_conversation, print_conversation_start_banner, get_npc_color
    from terminal_formatter import TerminalFormatter # Ensure TF is available
except ImportError:
    print("WARNING (handle_endhint): Failed to import from session_utils or terminal_formatter. Using fallbacks.")
    class TerminalFormatter: # Basic fallback for TF
        GREEN = DIM = YELLOW = RESET = BOLD = ""
        @staticmethod
        def get_terminal_width(): return 80
        @staticmethod
        def format_terminal_text(text, width=80): return text
    def save_current_conversation(db, player_id, npc, session, TF, game_state): pass
    def print_conversation_start_banner(npc_data, area_name, TF, game_state): pass # Added game_state to fallback
    def get_npc_color(npc_name, TF): return ""


def handle_endhint(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handles the /endhint command to leave consultation with the wise guide."""
    TF = state.get('TerminalFormatter', TerminalFormatter) # Use state's TF or fallback
    player_id = state['player_id']
    db = state['db']
    wise_guide_npc_name = state.get('wise_guide_npc_name', 'the Wise Guide') # Fallback name

    if not state.get('in_hint_mode', False):
        print(f"{TF.YELLOW}You are not currently consulting {wise_guide_npc_name}.{TF.RESET}")
        return state

    print(f"\n{TF.DIM}Ending consultation with {wise_guide_npc_name}...{TF.RESET}")

    # The conversation with the guide is typically ephemeral and not saved back to DB
    # The stashed conversation was saved before entering hint mode.

    state['in_hint_mode'] = False
    # Clear current guide NPC and session from active state
    current_guide_npc_name = state.get('current_npc', {}).get('name', 'the guide') # For logging
    state['current_npc'] = None
    state['chat_session'] = None

    if state.get('stashed_npc') and state.get('stashed_chat_session'):
        state['current_npc'] = state.pop('stashed_npc')
        state['chat_session'] = state.pop('stashed_chat_session')

        restored_npc_name = state['current_npc'].get('name', 'your previous conversation partner')
        restored_area_name = state['current_npc'].get('area', 'their location')

        print(f"{TF.GREEN}Returning to your conversation with {restored_npc_name} in {restored_area_name}.{TF.RESET}")

        # --- CORRECTED CALL to print_conversation_start_banner ---
        print_conversation_start_banner(
            state['current_npc'],
            restored_area_name,
            TF,
            state # Pass the full game_session_state
        )

        # Optionally, show the last message from the stashed conversation to re-orient the player
        if state['chat_session'].messages:
            last_msg = state['chat_session'].messages[-1]

            # Avoid reprinting the [CONVERSATION_BREAK:] marker if it's the last one
            # Also, if the last message was the [CONVERSATION_RESUMED:] marker, don't print that either.
            # Instead, the NPC should react to the player's return in the next turn.
            if not (last_msg.get('role') == 'user' and
                    (last_msg.get('content','').startswith("[CONVERSATION_BREAK:") or
                     last_msg.get('content','').startswith("[CONVERSATION_RESUMED:"))):

                npc_color_for_display = get_npc_color(state['current_npc'].get('name', 'NPC'), TF)
                role_display = "You" if last_msg['role'] == 'user' else state['current_npc'].get('name', 'NPC')
                color_to_use = TF.GREEN if last_msg['role'] == 'user' else npc_color_for_display

                print(f"{TF.BOLD}{color_to_use}{role_display} > {TF.RESET}")
                print(TF.format_terminal_text(last_msg['content'], width=TF.get_terminal_width()))
                print() # Newline after printing last message
            else:
                # If the last message was a break/resume marker, we might want to prompt the NPC
                # to acknowledge the player's return. For now, just don't print the marker.
                # The next player input will trigger an NPC response.
                pass
    else:
        print(f"{TF.YELLOW}No previous conversation to return to. Use /go or /talk to continue.{TF.RESET}")
        state['current_area'] = None # Or set to a default/last known area if preferred

    # Clean up hint-specific cache if it was per-consultation (currently hint_cache is more general)
    # For example, if you had state['hint_cache']['current_consultation_id'], you'd clear it here.
    # Since 'hint_cache' in main_core stores 'guide_name_chat_history', it will just be overwritten
    # next time /hint is used with that guide, or a different guide's history will be stored.

    # Add action to player profile log
    from command_handler_utils import _add_profile_action
    _add_profile_action(state, f"Ended hint consultation with '{current_guide_npc_name}'.")

    state['status'] = 'ok'
    state['continue_loop'] = True
    return state