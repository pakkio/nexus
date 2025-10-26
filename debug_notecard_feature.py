#!/usr/bin/env python3
"""Debug where notecard_feature gets lost during NPC processing"""

import json
from db_manager import DbManager
from chat_manager import build_npc_system_prompt

def test_notecard_feature_loss():
    print("=== DEBUGGING NOTECARD_FEATURE LOSS ===\n")
    
    # Step 1: Direct database access
    print("STEP 1: Direct database access")
    db = DbManager()
    db.use_mockup = True
    
    elira = db.get_npc('forest', 'elira')
    print(f"✓ DB get_npc result: notecard_feature present = {bool(elira.get('notecard_feature'))}")
    if elira.get('notecard_feature'):
        print(f"  Content length: {len(elira['notecard_feature'])} chars")
        print(f"  First 100 chars: {elira['notecard_feature'][:100]}")
    
    # Step 2: Mock game session state (as in server)
    print("\nSTEP 2: Mock game session state (simulating server behavior)")
    
    # This simulates what app.py does:
    # player_system.game_state['current_npc'] = npc_data
    mock_game_state = {
        'player_id': 'debug_player',
        'model_name': 'test-model',
        'current_area': 'forest',
        'current_npc': elira,  # This is the critical assignment
        'db': db,
        'storyboard_text': 'Test story'
    }
    
    print(f"✓ Game state current_npc: notecard_feature present = {bool(mock_game_state['current_npc'].get('notecard_feature'))}")
    
    # Step 3: Call build_npc_system_prompt (as chat_manager does)
    print("\nSTEP 3: Call build_npc_system_prompt (as chat_manager.py does)")
    
    try:
        system_prompt = build_npc_system_prompt(mock_game_state)
        
        print(f"✓ System prompt generated, length: {len(system_prompt)} chars")
        
        # Check if notecard instructions are in the prompt
        notecard_found = 'notecard' in system_prompt.lower()
        segreti_found = 'segreti_della_foresta' in system_prompt.lower()
        
        print(f"✓ Prompt contains 'notecard': {notecard_found}")
        print(f"✓ Prompt contains 'segreti_della_foresta': {segreti_found}")
        
        if notecard_found:
            print("\n✅ SUCCESS: Notecard feature is working!")
        else:
            print("\n❌ PROBLEM: Notecard feature not found in prompt")
            
        # Debug: check the debug file that gets created
        try:
            with open('/tmp/elira_notecard_debug.txt', 'r') as f:
                debug_content = f.read()
            print(f"\nDEBUG FILE CONTENT:")
            print(debug_content)
        except FileNotFoundError:
            print("\nDEBUG FILE: Not found")
        
        return system_prompt
        
    except Exception as e:
        print(f"❌ ERROR in build_npc_system_prompt: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    prompt = test_notecard_feature_loss()
    
    if prompt and 'segreti_della_foresta' not in prompt.lower():
        print("\n=== ADDITIONAL DEBUG ===")
        print("Searching for any mention of 'NOTECARD' in prompt:")
        lines = prompt.split('\n')
        for i, line in enumerate(lines):
            if 'notecard' in line.lower():
                print(f"Line {i+1}: {line}")
        
        print("\nSearching for 'EXAMPLE' in prompt (from notecard_feature):")
        for i, line in enumerate(lines):
            if 'example' in line.lower():
                print(f"Line {i+1}: {line}")