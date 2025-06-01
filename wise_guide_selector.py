import os
from typing import List, Dict, Any, Optional, Callable

try:
    # Attempt to import the project's llm_wrapper
    from llm_wrapper import llm_wrapper
except ImportError:
    # Fallback if running standalone or llm_wrapper is not in PYTHONPATH
    print("WARNING (wise_guide_selector): llm_wrapper.py not found in standard path. Using a dummy fallback.")
    def llm_wrapper(messages: List[Dict[str, str]], model_name: Optional[str], stream: bool, collect_stats: bool = False, **kwargs) -> tuple[str, dict | None]:
        """Dummy LLM wrapper for fallback."""
        print(f"DUMMY LLM CALL: Wise guide selection for model {model_name} with messages: {messages}")
        # In a real scenario, you might have a very simple rule here, or default to first NPC or a known sage.
        # For this refactor, we assume it tries to find Lyra if possible, or gives up.
        if any("Lyra" in msg.get("content", "") for msg in messages if msg.get("role") == "user"):
             return "Lyra", {"model": "dummy", "total_tokens": 10, "error": None}
        return "NONE", {"model": "dummy", "total_tokens": 5, "error": "No specific guide identifiable by dummy."}

try:
    from terminal_formatter import TerminalFormatter
except ImportError:
    class TerminalFormatter:
        YELLOW = ""; RESET = ""; DIM = ""

TF = TerminalFormatter

def get_wise_guide_npc_name(story_description: str, db: Any, llm_model_name: Optional[str] = None) -> Optional[str]:
    """
    Determines the wise guide's NPC name for a given story description.
    Uses the LLM to pick from available NPCs based on the story context.
    If an LLM is not available or fails, it might fall back to a heuristic or None.

    Args:
        story_description (str): The description of the current story.
        db (Any): The database manager instance to fetch NPC list.
        llm_model_name (Optional[str]): Specific model to use for this LLM call.

    Returns:
        Optional[str]: The name of the chosen wise guide NPC, or None.
    """
    print(f"{TF.DIM}[WiseGuideSelector] Attempting to determine wise guide...{TF.RESET}")
    npc_list = []
    if hasattr(db, "list_npcs_by_area") and callable(db.list_npcs_by_area):
        npc_list = db.list_npcs_by_area()
    else:
        print(f"{TF.YELLOW}[WiseGuideSelector] DB object does not have 'list_npcs_by_area' method.{TF.RESET}")
        return None # Cannot proceed without NPC list

    if not npc_list:
        print(f"{TF.YELLOW}[WiseGuideSelector] No NPCs found in the database to choose from.{TF.RESET}")
        return None

    npc_names = sorted(list(set(npc.get('name', '') for npc in npc_list if npc.get('name'))))

    if not npc_names:
        print(f"{TF.YELLOW}[WiseGuideSelector] No valid NPC names available to choose from.{TF.RESET}")
        return None

    # Determine the model to use for this specific call
    # Use the provided llm_model_name, or a general purpose model if not specified
    # This could also come from an environment variable like 'GUIDE_SELECTOR_LLM_MODEL'
    selector_model = llm_model_name or os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free")


    prompt_messages = [
        {"role": "system", "content": "You are an expert game AI designer tasked with identifying the most suitable 'wise guide' NPC for a player in a text-based RPG. Based on the story description and a list of available NPCs, you must choose one NPC to fulfill this role. The wise guide is the primary source of hints and overarching guidance for the player."},
        {"role": "user", "content":
            f"""Given this story:
"{story_description}"

And these available NPCs:
{', '.join(npc_names)}

Which single NPC from the list is best suited to the role of the player's 'wise guide' for providing hints and advice?
Consider NPCs whose roles or descriptions suggest wisdom, knowledge, or a central guiding purpose.
Reply ONLY with the exact NPC name from the list. If no NPC seems clearly suitable, reply with "NONE".
"""
        }
    ]

    try:
        answer, stats = llm_wrapper(
            messages=prompt_messages,
            model_name=selector_model, # Use the determined selector model
            stream=False,
            collect_stats=True
        )

        if stats and stats.get("error"):
            print(f"{TF.YELLOW}[WiseGuideSelector] LLM call failed: {stats['error']}. Defaulting to no guide.{TF.RESET}")
            return None

        guide_name = answer.strip().splitlines()[0] # Take the first line of the answer

        if guide_name.upper() == "NONE":
            print(f"{TF.DIM}[WiseGuideSelector] LLM indicated no specific wise guide.{TF.RESET}")
            return None

        # Validate if the returned name is actually in our list of NPCs
        if guide_name in npc_names:
            print(f"{TF.DIM}[WiseGuideSelector] LLM selected '{guide_name}' as the wise guide.{TF.RESET}")
            return guide_name
        else:
            print(f"{TF.YELLOW}[WiseGuideSelector] LLM returned name '{guide_name}' not in available NPC list. Defaulting to no guide.{TF.RESET}")
            # print(f"Available NPCs were: {npc_names}") # For debugging
            return None

    except Exception as e:
        print(f"{TF.YELLOW}[WiseGuideSelector] Exception during LLM call for wise guide: {e}. Defaulting to no guide.{TF.RESET}")
        return None

if __name__ == '__main__':
    # Example Usage (requires a mock DB and llm_wrapper to be available or correctly pathed)
    class MockDB:
        def list_npcs_by_area(self):
            return [
                {'name': 'Lyra', 'role': 'Sage'},
                {'name': 'Boros', 'role': 'Old Warrior'},
                {'name': 'Elara', 'role': 'Mystic'},
                {'name': 'Zarthus', 'role': 'Dark Sorcerer'}
            ]

    mock_db_instance = MockDB()
    test_story = "A great darkness is falling upon the land, and ancient prophecies speak of a hero who must seek out forgotten lore. The Veil between worlds is thin, and only knowledge can mend it. Seekers of truth often turn to Lyra, the Sage of the Sanctum, or Boros, the old warrior of the mountains, for their profound wisdom."

    # To make this test runnable standalone, ensure OPENROUTER_API_KEY is set if llm_wrapper uses it.
    # For a true unit test, llm_wrapper itself should be mocked.
    if 'llm_wrapper' not in globals() or llm_wrapper.__name__ == 'llm_wrapper': # Check if it's the real one
        print("Note: Running with potentially real LLM call for testing wise_guide_selector. Ensure API keys are set if needed.")

    selected_guide = get_wise_guide_npc_name(test_story, mock_db_instance)

    if selected_guide:
        print(f"Selected Wise Guide: {selected_guide}")
    else:
        print("No wise guide was selected.")