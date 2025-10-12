from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action
import json

def handle_profile(args_str: str, state: Dict[str, Any]) -> HandlerResult:
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    debug_mode = "--debug" in args_str.lower()
    _add_profile_action(state, f"Used /profile command{' (debug)' if debug_mode else ''}")

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

        # === Achievements Section ===
        achievements = profile_data.get("achievements", [])
        print(f"\n{TF.YELLOW}Achievements:{TF.RESET}")
        if achievements:
            for ach in achievements[-5:]:
                print(f"  {TF.DIM}- {ach}{TF.RESET}")
        else:
            print(f"  {TF.DIM}(No achievements yet){TF.RESET}")

        # === AI Considerations Section ===
        ai_considerations = profile_data.get("llm_analysis_notes", "")
        print(f"\n{TF.YELLOW}AI Considerations (Psychological Summary):{TF.RESET}")
        if ai_considerations:
            print(f"  {TF.DIM}{ai_considerations[:300]}{'...' if len(ai_considerations) > 300 else ''}{TF.RESET}")
        else:
            print(f"  {TF.DIM}(No AI summary available yet){TF.RESET}")

        # Debug mode: show philosophical alignment and LLM analysis details
        if debug_mode:
            print(f"\n{TF.BRIGHT_CYAN}{TF.BOLD}--- DEBUG INFO ---{TF.RESET}")
            
            # Show philosophical leaning if tracked
            philo_leaning = profile_data.get("philosophical_leaning", "neutral")
            print(f"{TF.CYAN}Philosophical Alignment:{TF.RESET} {TF.DIM}{philo_leaning.replace('_', ' ').title()}{TF.RESET}")
            
            # Show recent profile changes with reasoning
            recent_changes = profile_data.get("recent_changes_log", [])
            if recent_changes:
                print(f"\n{TF.CYAN}Recent Profile Changes:{TF.RESET}")
                for change in recent_changes[-3:]:  # Last 3 changes
                    print(f"  {TF.DIM}- {change}{TF.RESET}")
            
            # Show raw LLM analysis if available
            llm_notes = profile_data.get("llm_analysis_notes", "")
            if llm_notes:
                print(f"\n{TF.CYAN}LLM Analysis Notes:{TF.RESET}")
                print(f"  {TF.DIM}{llm_notes[:200]}{'...' if len(llm_notes) > 200 else ''}{TF.RESET}")
            
            print(f"\n{TF.CYAN}Raw Profile Data:{TF.RESET}")
            print(f"{TF.DIM}{json.dumps(profile_data, indent=2)[:500]}{'...' if len(str(profile_data)) > 500 else ''}{TF.RESET}")

    else:
        print(f" {TF.DIM}(No profile data available. This is unexpected.){TF.RESET}")
    print(f"{TF.BRIGHT_YELLOW}{'-'*30}{TF.RESET}")

    return {**state, 'status': 'ok', 'continue_loop': True}