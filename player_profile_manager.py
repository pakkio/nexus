# Path: player_profile_manager.py
# MODIFIED: Shifting profile trait/pattern updates towards LLM-based analysis.
# MODIFIED: Added robust JSON extraction from LLM response.

import json
import re # For regex extraction of JSON
from typing import Dict, List, Any, Optional, Callable, Tuple
import copy

try:
    from llm_wrapper import llm_wrapper # Crucial for this approach
    from terminal_formatter import TerminalFormatter
except ImportError:
    print("WARNING (player_profile_manager): llm_wrapper or terminal_formatter not found. Profile features WILL BE SEVERELY limited.")
    def llm_wrapper(messages, model_name, stream, collect_stats, formatting_function=None, width=None):
        print("Fallback llm_wrapper: LLM calls from player_profile_manager will not work.")
        return json.dumps({"analysis_notes": "LLM not available, no profile changes suggested."}), {"error": "llm_wrapper missing"}
    class TerminalFormatter:
        DIM = ""; RESET = ""; BOLD = ""; YELLOW = ""; RED = ""; GREEN = ""; MAGENTA = ""; CYAN = ""; ITALIC = "";
        @staticmethod
        def format_terminal_text(text, width=80): import textwrap; return "\n".join(textwrap.wrap(text, width=width))

DEFAULT_PROFILE = {
    "core_traits": {
        "curiosity": 5, "caution": 5, "empathy": 5, "skepticism": 5,
        "pragmatism": 5, "aggression": 3, "deception": 2, "honor": 5
    },
    "decision_patterns": [],
    "veil_perception": "neutral_curiosity",
    "interaction_style_summary": "Observant and typically polite.",
    "key_experiences_tags": [],
    "trust_levels": {"general": 5},
    "inferred_motivations": ["understand_the_veil_crisis", "survive"]
}

def get_default_player_profile() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULT_PROFILE)

def get_distilled_profile_insights_for_npc(
        player_profile: Dict[str, Any],
        current_npc_data: Dict[str, Any],
        story_context_summary: str,
        llm_wrapper_func: Callable,
        model_name: str,
        TF: type = TerminalFormatter
) -> str:
    if not player_profile or not current_npc_data:
        return ""
    simple_profile_summary = {
        "traits": player_profile.get("core_traits", {}),
        "style": player_profile.get("interaction_style_summary", "unknown"),
        "motivations": player_profile.get("inferred_motivations", [])
    }
    profile_summary_for_prompt = json.dumps(simple_profile_summary, indent=2)
    npc_name = current_npc_data.get('name', 'this NPC')
    npc_role = current_npc_data.get('role', 'unknown role')
    npc_motivation = current_npc_data.get('motivation', 'unclear motivations')

    prompt_messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant that helps an NPC understand a player (Seeker) better for richer interaction. "
                "Given the Seeker's psychological profile summary and the NPC's details, provide 1-2 extremely concise, actionable insights "
                "for the NPC. This information is for the NPC's internal 'awareness' to subtly guide their responses. "
                "Focus on what is most pertinent for THIS NPC given their goals and role. "
                "Example Output: 'Seeker seems {{trait}}, consider {{action}}.' OR 'Given Seeker's {{pattern}}, {{NPC_reaction_hint}}.' "
                "Be very brief. Do NOT reveal the raw profile data itself, but its implications."
            )
        },
        {
            "role": "user",
            "content": (
                f"Seeker's Psychological Profile Summary:\n{profile_summary_for_prompt}\n\n"
                f"NPC Details:\n"
                f"- Name: {npc_name}\n"
                f"- Role: {npc_role}\n"
                f"- Motivation: {npc_motivation}\n"
                f"Overall Story Context: {story_context_summary}\n\n"
                f"Provide 1-2 extremely concise insights for {npc_name} based on the Seeker's profile summary:"
            )
        }
    ]
    try:
        insights_text, stats = llm_wrapper_func(
            messages=prompt_messages, model_name=model_name, stream=False, collect_stats=False
        )
        if stats and stats.get("error"):
            return ""
        return insights_text.strip() if insights_text else ""
    except Exception as e:
        return ""

