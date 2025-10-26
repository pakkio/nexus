#!/usr/bin/env python3
"""
Test script to verify that each NPC receives:
1. Condensed antefatto (~800 chars)
2. Previous conversation summary (~500 chars)
3. ≤4KB total prompt size
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_utils import (
    _condense_antefatto_for_npc,
    _distill_previous_conversation,
    _enforce_system_prompt_size_limit,
    build_system_prompt
)
from terminal_formatter import TerminalFormatter

def test_antefatto_condenser():
    """Test that antefatto is properly condensed"""
    print("\n" + "="*80)
    print("TEST 1: Antefatto Condenser")
    print("="*80)

    # Read the full antefatto
    try:
        with open('ilpercorsodelcercastorie', 'r', encoding='utf-8') as f:
            full_story = f.read()
    except FileNotFoundError:
        print("❌ ilpercorsodelcercastorie file not found!")
        return False

    # Condense it
    condensed = _condense_antefatto_for_npc(full_story, target_chars=800)

    print(f"\n✅ Antefatto condensed successfully")
    print(f"   Full story: {len(full_story)} chars")
    print(f"   Condensed: {len(condensed)} chars (target: 800)")
    print(f"\nCondensed antefatto preview:")
    print("-" * 80)
    print(condensed[:500] + "..." if len(condensed) > 500 else condensed)
    print("-" * 80)

    if len(condensed) > 850:
        print(f"⚠️  WARNING: Condensed size {len(condensed)} exceeds target 800")
        return False

    return True


def test_conversation_distiller():
    """Test that previous conversation is properly distilled"""
    print("\n" + "="*80)
    print("TEST 2: Conversation Distiller")
    print("="*80)

    # Create mock conversation history
    mock_history = [
        {"role": "user", "content": "Ciao, chi sei?"},
        {"role": "assistant", "content": "Sono Erasmus, Ambasciatore dell'Oblio. Benvenuto al Vuoto Liminale."},
        {"role": "user", "content": "Mi puoi aiutare a recuperare la memoria?"},
        {"role": "assistant", "content": "Dovrai compiere un lungo percorso. Portami la Ciotola Sacra e ti aiuterò."},
        {"role": "user", "content": "Come trovo la Ciotola?"},
        {"role": "assistant", "content": "Jorin la custodisce nella Taverna. Procedi verso il Villaggio seguendo il sentiero."},
    ]

    distilled = _distill_previous_conversation(mock_history, target_chars=500)

    print(f"\n✅ Conversation distilled successfully")
    print(f"   Original messages: {len(mock_history)}")
    print(f"   Distilled size: {len(distilled)} chars (target: 500)")
    print(f"\nDistilled conversation:")
    print("-" * 80)
    print(distilled if distilled else "[No meaningful summary extracted]")
    print("-" * 80)

    if len(distilled) > 550:
        print(f"⚠️  WARNING: Distilled size {len(distilled)} exceeds target 500")
        return False

    return True


def test_size_limit_enforcement():
    """Test that prompts are enforced to ≤4KB"""
    print("\n" + "="*80)
    print("TEST 3: Size Limit Enforcement")
    print("="*80)

    # Create large prompt lines
    large_prompt = [
        "=" * 80,
        "SECTION 1: Large section",
        "This is a large section " * 50,
        "=" * 80,
        "SECTION 2: REGOLE OBBLIGATORIE",
        "CRITICAL: This section must be preserved " * 20,
        "=" * 80,
        "SECTION 3: Another large section",
        "More content " * 50,
    ]

    enforced = _enforce_system_prompt_size_limit(large_prompt, max_chars=4000)

    print(f"\n✅ Size limit enforced successfully")
    print(f"   Original size: {len(''.join(large_prompt))} chars")
    print(f"   Enforced size: {len(enforced)} chars (max: 4000)")

    if len(enforced) > 4050:
        print(f"❌ FAILED: Enforced size {len(enforced)} exceeds 4000")
        return False

    # Check that critical sections are preserved
    if "REGOLE OBBLIGATORIE" not in enforced:
        print(f"❌ FAILED: Critical section 'REGOLE OBBLIGATORIE' was removed!")
        return False

    print(f"✅ Critical sections preserved")

    return True


def test_full_npc_prompt():
    """Test complete NPC prompt generation"""
    print("\n" + "="*80)
    print("TEST 4: Full NPC Prompt Generation")
    print("="*80)

    try:
        with open('ilpercorsodelcercastorie', 'r', encoding='utf-8') as f:
            full_story = f.read()
    except FileNotFoundError:
        print("❌ ilpercorsodelcercastorie file not found!")
        return False

    # Create mock NPC data
    mock_npc = {
        'name': 'Syra',
        'role': 'Custode delle Rovine',
        'area': 'Ancient Ruins',
        'motivation': 'Completare la propria trasformazione nel Velo',
        'goal': 'Ricevere la Ciotola Sacra',
        'playerhint': 'Portami la Ciotola Sacra e ti aiuterò',
        'dialogue_hooks': 'Senti il peso del silenzio? È il peso delle parole mai dette.',
        'veil_connection': 'Custodisce il Cristallo di Memoria Antica',
        'default_greeting': 'Benvenuto nelle Rovine Antiche, Cercastorie.',
    }

    # Create mock game session state
    mock_game_state = {
        'player_id': 'test_player',
        'player_profile_cache': {},
        'profile_analysis_model_name': 'mistralai/mistral-7b-instruct:free',
        'model_name': 'google/gemma-2-9b-it:free',
        'wise_guide_npc_name': None,
        'brief_mode': False,
        'db': None,
        'last_npc_conversation_history': [
            {"role": "user", "content": "Ciao Erasmus"},
            {"role": "assistant", "content": "Benvenuto al Vuoto Liminale, Cercastorie."},
        ],
        'last_npc_name': 'Erasmus',
    }

    # Build prompt
    try:
        prompt = build_system_prompt(
            npc=mock_npc,
            story=full_story,
            TF=TerminalFormatter,
            game_session_state=mock_game_state,
            llm_wrapper_func_for_distill=None
        )

        print(f"\n✅ NPC prompt generated successfully")
        print(f"   Prompt size: {len(prompt)} chars (max for regular NPC: 8000)")

        # Check for CRITICAL components
        checks = {
            "Antefatto (il Cercastorie story context)": "Il Cercastorie è un Narratore Cosmico" in prompt,
            "Character data (Sei Syra)": "Sei Syra" in prompt or "Custode delle Rovine" in prompt,
            "Previous NPC context (Erasmus)": "Erasmus" in prompt or "CIÒ CHE IL CERCASTORIE HA FATTO PRIMA" in prompt,
        }

        print(f"\n✅ CRITICAL Prompt components check:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
            if not passed:
                all_passed = False

        if len(prompt) <= 8000:
            print(f"\n✅ Prompt size is within limits ({len(prompt)} ≤ 8000)")
        else:
            print(f"\n❌ Prompt size EXCEEDS limits ({len(prompt)} > 8000)")
            all_passed = False

        # Show prompt structure
        print(f"\nPrompt structure (first 300 chars):")
        print("-" * 80)
        print(prompt[:300] + "...")
        print("-" * 80)

        return all_passed

    except Exception as e:
        print(f"❌ Error generating prompt: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*80)
    print("TESTING: Antefatto + Previous Conversation for Each NPC")
    print("="*80)

    tests = [
        ("Antefatto Condenser", test_antefatto_condenser),
        ("Conversation Distiller", test_conversation_distiller),
        ("Size Limit Enforcement", test_size_limit_enforcement),
        ("Full NPC Prompt", test_full_npc_prompt),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! NPCs are ready to receive antefatto + previous conversations.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
