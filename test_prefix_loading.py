#!/usr/bin/env python3
"""
Test script to verify PREFIX file loading with debug output
"""

import os
import sys

# Enable debugging
os.environ['DEBUG_PREFIX_SEARCH'] = 'true'
os.environ['DEBUG_SYSTEM_PROMPT'] = 'true'

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DbManager
from terminal_formatter import TerminalFormatter
from chat_manager import ChatSession
import session_utils

def test_prefix_loading():
    """Test if PREFIX files are being loaded correctly"""

    print("="*80)
    print("PREFIX LOADING DEBUG TEST")
    print("="*80)
    print()

    # List of NPCs to test
    test_npcs = [
        ('village', 'garin'),
        ('village', 'mara'),
        ('tavern', 'jorin'),
        ('ancientruins', 'syra'),
        ('forest', 'elira'),
        ('mountain', 'boros'),
        ('sanctumofwhispers', 'lyra'),
    ]

    print("\nTesting PREFIX file access directly:")
    print("-" * 80)

    for area, name in test_npcs:
        prefix_file = f"NPC_PREFIX.{area}.{name}.txt"
        try:
            with open(prefix_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✓ {prefix_file}: {len(content)} chars")
        except FileNotFoundError:
            print(f"✗ {prefix_file}: NOT FOUND")
        except Exception as e:
            print(f"✗ {prefix_file}: ERROR - {e}")

    print()
    print("\nTesting _load_npc_narrative_prefix() function:")
    print("-" * 80)

    for area, name in test_npcs:
        print(f"\nTesting: {name} in {area}")
        result = session_utils._load_npc_narrative_prefix(area, name)
        if result:
            print(f"  ✓ Returned {len(result)} chars")
        else:
            print(f"  ✗ Returned empty string")

    print()
    print("\nTesting build_system_prompt with real NPC data:")
    print("-" * 80)

    try:
        db = DbManager()
        TF = TerminalFormatter()

        # Test with Garin (village)
        npc_data = db.get_npc('village', 'garin')
        if npc_data:
            print(f"\n✓ Got NPC data for Garin")
            print(f"  - area: {npc_data.get('area')}")
            print(f"  - name: {npc_data.get('name')}")

            # Build system prompt (this should load PREFIX)
            game_session_state = {
                'player_id': 'test_player',
                'model_name': 'anthropic/claude-3.5-haiku',
                'profile_analysis_model_name': 'anthropic/claude-3.5-haiku',
                'brief_mode': False,
            }

            story = "Test story"
            system_prompt = session_utils.build_system_prompt(
                npc_data, story, TF,
                game_session_state=game_session_state
            )

            print(f"  - system_prompt length: {len(system_prompt)} chars")
            if "CONTESTO NARRATIVO PERSONALIZZATO" in system_prompt:
                print(f"  ✓ System prompt CONTAINS PREFIX marker")
            else:
                print(f"  ✗ System prompt DOES NOT contain PREFIX marker")

            # Show first 500 chars
            print(f"\n  First 500 chars of system prompt:")
            print(f"  {system_prompt[:500]}...")
        else:
            print(f"✗ Could not get NPC data for Garin")

    except Exception as e:
        print(f"✗ Error during build_system_prompt test: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*80)
    print("DEBUG TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_prefix_loading()
