#!/usr/bin/env python3
"""
Test script to verify Elira's improved notecard instructions work with weaker models.
Simulates touch.lsl interaction asking for notecard in Italian.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
AVATAR_NAME = "Salahzar Stenvaag"

def simulate_lsl_headers():
    """Generate headers similar to touch.lsl"""
    return {
        "Content-Type": "application/json",
        "X-SecondLife-Shard": "Production",
        "X-SecondLife-Object-Name": "Elira.Forest",
        "X-SecondLife-Object-Key": "test-elira-uuid-123",
        "X-SecondLife-Region": "Nexus Test (265280, 290304)",
        "X-SecondLife-Local-Position": "(128.0, 128.0, 23.0)",
        "X-SecondLife-Owner-Name": "Test Owner",
        "X-SecondLife-Owner-Key": "owner-uuid-456"
    }

def talk_to_npc(avatar_name, npc_id, message):
    """Send a talk request to the NPC"""
    url = f"{BASE_URL}/api/chat"
    headers = simulate_lsl_headers()

    payload = {
        "player_id": avatar_name,
        "display_name": avatar_name,
        "npc_name": "elira",
        "area": "Forest",
        "message": message
    }

    print(f"\n{'='*80}")
    print(f"[{time.strftime('%H:%M')}] {avatar_name}: {message}")
    print(f"{'='*80}")

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        npc_response = data.get("npc_response", "")
        sl_commands = data.get("sl_commands", "")
        llm_stats = data.get("llm_stats", {})

        print(f"[{time.strftime('%H:%M')}] Elira.Forest: {npc_response}")

        # Show LLM stats
        if llm_stats.get('dialogue'):
            dialogue_stats = llm_stats['dialogue']
            time_ms = dialogue_stats.get('last_call_time_ms', 0)
            tokens_out = dialogue_stats.get('last_tokens_out', 0)
            print(f"[⏱ Tempo risposta: {time_ms/1000:.1f} secondi | Tokens: {tokens_out}]")

        if sl_commands:
            print(f"\n[SL COMMANDS]: {sl_commands[:200]}{'...' if len(sl_commands) > 200 else ''}")

            # Check for notecard
            if "notecard=" in sl_commands:
                print("\n✅ SUCCESS! NOTECARD GENERATED!")
                start = sl_commands.find("notecard=")
                # Find the end - look for the closing bracket
                bracket_count = 0
                end = start
                in_notecard = False
                for i in range(start, len(sl_commands)):
                    if sl_commands[i] == '[':
                        bracket_count += 1
                        in_notecard = True
                    elif sl_commands[i] == ']' and in_notecard:
                        bracket_count -= 1
                        if bracket_count == 0:
                            end = i + 1
                            break

                if end <= start:
                    end = len(sl_commands)

                notecard_section = sl_commands[start:end]
                print(f"\n[NOTECARD CONTENT]:")
                print(notecard_section[:500])
                if len(notecard_section) > 500:
                    print(f"... (truncated, total {len(notecard_section)} chars)")
                return True
            else:
                print("\n❌ NO NOTECARD FOUND in sl_commands")
                return False
        else:
            print("\n⚠️ No SL commands in response")
            return False
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return False

def main():
    """Run the test sequence"""
    print("\n" + "="*80)
    print("TESTING ELIRA NOTECARD WITH IMPROVED ITALIAN INSTRUCTIONS")
    print("="*80)
    print(f"Model: google/gemini-2.0-flash-001")
    print(f"Avatar: {AVATAR_NAME}")
    print(f"NPC: forest.elira")

    # Reset to clean state
    print("\n[Resetting game state...]")
    reset_response = requests.post(
        f"{BASE_URL}/reset",
        headers={"Content-Type": "application/json"},
        json={"key": "1234"}
    )
    if reset_response.status_code == 200:
        print("✓ Game state reset")

    time.sleep(1)

    # Test 1: Ask for notecard directly in Italian
    print("\n\n### TEST 1: Direct notecard request ###")
    success1 = talk_to_npc(AVATAR_NAME, "forest.elira", "mi daresti notecard?")

    time.sleep(2)

    # Test 2: Ask for "nota" (Italian synonym)
    print("\n\n### TEST 2: Ask for 'nota' ###")
    success2 = talk_to_npc(AVATAR_NAME, "forest.elira", "dammi una nota sulla tua missione")

    time.sleep(2)

    # Test 3: Ask for "guida" (guide)
    print("\n\n### TEST 3: Ask for 'guida' ###")
    success3 = talk_to_npc(AVATAR_NAME, "forest.elira", "hai una guida per me?")

    # Summary
    print("\n\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Test 1 (notecard): {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Test 2 (nota): {'✅ PASSED' if success2 else '❌ FAILED'}")
    print(f"Test 3 (guida): {'✅ PASSED' if success3 else '❌ FAILED'}")

    if success1 or success2 or success3:
        print("\n✅ AT LEAST ONE TEST PASSED - Instructions are working!")
    else:
        print("\n❌ ALL TESTS FAILED - LLM may still be too weak or needs more tuning")

    print("="*80)

if __name__ == "__main__":
    main()
