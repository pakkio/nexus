import json
from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_history(state: Dict[str, Any]) -> HandlerResult:
    _add_profile_action(state, "Used /history command")
    TF = state['TerminalFormatter']
    chat_session = state.get('chat_session')
    current_npc = state.get('current_npc')

    if chat_session and current_npc:
        npc_name = current_npc.get('name', 'current NPC')
        mode_info = " (Lyra Consultation)" if state.get('in_lyra_hint_mode') else ""
        print(f"\n{TF.DIM}--- History with {npc_name}{mode_info} ---{TF.RESET}")
        try:
            # Use ensure_ascii=False for better display of non-ASCII characters if present in dialogue
            history_json = json.dumps(chat_session.get_history(), indent=2, ensure_ascii=False)
            print(history_json)
        except Exception as e:
            print(f"{TF.RED}Error formatting history as JSON: {e}{TF.RESET}")
            print(f"{TF.DIM}Raw history object: {chat_session.get_history()}{TF.RESET}")
    else:
        print(f"{TF.YELLOW}No active chat session to show history for.{TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}