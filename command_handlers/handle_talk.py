import random
from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action, RANDOM_TALK_SYNTAX

def handle_talk(args: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    _add_profile_action(state, f"Used /talk command with args: '{args}'")

    if state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}You cannot use /talk while consulting Lyra. Use /endhint first.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    area = state.get('current_area')
    npc_old = state.get('current_npc')
    session_old = state.get('chat_session')
    model, story, ChatSession_cls = state['model_name'], state['story'], state['ChatSession']

    if not area:
        print(f"{TF.YELLOW}Not in an area. Use /go.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    if not args:
        print(f"{TF.YELLOW}Usage: /talk <npc_name|.>{TF.RESET}") # . for random
        return {**state, 'status': 'ok', 'continue_loop': True}

    target_npc_info = None
    talk_initiated = False
    new_state_part: Dict[str, Any] = {}

    all_npcs = session_utils.refresh_known_npcs_list(db, TF)
    npcs_here = [n for n in all_npcs if n.get('area','').lower() == area.lower()]

    if args == RANDOM_TALK_SYNTAX: # Random NPC
        if not npcs_here:
            print(f"{TF.YELLOW}No NPCs in {area}.{TF.RESET}")
            return state # No change, just return current state

        eligible_npcs = [n for n in npcs_here if not (npc_old and n.get('code') == npc_old.get('code'))]

        if not eligible_npcs and npc_old: # Only current NPC is here
            print(f"{TF.DIM}Only {npc_old.get('name')} is here, and you're already talking to them.{TF.RESET}")
            return state
        elif not eligible_npcs and not npc_old: # No other NPCs and not talking to anyone
            print(f"{TF.YELLOW}No other NPCs in {area} to talk to randomly.{TF.RESET}")
            return state

        target_npc_info = random.choice(eligible_npcs if eligible_npcs else npcs_here) # Fallback to npcs_here if eligible is empty (shouldn't happen with above checks)
        print(f"{TF.DIM}Randomly approaching: {target_npc_info['name']}{TF.RESET}")
        talk_initiated = True

    else: # Specific NPC name
        prefix = args.lower()
        matches = [n for n in npcs_here if n.get('name','').lower().startswith(prefix)]
        if len(matches) == 1:
            target_npc_info = matches[0]
            talk_initiated = True
        elif len(matches) > 1:
            print(f"{TF.YELLOW}Ambiguous NPC name '{args}'. Matches: {', '.join(m.get('name','') for m in matches)}{TF.RESET}")
        else:
            print(f"{TF.YELLOW}NPC '{args}' not found in {area}.{TF.RESET}")

    if talk_initiated and target_npc_info:
        if npc_old and npc_old.get('code') == target_npc_info.get('code'):
            print(f"{TF.DIM}You are already talking to {target_npc_info['name']}.{TF.RESET}")
        else: # Switching to a new NPC or starting a new conversation
            if session_old: # Save previous conversation if exists
                print(f"{TF.DIM}Saving previous conversation with {npc_old.get('name','NPC')}...{TF.RESET}")
                session_utils.save_current_conversation(db, player_id, npc_old, session_old, TF, state)

            llm_wrapper_for_npc_setup = state.get('llm_wrapper_func')
            npc_data, new_session = session_utils.start_conversation_with_specific_npc(
                db, player_id, area, target_npc_info['name'], model, story, ChatSession_cls, TF,
                game_session_state=state,
                llm_wrapper_for_profile_distillation=llm_wrapper_for_npc_setup,
                model_type="dialogue" # Regular NPC conversation
            )
            if npc_data and new_session:
                new_state_part.update({'current_npc': npc_data, 'chat_session': new_session})
            else: # Failed to start new conversation
                new_state_part.update({'current_npc': None, 'chat_session': None}) # Clear context
                print(f"{TF.RED}Error initiating talk with {target_npc_info.get('name', 'NPC')}.{TF.RESET}")

    state.update(new_state_part)
    return {**state, 'status': 'ok', 'continue_loop': True}