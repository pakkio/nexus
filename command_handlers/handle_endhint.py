from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action

def handle_endhint(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    _add_profile_action(state, "Used /endhint command")
    if not state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}You are not currently consulting Lyra.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    restored_npc = state.get('stashed_npc')
    restored_session = state.get('stashed_chat_session')

    state['in_lyra_hint_mode'] = False
    state['current_npc'] = restored_npc
    state['chat_session'] = restored_session
    state['stashed_npc'] = None
    state['stashed_chat_session'] = None

    if restored_npc and restored_session:
        print(f"\n{TF.DIM}You withdraw from your consultation with Lyra and return your attention to {restored_npc.get('name', 'your previous interaction')}...{TF.RESET}")
        if restored_session.messages:
            print(f"{TF.DIM}--- Resuming conversation with {restored_npc.get('name', 'NPC')} ---{TF.RESET}")
            # Display last 1 or 2 messages to reorient player
            last_msg_count = min(2, len(restored_session.messages))
            for msg in restored_session.messages[-last_msg_count:]:
                role_display = "You" if msg['role'] == 'user' else restored_npc.get('name', 'NPC')
                if msg['role'] == 'user':
                    color = TF.GREEN
                else:
                    color = session_utils.get_npc_color(restored_npc.get('name', 'NPC'), TF)
                print(f"\n{TF.BOLD}{color}{role_display} > {TF.RESET}")
                print(TF.format_terminal_text(msg['content']))
            print() # Extra newline for readability
        # else: No messages to show, just return to the prompt
    else:
        # This case should ideally not happen if /hint was used correctly
        state['current_npc'] = None # Clear context if restoration failed
        state['chat_session'] = None
        print(f"{TF.YELLOW}Returned from hint mode, but previous context was unclear. Please use /go or /talk.{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}