#!/usr/bin/env python3
"""
Test script for Eldoria Narrative Framework integration.

Demonstrates how to use the new narrative generation functions.
"""

from session_utils import build_narrative_prompt, analyze_narrative_quality
from eldoria_narrative_framework import get_narrative_framework, validate_narrative_against_framework
import json


def test_framework_prompt():
    """Test building a narrative prompt with the framework."""
    print("=" * 80)
    print("TEST 1: Building Narrative Prompt")
    print("=" * 80)

    prompt = build_narrative_prompt(
        context="Create an epic tale of a traveler who visits 5 NPCs in Eldoria and must choose sides in an irreconcilable conflict",
        protagonist_name="Cercastorie",
        npcs_list=[
            {"name": "Theron", "role": "Revolutionary"},
            {"name": "Cassian", "role": "Pragmatist"},
            {"name": "Irenna", "role": "Artist"},
            {"name": "Elira", "role": "Guardian"},
            {"name": "Erasmus", "role": "Guide"}
        ]
    )

    print(prompt[:800])
    print("\n... [prompt continues] ...\n")
    return prompt


def test_framework_validation():
    """Test validating a narrative against the framework."""
    print("=" * 80)
    print("TEST 2: Validating Narrative (BAD EXAMPLE - False Synthesis)")
    print("=" * 80)

    bad_narrative = """
    Cercastorie visited all the NPCs and learned that each perspective was
    equally valid and important. Like threads in a beautiful arazzo, each
    ideology contributed something unique to humanity. By honoring all sides,
    Cercastorie achieved wisdom and understanding that transcended the conflict.
    The protagonist learned that all perspectives are complementary, and the
    real victory was learning to appreciate everyone's viewpoint. Thus harmony
    was restored to Eldoria.
    """

    validation = validate_narrative_against_framework(bad_narrative)
    print(f"Validation Result: {json.dumps(validation, indent=2)}")
    print(f"PASSES FRAMEWORK: {validation.get('passes_gates')}")
    return validation


def test_good_narrative_validation():
    """Test validating a narrative that respects the framework."""
    print("=" * 80)
    print("TEST 3: Validating Narrative (GOOD EXAMPLE - Tragic Choice)")
    print("=" * 80)

    good_narrative = """
    Cercastorie traveled through Eldoria and encountered irreconcilable visions.
    Theron demanded the destruction of the Veil itself—a revolution that would
    unmake the world. Cassian counseled exploitation of the Veil's structures
    for profit and power. These were not complementary perspectives; they were
    antagonistic.

    The protagonist had to choose. Supporting Theron meant losing wealth and
    security. Supporting Cassian meant abandoning the quest for liberation that
    had sustained hope. Cercastorie chose revolution, and the scarring regret
    of that choice would never fully heal—colleagues lost, alliances betrayed.

    The narrative remained unresolved: Did the choice matter? Would Theron's
    vision succeed, or was it futile? Cercastorie could not know. Only the
    sacrifice was certain.
    """

    validation = validate_narrative_against_framework(good_narrative)
    print(f"Validation Result: {json.dumps(validation, indent=2)}")
    print(f"PASSES FRAMEWORK: {validation.get('passes_gates')}")
    return validation


def test_framework_direct():
    """Show the raw framework."""
    print("=" * 80)
    print("TEST 4: Raw Framework")
    print("=" * 80)

    framework = get_narrative_framework()
    print(framework[:1200])
    print("\n... [framework continues] ...\n")


if __name__ == "__main__":
    test_framework_direct()
    test_framework_prompt()
    test_framework_validation()
    test_good_narrative_validation()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The Eldoria Narrative Framework is now integrated into the codebase.

Key functions:
  - build_narrative_prompt(context, ...) → Full prompt with framework
  - analyze_narrative_quality(text) → Validation report
  - validate_narrative_against_framework(text) → Raw validation

To use in your code:
    from session_utils import build_narrative_prompt

    prompt = build_narrative_prompt(
        context="Your narrative request",
        protagonist_name="Name",
        npcs_list=[...],
        story_summary="..."
    )

    # Use prompt with your LLM
    response = llm_wrapper(messages=[{"role": "system", "content": prompt}], ...)

The framework enforces:
  ✅ No false synthesis of conflicting ideologies
  ✅ Irreversible costs for every choice
  ✅ Unresolved tensions in the narrative
  ✅ Epistemological humility (protagonist can be wrong)
  ✅ Materiality first (ideas need consequences)
""")
