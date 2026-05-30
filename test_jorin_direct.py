#!/usr/bin/env python3
"""Direct test of Jorin's quest response when player has the item"""

import requests
import json

BASE_URL = "http://localhost:5000"

# First, manually add trucioli_ferro to player's inventory via database
# We'll use the reset endpoint to start fresh, then manually test

print("="*80)
print("TESTING JORIN WITH TRUCIOLI_FERRO (DIRECT APPROACH)")
print("="*80)

# Test with a player who will have the item already
player_id = "JorinQuestTest"

# Step 1: Meet Jorin
print("\n[1] Meeting Jorin...")
response = requests.post(f"{BASE_URL}/sense", json={
    "player_id": player_id,
    "display_name": "QuestHero",
    "npcname": "Jorin",
    "area": "Tavern"
})

if response.status_code == 200:
    data = response.json()
    print(f"✓ {data.get('npc_response', '')}")

# Step 2: Try to talk about having the item
print("\n[2] Mentioning iron shavings from Garin...")
response = requests.post(f"{BASE_URL}/api/chat", json={
    "player_id": player_id,
    "display_name": "QuestHero",
    "message": "Hello Jorin! I helped Garin at his forge and he gave me these iron shavings. He said you might want them?"
}, timeout=60)

if response.status_code == 200:
    data = response.json()
    npc_response = data.get('npc_response', '')

    print(f"\n✓ JORIN'S RESPONSE:")
    print(f"{npc_response}")

    # Check for GIVEN_ITEMS tag
    if '[GIVEN_ITEMS:' in str(data):
        print("\n✓ FOUND [GIVEN_ITEMS:] TAG")

    # Check for notecard
    if '[notecard=' in str(data.get('system_messages', [])):
        print("✓ NOTECARD GENERATED")
        for msg in data.get('system_messages', []):
            if '[notecard=' in msg:
                # Extract notecard preview
                notecard_start = msg.find('[notecard=')
                notecard_preview = msg[notecard_start:notecard_start+200]
                print(f"  Preview: {notecard_preview}...")

    # Show LLM stats
    llm_stats = data.get('llm_stats', {})
    dialogue_stats = llm_stats.get('dialogue', {})
    if dialogue_stats:
        print(f"\n[LLM Performance]")
        print(f"  Model: {dialogue_stats.get('model', 'N/A')}")
        print(f"  Time: {dialogue_stats.get('last_call_time_ms', 0)}ms")
        print(f"  Tokens/sec: {dialogue_stats.get('tokens_per_sec', 0):.1f}")

    # Show full system messages for debugging
    print(f"\n[System Messages]:")
    for msg in data.get('system_messages', [])[:3]:
        print(f"  {msg[:200]}...")

else:
    print(f"✗ Error: {response.text}")

# Step 3: Try explicit /give command
print("\n[3] Testing explicit /give command...")
response = requests.post(f"{BASE_URL}/api/chat", json={
    "player_id": player_id,
    "display_name": "QuestHero",
    "message": "/give trucioli_ferro to Jorin"
}, timeout=60)

if response.status_code == 200:
    data = response.json()
    print(f"Response: {data.get('npc_response', '')[:300]}...")

    # Check inventory after
    inv_response = requests.get(f"{BASE_URL}/api/player/{player_id}/inventory")
    if inv_response.status_code == 200:
        inv_data = inv_response.json()
        print(f"\nInventory after: {inv_data.get('inventory', [])}")

print("\n" + "="*80)
