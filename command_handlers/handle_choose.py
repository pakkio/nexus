from typing import Dict, Any
import veil_finale
from command_handler_utils import HandlerResult, _add_profile_action


def handle_choose(args: str, state: Dict[str, Any]) -> HandlerResult:
    """/choose <preserve|dissolve|transform> -- the player's irreversible decision on the Veil, before Meridia."""
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    npc = state.get('current_npc') or {}
    chat_session = state.get('chat_session')
    ok = {**state, 'status': 'ok', 'continue_loop': True}

    if npc.get('code') != veil_finale.MERIDIA_CODE or not chat_session:
        print(f"{TF.YELLOW}The fate of the Veil is decided before Meridia, at the {veil_finale.MERIDIA_AREA}.{TF.RESET}")
        return ok

    if state.get('plot_flags') is None:
        state['plot_flags'] = {}
    flags = state['plot_flags']

    done = veil_finale.chosen_fate(flags)
    if done:
        print(f"{TF.YELLOW}You have already chosen: {done}. The choice cannot be undone.{TF.RESET}")
        return ok

    open_, missing = veil_finale.gate_status(flags)
    if not open_:
        print(f"{TF.YELLOW}{veil_finale.locked_message(missing, flags)}{TF.RESET}")
        return ok

    fate = veil_finale.normalize_fate(args)
    if not fate:
        options = ", ".join(veil_finale.FATES)
        print(f"{TF.YELLOW}Usage: /choose <{options.replace(', ', '|')}>{TF.RESET}")
        return ok

    veil_finale.record_fate(flags, fate)
    db.add_item_to_inventory(player_id, veil_finale.LOOM_ITEM, state)
    print(f"{TF.GREEN}You have chosen the fate of the Veil: {fate}.{TF.RESET}")
    _add_profile_action(state, f"Chose the fate of the Veil: {fate}")
    chat_session.add_message("user", f"I choose to {fate} the Veil. {veil_finale.FATES[fate]}")
    state['force_npc_turn_after_command'] = True
    return {**state, 'status': 'ok', 'continue_loop': True}
