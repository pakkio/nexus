from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action

def handle_profile(state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    _add_profile_action(state, "Used /profile command")

    # Load fresh profile from DB for display, but keep state's cache consistent if needed

    profile_data = db.load_player_profile(player_id) # Fresh
    state['player_profile_cache'] = profile_data # Update cache with fresh data

    print(f"\n{TF.BRIGHT_YELLOW}{TF.BOLD}--- Your Psychological Profile ---{TF.RESET}")
    if profile_data:
        print(f"{TF.YELLOW}Core Traits:{TF.RESET}")
        for trait, value in profile_data.get("core_traits", {}).items():
            print(f" {TF.DIM}- {trait.replace('_', ' ').capitalize()}: {value}/10{TF.RESET}")

        print(f"\n{TF.YELLOW}Decision Patterns:{TF.RESET}")
        patterns = profile_data.get("decision_patterns", [])
        if patterns:
            for p in patterns[-5:]: # Show last 5 patterns for brevity
                print(f"  {TF.DIM}- {p.replace('_', ' ').capitalize()}{TF.RESET}")
        else:
            print(f"  {TF.DIM}(None observed yet){TF.RESET}")

        print(f"\n{TF.YELLOW}Veil Perception:{TF.RESET} {TF.DIM}{profile_data.get('veil_perception', 'Undefined').replace('_', ' ').capitalize()}{TF.RESET}")
        print(f"{TF.YELLOW}Interaction Style:{TF.RESET} {TF.DIM}{profile_data.get('interaction_style_summary', 'Undefined')}{TF.RESET}")

        print(f"\n{TF.YELLOW}Key Experiences (Recent):{TF.RESET}")
        experiences = profile_data.get("key_experiences_tags", [])
        if experiences:
            for exp in experiences[-5:]: # Show last 5 experiences
                print(f"  {TF.DIM}- {exp.replace('_', ' ').capitalize()}{TF.RESET}")
        else:
            print(f"  {TF.DIM}(None recorded yet){TF.RESET}")

        print(f"\n{TF.YELLOW}Trust Levels:{TF.RESET}")
        print(f"  {TF.DIM}- General: {profile_data.get('trust_levels', {}).get('general', 5)}/10{TF.RESET}")
        # Could add specific NPC trust levels if tracked

        print(f"\n{TF.YELLOW}Inferred Motivations:{TF.RESET}")
        motivations = profile_data.get("inferred_motivations", [])
        if motivations:
            for m in motivations:
                print(f"  {TF.DIM}- {m.replace('_', ' ').capitalize()}{TF.RESET}")
        else:
            print(f"  {TF.DIM}(Primary quest focus assumed){TF.RESET}")

    else:
        print(f" {TF.DIM}(No profile data available. This is unexpected.){TF.RESET}")
    print(f"{TF.BRIGHT_YELLOW}{'-'*30}{TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}