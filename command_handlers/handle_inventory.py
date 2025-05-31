from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_inventory(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    _add_profile_action(state, "Used /inventory command")

    # Ensure inventory and credits are up-to-date from DB if not relying solely on cache
    # For this command, always fetch fresh, but update cache if state uses it.

    inventory_list = db.load_inventory(player_id) # Fresh from DB
    current_credits = db.get_player_credits(player_id) # Fresh from DB

    # Update cache in state if these fields are used there primarily

    state['player_inventory'] = inventory_list
    state['player_credits_cache'] = current_credits

    print(f"\n{TF.BRIGHT_GREEN}{TF.BOLD}--- Your Inventory ---{TF.RESET}")
    if inventory_list:
        for item in inventory_list: # Assumes item is just a string name
            print(f" {TF.GREEN}❖ {item.title()}{TF.RESET}") # .title() for nicer display
    else:
        print(f" {TF.DIM}(Your inventory is empty){TF.RESET}")

    print(f"{TF.BRIGHT_YELLOW}Credits: {current_credits}{TF.RESET}")
    print(f"{TF.BRIGHT_GREEN}{'-'*22}{TF.RESET}") # Separator

    return {**state, 'status': 'ok', 'continue_loop': True}