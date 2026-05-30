#!/usr/bin/env python3
"""
Test script to verify the fix for NPC mention handling.

This test verifies that when an NPC mentions another NPC (like "Boros" or "Lyra"),
and the player responds with something like "vado da Boros", the system correctly
interprets it as DIALOGUE (talking about future plans) rather than a /talk command.

Bug Report Context:
- Syra mentions Boros, player says "vado da Boros" → System was incorrectly showing
  "NPC 'Boros' not found in Ancient Ruins" instead of letting Syra respond naturally.
- Meridia mentions Lyra, player says "vado da Lyra" → Same issue.
"""

from command_interpreter import _fallback_interpretation

def test_npc_mention_scenarios():
    """Test the scenarios reported in the bug."""

    test_state = {
        'current_area': 'Ancient Ruins',
        'current_npc': {'name': 'Syra'},
        'in_lyra_hint_mode': False,
        'available_areas': ['Ancient Ruins', 'City', 'Forest', 'Mountain', 'Sanctum of Whispers', 'Tavern', 'Village', 'Nexus of Paths']
    }

    test_cases = [
        # Bug scenario 1: Syra mentions Boros
        {
            'input': 'vado da Boros',
            'expected_type': 'DIALOGO',
            'description': 'Player mentions going to see Boros (future plan)',
            'scenario': 'Syra mentioned Boros, player responds about going to see him'
        },
        # Bug scenario 2: Meridia mentions Lyra
        {
            'input': 'vado da Lyra',
            'expected_type': 'DIALOGO',
            'description': 'Player mentions going to see Lyra (future plan)',
            'scenario': 'Meridia mentioned Lyra, player responds about going to see her'
        },
        # Additional edge cases
        {
            'input': 'andrò da Boros dopo',
            'expected_type': 'DIALOGO',
            'description': 'Player plans to visit Boros later',
            'scenario': 'Future plan with "dopo" (later)'
        },
        {
            'input': 'saluto e vado da Syra',
            'expected_type': 'DIALOGO',
            'description': 'Player says goodbye and mentions going somewhere',
            'scenario': 'Polite farewell with future plan'
        },
        # Contrast: Explicit talk commands (should still work)
        {
            'input': 'parla con Jorin',
            'expected_type': 'COMANDO',
            'description': 'Player explicitly wants to start conversation',
            'scenario': 'Explicit /talk command using natural language'
        },
        {
            'input': 'voglio parlare con Elira',
            'expected_type': 'COMANDO',
            'description': 'Player explicitly wants to talk to someone',
            'scenario': 'Explicit intention to start conversation'
        },
        # Asking about NPCs (should be dialogue)
        {
            'input': 'parlami di Boros',
            'expected_type': 'DIALOGO',
            'description': 'Player asks NPC to talk about someone',
            'scenario': 'Requesting information about another NPC'
        },
        {
            'input': 'cosa sai di Lyra?',
            'expected_type': 'DIALOGO',
            'description': 'Player asks what NPC knows about someone',
            'scenario': 'Requesting knowledge about another NPC'
        },
        {
            'input': 'chi è Cassian?',
            'expected_type': 'DIALOGO',
            'description': 'Player asks about NPC identity',
            'scenario': 'Requesting information about NPC identity'
        },
    ]

    print("=" * 70)
    print("Testing NPC Mention Handling Fix")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        user_input = test_case['input']
        expected = test_case['expected_type']
        description = test_case['description']
        scenario = test_case['scenario']

        result = _fallback_interpretation(user_input, test_state)
        actual = "COMANDO" if result['is_command'] else "DIALOGO"

        status = "✓ PASS" if actual == expected else "✗ FAIL"
        if actual == expected:
            passed += 1
        else:
            failed += 1

        print(f"Test {i}: {status}")
        print(f"  Input: '{user_input}'")
        print(f"  Expected: {expected}, Got: {actual}")
        print(f"  Description: {description}")
        print(f"  Scenario: {scenario}")

        if actual != expected:
            print(f"  Reasoning: {result['reasoning']}")
            print(f"  Inferred command: {result.get('inferred_command', 'None')}")

        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed! The bug is fixed.")
        print("\nWhat was fixed:")
        print("- NPCs can now mention other NPCs without triggering errors")
        print("- Player statements like 'vado da Boros' are treated as dialogue")
        print("- Player can still use explicit commands like 'parla con Jorin'")
        print("- System distinguishes between future plans and immediate actions")
        return True
    else:
        print("\n✗ Some tests failed. Please review the command interpreter logic.")
        return False

if __name__ == '__main__':
    success = test_npc_mention_scenarios()
    exit(0 if success else 1)
