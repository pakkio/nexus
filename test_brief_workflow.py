#!/usr/bin/env python3
"""
Test script to verify brief mode workflow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_brief_mode_workflow():
    print("=== Testing Brief Mode Workflow ===")
    
    try:
        from db_manager import DbManager
        from command_processor import process_input_revised
        from terminal_formatter import TerminalFormatter
        from chat_manager import ChatSession  # Add this import
        
        # Initialize minimal game state
        print("1. Initializing minimal game state...")
        db = DbManager(use_mockup=True)
        
        # Create basic state
        state = {
            'db': db,
            'player_id': 'test_player',
            'story': 'test story',
            'current_area': 'sanctumofwhispers',
            'current_npc': None,
            'chat_session': None,
            'model_name': 'test-model',
            'TerminalFormatter': TerminalFormatter,
            'ChatSession': ChatSession,  # Add this
            'player_inventory': [],
            'player_credits_cache': 100,
            'brief_mode': False  # Start with brief mode off
        }
        
        # Test brief mode toggle
        print("2. Testing brief mode toggle...")
        result = process_input_revised("/brief on", state)
        
        brief_status = result.get('brief_mode', False)
        print(f"   Brief mode after toggle: {brief_status}")
        
        if brief_status:
            print("   ✅ Brief mode toggle successful")
        else:
            print("   ❌ Brief mode toggle failed")
            return
        
        # Move to an area with an NPC
        print("3. Moving to city...")
        result = process_input_revised("/go city", result)
        
        current_area = result.get('current_area')
        print(f"   Current area: {current_area}")
        
        # Start talking to an NPC
        print("4. Starting conversation with Cassian...")
        result = process_input_revised("/talk cassian", result)
        
        # Check if chat session exists and has system prompt
        chat_session = result.get('chat_session')
        if chat_session and hasattr(chat_session, 'system_prompt'):
            system_prompt = chat_session.system_prompt or ""
            has_brief_instructions = "MODALITÀ BRIEF ATTIVA" in system_prompt
            print(f"   System prompt contains brief instructions: {has_brief_instructions}")
            
            if has_brief_instructions:
                print("   ✅ Brief mode instructions found in system prompt")
                print("   ✅ Brief mode workflow is working correctly!")
            else:
                print("   ❌ Brief mode instructions NOT found in system prompt")
                print(f"   System prompt length: {len(system_prompt)} chars")
                if system_prompt:
                    print(f"   System prompt preview: {system_prompt[:300]}...")
        else:
            print("   ❌ No chat session or system prompt found")
        
        print("\n=== Test Complete ===")
        return result
        
    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_brief_mode_workflow()