#!/usr/bin/env python3
"""Debug brief mode persistence and system prompt generation."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_manager import DBManager
from chat_manager import build_npc_system_prompt

def test_brief_mode_debug():
    """Test brief mode state persistence and system prompt generation."""
    
    print("=== BRIEF MODE DEBUG TEST ===")
    
    # Initialize DB Manager
    db_manager = DBManager()
    print("✓ DB Manager initialized")
    
    # Test player ID
    player_id = "debug_test_player"
    
    # Create mock game session state
    mock_state = {
        'player_id': player_id,
        'brief_mode': True,  # Enable brief mode
        'player_profile_cache': {
            'core_traits': {'curiosity': 5.0, 'caution': 6.0},
            'interaction_style_summary': 'test style',
            'inferred_motivations': ['test'],
            'philosophical_leaning': 'neutral',
            'veil_perception': 'neutral',
            'achievements': ['Test Achievement'],
            'recent_changes_log': [],
            'llm_analysis_notes': 'test notes'
        },
        'player_inventory': {},
        'player_credits_cache': 100,
        'current_npc': {'name': 'Test NPC'},
        'story': 'Test story context'
    }
    
    print(f"✓ Mock state created with brief_mode={mock_state['brief_mode']}")
    
    # Save the state to ensure brief mode persists
    db_manager.save_player_state(player_id, mock_state)
    print("✓ State saved to database")
    
    # Load the state back
    loaded_state = db_manager.load_player_state(player_id)
    print(f"✓ State loaded. brief_mode={loaded_state.get('brief_mode', 'NOT_FOUND')}")
    
    # Test system prompt generation with brief mode
    system_prompt = build_npc_system_prompt(loaded_state, 'Test NPC')
    
    print("\n=== SYSTEM PROMPT ANALYSIS ===")
    print(f"Prompt length: {len(system_prompt)} chars")
    
    # Check if brief mode instructions are included
    brief_indicators = [
        "MODALITÀ BRIEF ATTIVA",
        "MASSIMO 50-80 PAROLE",
        "LIMITE INVALICABILE",
        "CONTA LE PAROLE"
    ]
    
    found_indicators = []
    for indicator in brief_indicators:
        if indicator in system_prompt:
            found_indicators.append(indicator)
    
    print(f"Brief mode indicators found: {len(found_indicators)}/{len(brief_indicators)}")
    for indicator in found_indicators:
        print(f"  ✓ Found: {indicator}")
    
    missing_indicators = [i for i in brief_indicators if i not in found_indicators]
    for indicator in missing_indicators:
        print(f"  ❌ Missing: {indicator}")
    
    # Show first 500 chars of prompt
    print(f"\n=== FIRST 500 CHARS OF PROMPT ===")
    print(system_prompt[:500])
    print("...")
    
    # Show brief mode section if it exists
    if "MODALITÀ BRIEF ATTIVA" in system_prompt:
        brief_start = system_prompt.find("MODALITÀ BRIEF ATTIVA")
        brief_section = system_prompt[brief_start:brief_start+1000]
        print(f"\n=== BRIEF MODE SECTION ===")
        print(brief_section)
    else:
        print(f"\n❌ BRIEF MODE SECTION NOT FOUND")
    
    # Cleanup
    print(f"\n=== CLEANUP ===")
    try:
        db_manager.delete_player_state(player_id)
        print("✓ Test player state deleted")
    except Exception as e:
        print(f"Warning: Could not delete test state: {e}")

if __name__ == "__main__":
    test_brief_mode_debug()