from typing import Dict, Any
import session_utils
from command_handler_utils import HandlerResult, _add_profile_action, get_distilled_profile_insights_for_npc # Uses the (potentially fallback) version

def handle_profile_for_npc(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    current_npc = state.get('current_npc')
    llm_wrapper_func = state.get('llm_wrapper_func')
    model_name = state.get('model_name') # Or a specific model for this task if configured
    story_context = state.get('story', "") # Get story context from state
    _add_profile_action(state, "Used /profile_for_npc command")

    if state.get('in_lyra_hint_mode'):
        print(f"{TF.YELLOW}This command is not available while consulting Lyra.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    if not current_npc:
        print(f"{TF.YELLOW}You are not currently talking to an NPC.{TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    if not llm_wrapper_func or not model_name:
        print(f"{TF.RED}LLM tools not available to generate NPC insights for profile.{TF.RESET}")
        print(f"{TF.DIM}(This feature requires an LLM to distill profile information for the NPC. This is a debug view.){TF.RESET}")
        return {**state, 'status': 'ok', 'continue_loop': True}

    profile_data = state.get('player_profile_cache', db.load_player_profile(player_id)) # Use cached profile
    npc_name = current_npc.get('name', 'Current NPC')
    npc_color = session_utils.get_npc_color(npc_name, TF)

    print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}--- Distilled Profile Insights for {npc_color}{npc_name}{TF.RESET}{TF.BRIGHT_CYAN}{TF.BOLD} ---{TF.RESET}")
    print(f"{TF.DIM}(This is what {npc_name} might subtly 'know' or infer about you based on your profile, used to tailor their responses. This is a debug view.){TF.RESET}")

    # Call the (potentially fallback) function

    distilled_insights = get_distilled_profile_insights_for_npc(
        player_profile=profile_data,
        current_npc_data=current_npc,
        story_context_summary=story_context, # Pass the story context
        llm_wrapper_func=llm_wrapper_func,
        model_name=model_name,
        TF=TF
    )

    if distilled_insights:
        # format_terminal_text might be good here if insights are long
        print(f"{TF.CYAN}➢ {TF.format_terminal_text(distilled_insights, width=TF.get_terminal_width() - 4)}{TF.RESET}")
    else:
        print(f"{TF.DIM}(No specific insights could be distilled for {npc_name} at this time, or an error occurred.){TF.RESET}")

    print(f"{TF.BRIGHT_CYAN}{'-'*40}{TF.RESET}")
    return {**state, 'status': 'ok', 'continue_loop': True}