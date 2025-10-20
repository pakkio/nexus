#!/usr/bin/env python3
"""
Realistic test of NPC conversations through the actual game loop
Tests if PREFIX files are being used in actual NPC responses
"""

import os
import sys

# Enable debugging
os.environ['DEBUG_PREFIX_SEARCH'] = 'false'  # Set to true for verbose output
os.environ['DEBUG_SYSTEM_PROMPT'] = 'false'  # Set to true for verbose output

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DbManager
from terminal_formatter import TerminalFormatter
from chat_manager import ChatSession
import session_utils
from llm_wrapper import llm_wrapper
import time

def test_realistic_npc_conversation():
    """Test a realistic NPC conversation flow"""

    print("="*80)
    print("REALISTIC NPC CONVERSATION TEST")
    print("="*80)
    print()

    try:
        db = DbManager()
        TF = TerminalFormatter()

        # Test with Garin (village)
        area_name = 'village'
        npc_name = 'garin'
        player_id = 'test_player_realistic'
        model_name = 'anthropic/claude-3.5-haiku'

        print(f"Testing conversation with {npc_name.upper()} in {area_name.upper()}")
        print("-" * 80)

        # Get NPC data
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"✗ Could not load NPC data for {npc_name}")
            return

        print(f"✓ Loaded NPC data for {npc_name}")
        print(f"  - area: {npc_data.get('area')}")
        print(f"  - name: {npc_data.get('name')}")
        print(f"  - role: {npc_data.get('role')}")

        # Build system prompt (which should include PREFIX)
        game_session_state = {
            'player_id': player_id,
            'model_name': model_name,
            'profile_analysis_model_name': model_name,
            'brief_mode': False,
            'wise_guide_npc_name': 'lyra',
            'in_hint_mode': False,
            'in_lyra_hint_mode': False,
        }

        story = "Test story for this session"
        system_prompt = session_utils.build_system_prompt(
            npc_data, story, TF,
            game_session_state=game_session_state
        )

        print(f"\n✓ Built system prompt: {len(system_prompt)} chars")
        if "CONTESTO NARRATIVO PERSONALIZZATO" in system_prompt:
            print(f"  ✓ System prompt CONTAINS PREFIX marker")
            # Show first few lines of PREFIX
            lines = system_prompt.split('\n')
            prefix_start = next((i for i, l in enumerate(lines) if 'CONTESTO NARRATIVO' in l), -1)
            if prefix_start >= 0:
                print(f"\n  PREFIX Content Preview (first 300 chars):")
                prefix_content = '\n'.join(lines[prefix_start:prefix_start+5])
                print(f"  {prefix_content[:300]}...")
        else:
            print(f"  ✗ System prompt DOES NOT contain PREFIX marker")

        # Create chat session
        chat_session = ChatSession(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)

        print(f"\n✓ Created chat session")

        # Test conversation - send a message
        user_message = "Hello Garin, I need some help with metal tools"
        print(f"\n--- CONVERSATION ---")
        print(f"Player > {user_message}")

        # Add user message to history
        chat_session.add_message("user", user_message)

        # Get LLM response
        print(f"\nCalling LLM for response...")
        start_time = time.time()

        npc_response, stats = chat_session.ask(
            user_message,
            current_npc_name_for_placeholder=npc_name,
            stream=False,
            collect_stats=True,
            npc_data=npc_data,
            game_session_state=game_session_state
        )

        elapsed_time = time.time() - start_time

        print(f"\n✓ Got LLM response in {elapsed_time:.2f}s")
        print(f"\nGarin > {npc_response}")

        # Analyze response
        print(f"\n--- RESPONSE ANALYSIS ---")
        if npc_response:
            if len(npc_response) < 50:
                print(f"⚠️  Response is very short: {len(npc_response)} chars")
            else:
                print(f"✓ Response length: {len(npc_response)} chars (good)")

            # Check if response seems generic
            generic_indicators = [
                "Bentornato",
                "Di cosa volevi parlare",
                "viandante",
                "Salve",
            ]

            is_generic = any(indicator in npc_response for indicator in generic_indicators)
            if is_generic:
                print(f"⚠️  Response contains generic greeting indicators")
            else:
                print(f"✓ Response does NOT contain generic greetings")

            # Check if response mentions Garin-specific concepts
            garin_indicators = [
                "metallo",
                "memoria",
                "forgia",
                "martello",
                "acciaio",
                "ferro",
                "crafted",
                "craft",
                "tool",
                "passion",
            ]

            has_garin_context = any(ind.lower() in npc_response.lower() for ind in garin_indicators)
            if has_garin_context:
                print(f"✓ Response contains Garin-specific context keywords")
            else:
                print(f"⚠️  Response lacks Garin-specific context")

        else:
            print(f"✗ Empty response from LLM!")

        # Show stats
        if stats:
            print(f"\n--- LLM STATS ---")
            print(f"Model: {stats.get('model', 'Unknown')}")
            print(f"Input tokens: {stats.get('input_tokens', '?')}")
            print(f"Output tokens: {stats.get('output_tokens', '?')}")
            print(f"Total time: {stats.get('total_time', '?')}s")
            if stats.get('error'):
                print(f"⚠️  Error: {stats.get('error')}")

        # Show full chat history for debugging
        print(f"\n--- FULL CHAT HISTORY ---")
        history = chat_session.get_history()
        for i, msg in enumerate(history):
            role = msg.get('role', '?')
            content = msg.get('content', '')
            if role == 'system':
                print(f"[{i}] SYSTEM: {content[:200]}...")
            else:
                print(f"[{i}] {role.upper()}: {content}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_realistic_npc_conversation()
