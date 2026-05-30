#!/usr/bin/env python3
"""Test Jorin's bowl quest with Flash 3"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
PLAYER_ID = "QuestTester"
DISPLAY_NAME = "Adventurer"

def test_jorin_quest():
    print("="*80)
    print("TESTING JORIN'S BOWL QUEST WITH GEMINI FLASH 3")
    print("="*80)

    # Step 1: Meet Garin
    print("\n[STEP 1] Meeting Garin at the forge...")
    response = requests.post(f"{BASE_URL}/sense", json={
        "player_id": PLAYER_ID,
        "display_name": DISPLAY_NAME,
        "npcname": "Garin",
        "area": "Village"
    })

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Garin: {data.get('npc_response', 'N/A')}")
    else:
        print(f"✗ Error: {response.text}")
        return

    time.sleep(2)

    # Step 2: Ask Garin about iron shavings
    print("\n[STEP 2] Asking Garin for iron shavings...")
    response = requests.post(f"{BASE_URL}/api/chat", json={
        "player_id": PLAYER_ID,
        "display_name": DISPLAY_NAME,
        "message": "Hello Garin! Jorin told me you might have some iron shavings. Can I help you with anything?"
    }, timeout=60)

    if response.status_code == 200:
        data = response.json()
        npc_response = data.get('npc_response', '')
        print(f"✓ Garin says: {npc_response[:300]}...")
        print(f"\n[LLM Stats] Model: {data.get('llm_stats', {}).get('dialogue', {}).get('model', 'N/A')}")
        print(f"  Time: {data.get('llm_stats', {}).get('dialogue', {}).get('last_call_time_ms', 0)}ms")
    else:
        print(f"✗ Error: {response.text}")
        return

    time.sleep(2)

    # Step 3: Check inventory
    print("\n[STEP 3] Checking inventory...")
    response = requests.get(f"{BASE_URL}/api/player/{PLAYER_ID}/inventory")

    if response.status_code == 200:
        data = response.json()
        inventory = data.get('inventory', [])
        credits = data.get('credits', 0)
        print(f"✓ Inventory: {inventory}")
        print(f"✓ Credits: {credits}")

        has_iron_shavings = any('trucioli' in item.lower() or 'iron' in item.lower() or 'ferro' in item.lower() for item in inventory)

        if not has_iron_shavings:
            print("\n⚠ No iron shavings received yet. Trying to ask more directly...")
            time.sleep(2)

            response = requests.post(f"{BASE_URL}/api/chat", json={
                "player_id": PLAYER_ID,
                "display_name": DISPLAY_NAME,
                "message": "I would like to help the community. Could you give me some trucioli di ferro?"
            }, timeout=60)

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Garin says: {data.get('npc_response', '')[:300]}...")

                # Check inventory again
                time.sleep(1)
                inv_response = requests.get(f"{BASE_URL}/api/player/{PLAYER_ID}/inventory")
                if inv_response.status_code == 200:
                    inv_data = inv_response.json()
                    print(f"✓ Updated Inventory: {inv_data.get('inventory', [])}")
                    inventory = inv_data.get('inventory', [])
                    has_iron_shavings = any('trucioli' in item.lower() or 'iron' in item.lower() or 'ferro' in item.lower() for item in inventory)
    else:
        print(f"✗ Error checking inventory: {response.text}")
        return

    time.sleep(2)

    if not has_iron_shavings:
        print("\n⚠ Still no iron shavings. Let me try giving directly via /give command...")
        # Manually add item for testing
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "player_id": PLAYER_ID,
            "display_name": DISPLAY_NAME,
            "message": "/give trucioli_ferro to Garin"
        }, timeout=60)
        print(f"Debug: {response.text[:500]}")

    # Step 4: Go to Jorin
    print("\n[STEP 4] Going to Jorin at the Tavern...")
    response = requests.post(f"{BASE_URL}/sense", json={
        "player_id": PLAYER_ID,
        "display_name": DISPLAY_NAME,
        "npcname": "Jorin",
        "area": "Tavern"
    })

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Jorin: {data.get('npc_response', 'N/A')}")
    else:
        print(f"✗ Error: {response.text}")
        return

    time.sleep(2)

    # Step 5: Give iron shavings to Jorin
    print("\n[STEP 5] Trying to give iron shavings to Jorin...")

    # First, let's just talk about having them
    response = requests.post(f"{BASE_URL}/api/chat", json={
        "player_id": PLAYER_ID,
        "display_name": DISPLAY_NAME,
        "message": "Hello Jorin! I brought you the trucioli di ferro from Garin."
    }, timeout=60)

    if response.status_code == 200:
        data = response.json()
        npc_response = data.get('npc_response', '')
        system_messages = data.get('system_messages', [])

        print(f"\n✓ Jorin says:")
        print(f"{npc_response}")

        if system_messages:
            print(f"\n[System Messages]:")
            for msg in system_messages:
                print(f"  {msg}")

        # Check for notecard
        if '[notecard=' in str(system_messages):
            print("\n✓ NOTECARD GENERATED!")

        # Check SL commands
        sl_commands = data.get('sl_commands', '')
        if sl_commands:
            print(f"\n[SL Commands] {sl_commands[:200]}...")

        print(f"\n[LLM Stats] Model: {data.get('llm_stats', {}).get('dialogue', {}).get('model', 'N/A')}")
        print(f"  Time: {data.get('llm_stats', {}).get('dialogue', {}).get('last_call_time_ms', 0)}ms")
        print(f"  Tokens/sec: {data.get('llm_stats', {}).get('dialogue', {}).get('tokens_per_sec', 0):.1f}")
    else:
        print(f"✗ Error: {response.text}")
        return

    time.sleep(2)

    # Step 6: Check final inventory
    print("\n[STEP 6] Checking final inventory...")
    response = requests.get(f"{BASE_URL}/api/player/{PLAYER_ID}/inventory")

    if response.status_code == 200:
        data = response.json()
        inventory = data.get('inventory', [])
        credits = data.get('credits', 0)
        print(f"✓ Final Inventory: {inventory}")
        print(f"✓ Credits: {credits}")

        has_bowl = any('ciotola' in item.lower() or 'bowl' in item.lower() for item in inventory)
        if has_bowl:
            print("\n🎉 SUCCESS! Received the sacred offering bowl!")
        else:
            print("\n⚠ Bowl not found in inventory yet")

    print("\n" + "="*80)
    print("QUEST TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_jorin_quest()