def get_profile_update_suggestions_from_llm(
        previous_profile_json_str: str,
        interaction_log_json_str: str,
        player_actions_summary_json_str: str,
        llm_wrapper_func: Callable,
        model_name: str,
        TF: type = TerminalFormatter
) -> Dict[str, Any]:
    system_prompt_content = f"""You are an AI analyzing a player's recent interactions in a text-based RPG to update their psychological profile.
The player's current profile is:
{previous_profile_json_str}

The recent interaction log (last few turns with an NPC) is:
{interaction_log_json_str}

The player's key actions this turn were:
{player_actions_summary_json_str}

Based *only* on the RECENT interaction log and actions, analyze the player's behavior.
Suggest updates to their 'core_traits' (values between 1-10, suggest incremental changes like "+1", "-0.5"),
new 'decision_patterns' (short descriptive strings, e.g., "expressed_anger_to_npc_X", "showed_skepticism_about_Y"),
and new 'key_experiences_tags' (short descriptive tags, e.g., "confronted_theron_verbally", "aided_syra_with_offering").
Also, consider if 'interaction_style_summary' or 'veil_perception' should be subtly updated based on recent events.
Do NOT invent NPCs or extensive new motivations unless directly implied by actions.
Focus on direct implications of the provided log and actions.

Output your suggested updates STRICTLY as a JSON object.
Example of desired JSON output format:
{{
  "trait_adjustments": {{ "caution": "+0.5", "empathy": "-1", "aggression": "+1" }},
  "new_decision_patterns": ["prefers_questions_over_statements", "hesitated_before_acting"],
  "new_key_experiences_tags": ["questioned_npc_authority_X", "expressed_anger_to_Lyra_about_Theron"],
  "updated_interaction_style_summary": "More inquisitive and slightly more assertive.",
  "updated_veil_perception": "slightly_more_concerned",
  "analysis_notes": "Player asked multiple probing questions to Lyra regarding Theron, indicating increased skepticism and emerging anger. Player stated 'sono arrabbiato con l'alto giudice'."
}}
If no significant changes are warranted for a category, omit it or provide an empty list/dict for it.
'analysis_notes' should briefly explain your reasoning.
ONLY output the JSON object. Do not include any explanatory text before or after the JSON.
Ensure all keys and string values in the JSON are enclosed in double quotes.
Ensure there are no trailing commas.
"""
    messages = [{"role": "system", "content": system_prompt_content}]

    try:
        response_text, stats = llm_wrapper_func(
            messages=messages,
            model_name=model_name,
            stream=False, # Profile analysis should be non-streamed
            collect_stats=True
        )
        if stats and stats.get("error"):
            print(f"{TF.RED}LLM Error during profile update suggestion: {stats['error']}{TF.RESET}")
            return {"analysis_notes": f"LLM error: {stats['error']}"}

        cleaned_response_text = response_text.strip()

        # Uncomment these for deep debugging of LLM response
        # print(f"{TF.DIM}--- RAW LLM RESPONSE (len: {len(response_text)}) FOR PROFILE UPDATE ---{TF.RESET}")
        # print(repr(response_text))
        # print(f"{TF.DIM}--- CLEANED LLM RESPONSE (len: {len(cleaned_response_text)}) ---{TF.RESET}")
        # print(repr(cleaned_response_text))

        json_to_parse = None
        # Try to find JSON within markdown code blocks first
        json_match_markdown = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", cleaned_response_text, re.MULTILINE)
        if json_match_markdown:
            json_to_parse = json_match_markdown.group(1)
            # print(f"{TF.DIM}Extracted JSON via markdown block.{TF.RESET}")
        else:
            # If not in markdown, try to find the first occurrence of a valid JSON object
            # This regex tries to find a balanced {} block. It's not perfect for all edge cases of nested objects within other text.
            json_match_direct = re.search(r"^\s*(\{[\s\S]*?\})\s*$", cleaned_response_text, re.MULTILINE) # Try to match if JSON is the whole string
            if json_match_direct:
                json_to_parse = json_match_direct.group(1)
                # print(f"{TF.DIM}Extracted JSON via direct object search (whole string).{TF.RESET}")
            else: # Fallback: try to find any object, more risky if there's surrounding text
                first_brace = cleaned_response_text.find('{')
                last_brace = cleaned_response_text.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_to_parse = cleaned_response_text[first_brace : last_brace+1]
                    # print(f"{TF.DIM}Attempting extraction from first '{'{' to last '}'}'.{TF.RESET}")
                else:
                    # print(f"{TF.YELLOW}Could not find a clear JSON block in the response. Attempting to parse cleaned text directly.{TF.RESET}")
                    json_to_parse = cleaned_response_text # Last resort

        if not json_to_parse:
            print(f"{TF.RED}No parsable JSON content identified in LLM response: '{response_text}'{TF.RESET}")
            return {"analysis_notes": "No parsable JSON content identified in LLM response."}

        try:
            # print(f"{TF.DIM}Attempting to parse: {repr(json_to_parse)}{TF.RESET}")
            suggestions = json.loads(json_to_parse)
            # print(f"{TF.GREEN}Successfully parsed JSON from LLM.{TF.RESET}")
            return suggestions
        except json.JSONDecodeError as je:
            print(f"{TF.RED}Error decoding LLM JSON response: {je}{TF.RESET}")
            print(f"{TF.DIM}Failed to parse text segment: {repr(json_to_parse)}{TF.RESET}")
            print(f"{TF.DIM}Original full LLM response was: {repr(response_text)}{TF.RESET}")
            return {"analysis_notes": f"Failed to decode LLM JSON. Segment: {json_to_parse[:100]}..."}

    except Exception as e:
        print(f"{TF.RED}Exception during LLM call or processing for profile update: {type(e).__name__} - {e}{TF.RESET}")
        # traceback.print_exc() # Uncomment for full traceback during development
        return {"analysis_notes": f"Exception during LLM call/processing: {type(e).__name__}"}


