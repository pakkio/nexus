import re
from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_give(args: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc = state['current_npc']
    chat_session = state['chat_session']
    command_result_payload: Dict[str, Any] = {} # To store results for the main loop

    if state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}You cannot use /give while consulting Lyra. Use /endhint first.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    if not current_npc or not chat_session:
        print(f"{TF.YELLOW}Not talking to anyone to give an item to.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    input_str = args.strip()
    if not input_str:
        print(f"{TF.YELLOW}What do you want to give? Usage: /give <item_name_or_amount Credits>{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    credit_match = re.match(r"(\d+)\s+(credits?)$", input_str, re.IGNORECASE)
    item_name_for_log_and_action = ""

    if credit_match:
        amount_to_give = int(credit_match.group(1))
        player_current_credits = state.get('player_credits_cache', db.get_player_credits(player_id))

        if amount_to_give <= 0:
            print(f"{TF.YELLOW}You must give a positive amount of Credits.{TF.RESET}")
            return {**state, 'status': 'ok', 'continue_loop': True}

        if player_current_credits >= amount_to_give:
            if db.update_player_credits(player_id, -amount_to_give, state): # game_state (state here) is passed for cache update
                item_name_for_log_and_action = f"{amount_to_give} Credits"
                # This payload will be checked by main_core after the command
                command_result_payload['item_given_to_npc_this_turn'] = {
                    'item_name': item_name_for_log_and_action, # e.g., "50 Credits"
                    'type': 'currency',
                    'amount': amount_to_give,
                    'npc_code': current_npc.get('code') # To ensure correct NPC processes it
                }
            # else: update_player_credits would print error if it failed, but should return False
        else:
            print(f"{TF.YELLOW}You don't have enough Credits. You only have {player_current_credits}.{TF.RESET}")
            return {**state, 'status': 'ok', 'continue_loop': True}

    else:
        # Giving an item
        item_name_to_give = input_str # User's raw input for the item name
        
        # Try to find item by partial name (handles both exact and partial matches)
        matched_item_name = db.find_item_by_partial_name(player_id, item_name_to_give)
        
        if not matched_item_name:
            print(f"{TF.YELLOW}You don't have '{item_name_to_give}' (or similar) in your inventory.{TF.RESET}")
            return {**state, 'status': 'ok', 'continue_loop': True}
        
        cleaned_item_name_for_check = matched_item_name  # Use the matched exact name

        if db.remove_item_from_inventory(player_id, cleaned_item_name_for_check, state): # game_state (state here) for inv cache update
            item_name_for_log_and_action = item_name_to_give.strip() # Use original user input for log/action message clarity
            command_result_payload['item_given_to_npc_this_turn'] = {
                'item_name': cleaned_item_name_for_check, # Use cleaned name for quest logic
                'original_user_input_item_name': item_name_for_log_and_action,
                'type': 'item',
                'npc_code': current_npc.get('code')
            }
        else:
            # This should ideally not happen if check_item_in_inventory passed
            print(f"{TF.RED}Error: Could not remove '{item_name_to_give}' from inventory (unexpected).{TF.RESET}")
            return {**state, 'status': 'ok', 'continue_loop': True}

    if item_name_for_log_and_action: # If an item or credits were successfully processed for giving
        print(f"{TF.DIM}You hand {item_name_for_log_and_action} to {current_npc['name']}.{TF.RESET}")
        # Create a user message in chat history reflecting the action
        player_action_message = f"You hand over {item_name_for_log_and_action} to {current_npc['name']}."
        chat_session.add_message("user", player_action_message)
        command_result_payload['force_npc_turn_after_command'] = True
        _add_profile_action(state, f"Gave '{item_name_for_log_and_action}' to NPC '{current_npc['name']}'")

    state.update(command_result_payload) # Merge payload into state for main_core to use
    return {**state, 'status': 'ok', 'continue_loop': True}