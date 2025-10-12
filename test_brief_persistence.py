#!/usr/bin/env python3
"""
Test script to verify brief mode persistence across conversation sessions
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_brief_mode_persistence():
    print("=== Testing Brief Mode Persistence Across Sessions ===")
    
    try:
        from db_manager import DbManager
        from command_processor import process_input_revised
        from terminal_formatter import TerminalFormatter
        from chat_manager import ChatSession
        
        # Initialize minimal game state
        print("1. Initializing game state...")
        db = DbManager(use_mockup=True)
        
        state = {
            'db': db,
            'player_id': 'test_player',
            'story': 'test story',
            'current_area': 'sanctumofwhispers',
            'current_npc': None,
            'chat_session': None,
            'model_name': 'test-model',
            'TerminalFormatter': TerminalFormatter,
            'ChatSession': ChatSession,
            'player_inventory': [],
            'player_credits_cache': 100,
            'brief_mode': False
        }
        
        # Enable brief mode
        print("2. Enabling brief mode...")
        result = process_input_revised("/brief on", state)
        brief_status = result.get('brief_mode', False)
        print(f"   Brief mode: {brief_status}")
        
        # Initialize variables to track brief mode across conversations
        has_brief_1 = has_brief_2 = has_brief_3 = has_brief_4 = False
        
        # Talk to first NPC (Cassian)
        print("3. Starting conversation with Cassian...")
        result = process_input_revised("/go city", result)
        result = process_input_revised("/talk cassian", result)
        
        chat_session1 = result.get('chat_session')
        if chat_session1 and hasattr(chat_session1, 'system_prompt'):
            has_brief_1 = "MODALITÀ BRIEF ATTIVA" in (chat_session1.system_prompt or "")
            print(f"   Cassian system prompt has brief instructions: {has_brief_1}")
        
        # Switch to second NPC (Theron)  
        print("4. Switching to Theron...")
        result = process_input_revised("/talk theron", result)
        
        chat_session2 = result.get('chat_session')
        if chat_session2 and hasattr(chat_session2, 'system_prompt'):
            has_brief_2 = "MODALITÀ BRIEF ATTIVA" in (chat_session2.system_prompt or "")
            print(f"   Theron system prompt has brief instructions: {has_brief_2}")
        
        # Go to different area and talk to another NPC
        print("5. Going to village and talking to Garin...")
        result = process_input_revised("/go village", result)
        result = process_input_revised("/talk garin", result)
        
        chat_session3 = result.get('chat_session')
        if chat_session3 and hasattr(chat_session3, 'system_prompt'):
            has_brief_3 = "MODALITÀ BRIEF ATTIVA" in (chat_session3.system_prompt or "")
            print(f"   Garin system prompt has brief instructions: {has_brief_3}")
        
        # Test disabling brief mode mid-session
        print("6. Disabling brief mode...")
        result = process_input_revised("/brief off", result)
        brief_status_off = result.get('brief_mode', True)
        print(f"   Brief mode after disable: {brief_status_off}")
        
        # Switch to another NPC to see if brief mode is removed
        print("7. Switching back to Cassian after disabling brief mode...")
        result = process_input_revised("/go city", result)
        result = process_input_revised("/talk cassian", result)
        
        chat_session4 = result.get('chat_session')
        if chat_session4 and hasattr(chat_session4, 'system_prompt'):
            has_brief_4 = "MODALITÀ BRIEF ATTIVA" in (chat_session4.system_prompt or "")
            print(f"   Cassian system prompt has brief instructions after disable: {has_brief_4}")
        
        # Verify persistence check
        if has_brief_1 and has_brief_2 and has_brief_3 and not has_brief_4:
            print("\n   ✅ Brief mode persistence test PASSED")
            print("   ✅ Brief mode correctly applies to all new conversations")
            print("   ✅ Brief mode correctly removes from conversations when disabled")
        else:
            print("\n   ❌ Brief mode persistence test FAILED")
            print(f"   Cassian (first): {has_brief_1}")
            print(f"   Theron: {has_brief_2}")  
            print(f"   Garin: {has_brief_3}")
            print(f"   Cassian (after disable): {has_brief_4}")
        
        print("\n=== Persistence Test Complete ===")
        
    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_brief_mode_persistence()