def apply_llm_suggestions_to_profile(
        current_profile: Dict[str, Any],
        suggestions: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    updated_profile = copy.deepcopy(current_profile)
    changes_made_descriptions = []

    if not isinstance(suggestions, dict):
        changes_made_descriptions.append("LLM suggestions were not in the expected dict format.")
        return updated_profile, changes_made_descriptions

    analysis_notes = suggestions.get("analysis_notes")
    if analysis_notes and isinstance(analysis_notes, str):
        changes_made_descriptions.append(f"LLM Analysis: {analysis_notes}")

    trait_adjustments = suggestions.get("trait_adjustments")
    if isinstance(trait_adjustments, dict):
        if "core_traits" not in updated_profile or not isinstance(updated_profile["core_traits"], dict):
            updated_profile["core_traits"] = copy.deepcopy(DEFAULT_PROFILE["core_traits"])
        for trait, adjustment_str in trait_adjustments.items():
            if trait in updated_profile["core_traits"]:
                try:
                    adjustment_val = float(str(adjustment_str).replace('"', '').strip()) # Clean string like "+1"
                    old_value = updated_profile["core_traits"][trait]
                    new_value = max(1, min(10, round(old_value + adjustment_val, 1)))
                    if new_value != old_value:
                        updated_profile["core_traits"][trait] = new_value
                        changes_made_descriptions.append(f"Trait '{trait}' adjusted from {old_value} to {new_value} (adj: {adjustment_str}).")
                except ValueError:
                    changes_made_descriptions.append(f"Invalid adjustment value '{adjustment_str}' for trait '{trait}'.")

    new_patterns = suggestions.get("new_decision_patterns")
    if isinstance(new_patterns, list):
        if "decision_patterns" not in updated_profile or not isinstance(updated_profile["decision_patterns"], list):
            updated_profile["decision_patterns"] = []
        for pattern in new_patterns:
            if isinstance(pattern, str) and pattern not in updated_profile["decision_patterns"]:
                updated_profile["decision_patterns"].append(pattern)
                changes_made_descriptions.append(f"New decision pattern: '{pattern}'.")

    new_tags = suggestions.get("new_key_experiences_tags")
    if isinstance(new_tags, list):
        if "key_experiences_tags" not in updated_profile or not isinstance(updated_profile["key_experiences_tags"], list):
            updated_profile["key_experiences_tags"] = []
        for tag in new_tags:
            if isinstance(tag, str) and tag not in updated_profile["key_experiences_tags"]:
                updated_profile["key_experiences_tags"].append(tag)
                changes_made_descriptions.append(f"New key experience: '{tag}'.")

    updated_style = suggestions.get("updated_interaction_style_summary")
    if updated_style and isinstance(updated_style, str) and updated_profile.get("interaction_style_summary") != updated_style:
        updated_profile["interaction_style_summary"] = updated_style
        changes_made_descriptions.append(f"Interaction style updated to: '{updated_style}'.")

    updated_veil = suggestions.get("updated_veil_perception")
    if updated_veil and isinstance(updated_veil, str) and updated_profile.get("veil_perception") != updated_veil:
        updated_profile["veil_perception"] = updated_veil
        changes_made_descriptions.append(f"Veil perception updated to: '{updated_veil}'.")

    if "decision_patterns" in updated_profile: updated_profile["decision_patterns"] = sorted(list(set(updated_profile["decision_patterns"])))
    if "key_experiences_tags" in updated_profile: updated_profile["key_experiences_tags"] = sorted(list(set(updated_profile["key_experiences_tags"])))

    return updated_profile, changes_made_descriptions


def update_player_profile(
        previous_profile: Dict[str, Any],
        interaction_log: List[Dict[str, str]],
        player_actions_summary: List[str],
        llm_wrapper_func: Callable,
        model_name: str,
        current_npc_name: Optional[str] = None,
        TF: type = TerminalFormatter
) -> Tuple[Dict[str, Any], List[str]]:
    profile_for_llm_prompt = copy.deepcopy(get_default_player_profile())
    profile_for_llm_prompt.update(previous_profile)

    previous_profile_json_str = json.dumps(profile_for_llm_prompt, indent=2)
    interaction_log_json_str = json.dumps(interaction_log, indent=2)
    player_actions_summary_json_str = json.dumps(player_actions_summary, indent=2)

    llm_suggestions = get_profile_update_suggestions_from_llm(
        previous_profile_json_str,
        interaction_log_json_str,
        player_actions_summary_json_str,
        llm_wrapper_func,
        model_name,
        TF
    )

    updated_profile, changes_descriptions = apply_llm_suggestions_to_profile(
        previous_profile,
        llm_suggestions
    )

    # Rule-based additions can be minimal or serve as fallbacks/guarantees
    if "key_experiences_tags" not in updated_profile: updated_profile["key_experiences_tags"] = []
    for action_summary in player_actions_summary:
        action_lower = action_summary.lower()
        tag_to_add = None
        # Example: "Gave '100 Credits' to NPC 'High Judge Theron'"
        if "gave" in action_lower and "credits" in action_lower:
            if "gave_credits_to_npc" not in updated_profile["key_experiences_tags"]: tag_to_add = "gave_credits_to_npc"
        elif "gave" in action_lower and "credits" not in action_lower: # Gave an item
            if "gave_item_to_npc" not in updated_profile["key_experiences_tags"]: tag_to_add = "gave_item_to_npc"
        elif "received" in action_lower and "credits" not in action_lower: # Received an item
            if "received_item_from_npc" not in updated_profile["key_experiences_tags"]: tag_to_add = "received_item_from_npc"
        elif "received" in action_lower and "credits" in action_lower:
            if "received_credits_from_npc" not in updated_profile["key_experiences_tags"]: tag_to_add = "received_credits_from_npc"


        if tag_to_add:
            updated_profile["key_experiences_tags"].append(tag_to_add)
            changes_descriptions.append(f"Rule-based key experience (for action tracking): '{tag_to_add}'.")
            updated_profile["key_experiences_tags"] = sorted(list(set(updated_profile["key_experiences_tags"])))

    return updated_profile, changes_descriptions


if __name__ == '__main__':
    print("--- Player Profile Manager LLM-based Update Tests ---")
    profile = get_default_player_profile()
    TF = TerminalFormatter
    def mock_llm_profile_updater(messages, model_name, stream, collect_stats, **kwargs):
        system_prompt_text = messages[0]["content"]
        # print("\n--- MOCK LLM PROMPT FOR PROFILE UPDATE ---") # Keep this for debugging your prompt
        # print(system_prompt_text[:1000] + "...")
        # print("--- END MOCK LLM PROMPT ---\n")

        # Simulate a good JSON response
        suggestions_dict = {
            "trait_adjustments": {"aggression": "+1.5", "empathy": "-0.5", "caution": "+0.2"},
            "new_decision_patterns": ["verbally_confrontational_with_theron", "sought_information_aggressively"],
            "new_key_experiences_tags": ["confronted_theron_about_anger", "paid_theron_for_info"],
            "updated_interaction_style_summary": "Became more direct and confrontational, especially towards Theron.",
            "updated_veil_perception": "slightly_more_distrustful_of_authority_figures_related_to_veil",
            "analysis_notes": "Player expressed direct anger to Lyra about Theron and then gave Theron credits, suggesting a complex interaction pattern."
        }
        # Simulate LLM might add the ```json ``` fences
        # return f"```json\n{json.dumps(suggestions_dict)}\n```", {"error": None}
        return json.dumps(suggestions_dict), {"error": None}


    print(f"Initial Profile: {json.dumps(profile, indent=2)}")

    log1 = [
        {"role": "user", "content": "Sono arrabbiato con l'alto giudice"},
        {"role": "assistant", "content": "Capisco la tua frustrazione, Cercatore."}
    ]
    actions1 = [
        "Said to NPC: 'Sono arrabbiato con l'alto giudice'", # This is a key action for the LLM
        "Gave '100 Credits' to NPC 'High Judge Theron'" # Another key action
    ]

    profile, changes1 = update_player_profile(
        profile, log1, actions1, mock_llm_profile_updater, "test-analyzer-model", "High Judge Theron", TF
    )
    print(f"\nProfile after interaction 1 (Theron): {json.dumps(profile, indent=2)}")
    print(f"Changes Reported: \n - " + "\n - ".join(changes1))

    assert profile["core_traits"]["aggression"] == 4.5 # 3 (default) + 1.5
    assert profile["core_traits"]["empathy"] == 4.5   # 5 (default) - 0.5
    assert "verbally_confrontational_with_theron" in profile["decision_patterns"]
    assert "paid_theron_for_info" in profile["key_experiences_tags"]
    assert "gave_credits_to_npc" in profile["key_experiences_tags"] # From rule-based addition

    print("\n--- Player Profile Manager LLM-based Update Tests Done ---")