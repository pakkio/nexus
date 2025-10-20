#!/usr/bin/env python3
"""
Test script to simulate server conversation with 4 NPCs in brief mode
"""

import time
import sys
import os
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_processor import process_input_revised
from db_manager import get_db_manager

def simulate_conversation():
    """Simulate a conversation with 4 NPCs in brief mode"""
    
    print("=== STARTING BRIEF MODE CONVERSATION TEST ===")
    
    # Initialize state
    state = {
        'player_id': 'test_player',
        'current_area': 'Sanctum of Whispers',
        'current_npc_code': 'sanctumofwhispers.lyra',
        'plot_flags': {},
        'credits': 100,
        'brief_mode': False
    }
    
    # List of NPCs to test
    npcs_to_test = [
        ('sanctumofwhispers.lyra', 'Sanctum of Whispers'),
        ('city.cassian', 'City'),
        ('village.garin', 'Village'), 
        ('forest.elira', 'Forest')
    ]
    
    conversations = []
    
    try:
        # 1. Enable brief mode
        print("\n1. Enabling brief mode...")
        result = process_input_revised("/brief on", state)
        if isinstance(result, dict):
            state.update(result)
        brief_status = state.get('brief_mode', False)
        print(f"   Brief mode enabled: {brief_status}")
        
        # 2. Test conversation with each NPC
        for i, (npc_code, area) in enumerate(npcs_to_test, 1):
            print(f"\n{i+1}. Testing conversation with {npc_code} in {area}")
            
            # Move to area if needed
            if state.get('current_area') != area:
                print(f"   Moving to {area}...")
                result = process_input_revised(f"/go {area}", state)
                if isinstance(result, dict):
                    state.update(result)
            
            # Start conversation
            npc_name = npc_code.split('.')[-1]
            print(f"   Starting conversation with {npc_name}...")
            result = process_input_revised(f"/talk {npc_name}", state)
            if isinstance(result, dict):
                state.update(result)
            
            # Send a simple message
            test_message = f"Hello {npc_name}, I'm testing brief mode"
            print(f"   Sending: {test_message}")
            result = process_input_revised(test_message, state)
            if isinstance(result, dict):
                state.update(result)
                
            # Record conversation details
            conversation_info = {
                'npc': npc_code,
                'area': area,
                'message_sent': test_message,
                'brief_mode_active': state.get('brief_mode', False)
            }
            conversations.append(conversation_info)
            
            print(f"   ✓ Conversation with {npc_name} completed")
            
            # Brief pause between conversations
            time.sleep(0.5)
            
        # 3. Summary
        print("\n=== CONVERSATION TEST SUMMARY ===")
        print(f"Brief mode was: {'ENABLED' if state.get('brief_mode') else 'DISABLED'}")
        print(f"Total NPCs tested: {len(conversations)}")
        
        for i, conv in enumerate(conversations, 1):
            print(f"{i}. {conv['npc']} in {conv['area']} - Brief mode: {conv['brief_mode_active']}")
            
        print("\n✓ Brief mode conversation test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during conversation test: {e}")
        import traceback
        traceback.print_exc()
        
    return conversations

if __name__ == "__main__":
    simulate_conversation()