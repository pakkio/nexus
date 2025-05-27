# tests/test_player_profile_manager.py
import pytest
import json
from unittest.mock import Mock, MagicMock, patch

# Import the modules to test
from player_profile_manager import (
    get_default_player_profile,
    update_player_profile,
    get_profile_update_suggestions_from_llm,
    apply_llm_suggestions_to_profile,
    get_distilled_profile_insights_for_npc
)

@pytest.fixture
def mock_terminal_formatter():
    class MockTF:
        RED = YELLOW = GREEN = RESET = BOLD = DIM = ""
        MAGENTA = CYAN = BRIGHT_CYAN = BG_BLUE = ""
        BRIGHT_WHITE = BG_GREEN = BLACK = ""
        BRIGHT_MAGENTA = BRIGHT_GREEN = BRIGHT_YELLOW = ITALIC = ""

        @staticmethod
        def format_terminal_text(text, width=80):
            return text
    return MockTF

@pytest.fixture
def default_profile():
    return get_default_player_profile()

@pytest.fixture
def mock_llm_wrapper():
    def mock_llm(messages, model_name, stream=False, collect_stats=True, **kwargs):
        # Verify the system message contains our expected profile analysis markers
        system_content = messages[0]["content"]
        assert "analyzing a player's recent interactions" in system_content.lower()

        # Return a mock profile update suggestion
        suggestions = {
            "trait_adjustments": {"curiosity": "+1.5", "empathy": "-0.5"},
            "new_decision_patterns": ["seeks_knowledge_actively", "questions_authority"],
            "new_key_experiences_tags": ["confronted_npc_about_veil", "discovered_ancient_artifact"],
            "updated_interaction_style_summary": "More assertive and knowledge-seeking than before.",
            "updated_veil_perception": "increasingly_suspicious_of_veil_origins",
            "analysis_notes": "Player showed heightened curiosity but decreased empathy in recent interactions."
        }
        return json.dumps(suggestions), {"total_tokens": 150}
    return mock_llm

@pytest.fixture
def sample_interaction_log():
    return [
        {"role": "user", "content": "Tell me more about the Veil. I don't believe the official story."},
        {"role": "assistant", "content": "The Veil has many mysteries, Seeker. Your skepticism is warranted."}
    ]

@pytest.fixture
def sample_actions():
    return [
        "Asked skeptical questions about the Veil",
        "Expressed disbelief in official explanation",
        "Gave '50 Credits' to NPC 'Merchant Talia'"
    ]

def test_get_default_player_profile():
    """Test that default profile has expected structure and values."""
    profile = get_default_player_profile()

    # Check core structure
    assert isinstance(profile, dict)
    assert "core_traits" in profile
    assert "decision_patterns" in profile
    assert "interaction_style_summary" in profile
    assert "key_experiences_tags" in profile

    # Check specific values
    assert profile["core_traits"]["curiosity"] == 5
    assert profile["core_traits"]["aggression"] == 3
    assert isinstance(profile["decision_patterns"], list)
    assert isinstance(profile["key_experiences_tags"], list)

def test_get_profile_update_suggestions_from_llm(mock_llm_wrapper, mock_terminal_formatter):
    """Test that profile update suggestions are correctly requested from LLM."""
    profile_json = json.dumps(get_default_player_profile())
    interaction_log_json = json.dumps([{"role": "user", "content": "Test message"}])
    actions_json = json.dumps(["Test action"])

    suggestions = get_profile_update_suggestions_from_llm(
        profile_json, interaction_log_json, actions_json,
        mock_llm_wrapper, "test-model", mock_terminal_formatter
    )

    # Verify we got a dictionary with expected fields
    assert isinstance(suggestions, dict)
    assert "trait_adjustments" in suggestions
    assert "new_decision_patterns" in suggestions
    assert "analysis_notes" in suggestions

def test_apply_llm_suggestions_to_profile(default_profile):
    """Test that profile updates are correctly applied from LLM suggestions."""
    # Create test suggestions
    suggestions = {
        "trait_adjustments": {"curiosity": "+2", "empathy": "-1"},
        "new_decision_patterns": ["test_pattern"],
        "new_key_experiences_tags": ["test_experience"],
        "updated_interaction_style_summary": "New style summary.",
        "updated_veil_perception": "new_perception",
        "analysis_notes": "Test analysis."
    }

    # Apply suggestions
    updated_profile, changes = apply_llm_suggestions_to_profile(default_profile, suggestions)

    # Verify core traits were updated correctly
    assert updated_profile["core_traits"]["curiosity"] == 7  # 5 + 2
    assert updated_profile["core_traits"]["empathy"] == 4    # 5 - 1

    # Verify other fields were updated
    assert "test_pattern" in updated_profile["decision_patterns"]
    assert "test_experience" in updated_profile["key_experiences_tags"]
    assert updated_profile["interaction_style_summary"] == "New style summary."
    assert updated_profile["veil_perception"] == "new_perception"

    # Verify changes descriptions
    assert len(changes) > 0
    assert any("curiosity" in change for change in changes)
    assert any("test_pattern" in change for change in changes)
    assert any("test_experience" in change for change in changes)

def test_apply_llm_suggestions_trait_boundaries(default_profile):
    """Test that trait adjustments respect min/max boundaries."""
    # Create suggestions that would exceed boundaries
    suggestions = {
        "trait_adjustments": {
            "curiosity": "+10",  # Should max out at 10
            "empathy": "-10"     # Should min out at 1
        }
    }

    # Apply suggestions
    updated_profile, changes = apply_llm_suggestions_to_profile(default_profile, suggestions)

    # Verify traits were capped at boundaries
    assert updated_profile["core_traits"]["curiosity"] == 10
    assert updated_profile["core_traits"]["empathy"] == 1

def test_update_player_profile_full_flow(
        default_profile, sample_interaction_log, sample_actions,
        mock_llm_wrapper, mock_terminal_formatter
):
    """Test the complete profile update flow."""
    # Perform a full update
    updated_profile, changes = update_player_profile(
        previous_profile=default_profile,
        interaction_log=sample_interaction_log,
        player_actions_summary=sample_actions,
        llm_wrapper_func=mock_llm_wrapper,
        model_name="test-model",
        current_npc_name="Test NPC",
        TF=mock_terminal_formatter
    )

    # Verify profile was updated
    assert updated_profile != default_profile
    assert updated_profile["core_traits"]["curiosity"] > default_profile["core_traits"]["curiosity"]

    # Verify changes were described
    assert len(changes) > 0

    # Verify rule-based additions worked
    assert "gave_credits_to_npc" in updated_profile["key_experiences_tags"]
    assert any("Rule-based" in change for change in changes)

def test_get_distilled_profile_insights_for_npc(
        default_profile, mock_llm_wrapper, mock_terminal_formatter
):
    """Test that profile insights for NPC are correctly generated."""
    # Create test NPC data
    npc_data = {
        "name": "Merchant Talia",
        "role": "Information Broker",
        "motivation": "Accumulate knowledge and wealth"
    }

    # Get insights
    with patch("player_profile_manager.llm_wrapper") as mock_llm:
        mock_llm.return_value = ("Seeker shows high curiosity; appeal to their thirst for knowledge.", {})

        insights = get_distilled_profile_insights_for_npc(
            default_profile, npc_data, "The Veil is unstable",
            mock_llm_wrapper, "test-model", mock_terminal_formatter
        )

    # Verify we got meaningful insights
    assert isinstance(insights, str)
    assert len
