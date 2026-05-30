#!/usr/bin/env python3
"""
Analyze Flash 3 performance with Jorin's complex character
Focus on philosophical depth, identity crisis handling, and lore integration
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
PLAYER_ID = "Flash3JorinAnalysis"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")

def chat(message, show_full=False):
    """Send a chat message and return formatted response"""
    response = requests.post(f"{BASE_URL}/api/chat", json={
        "player_id": PLAYER_ID,
        "display_name": "Philosopher",
        "message": message
    }, timeout=60)

    if response.status_code != 200:
        print(f"✗ Error: {response.text}")
        return None

    data = response.json()
    npc_response = data.get('npc_response', '')
    llm_stats = data.get('llm_stats', {}).get('dialogue', {})

    print(f"[Q] {message}")
    print(f"\n[Jorin] {npc_response}\n")

    if llm_stats:
        print(f"[Stats] Model: {llm_stats.get('model', 'N/A')} | "
              f"Time: {llm_stats.get('last_call_time_ms', 0)}ms | "
              f"Tokens/sec: {llm_stats.get('tokens_per_sec', 0):.1f}")

    if show_full:
        print(f"\n[Full Response Data]")
        print(json.dumps(data, indent=2)[:1000])

    return data

# Initialize
print_section("FLASH 3 ANALYSIS: JORIN'S CHARACTER DEPTH")

print("Initializing conversation with Jorin at the Tavern...")
response = requests.post(f"{BASE_URL}/sense", json={
    "player_id": PLAYER_ID,
    "display_name": "Philosopher",
    "npcname": "Jorin",
    "area": "Tavern"
})

if response.status_code == 200:
    print(f"✓ {response.json().get('npc_response', '')}\n")
else:
    print(f"✗ Failed to initialize")
    exit(1)

time.sleep(2)

# Test 1: Dream collection (core personality)
print_section("TEST 1: Core Personality - Dream Collection")
chat("What strange dreams have travelers been sharing with you lately?")
time.sleep(3)

# Test 2: Identity crisis (complex philosophical theme)
print_section("TEST 2: Identity Crisis - Scriptorium Visions")
chat("You seem troubled, Jorin. Do you ever feel like you've lived other lives?")
time.sleep(3)

# Test 3: Philosophical depth (Tabula Rasa reference)
print_section("TEST 3: Philosophical Depth - Tabula Rasa")
chat("What do you know about the Tabula Rasa? That blank slate concept fascinates me.")
time.sleep(3)

# Test 4: Community values test
print_section("TEST 4: Community Values")
chat("I want to help the village community. What matters most to you, Jorin?")
time.sleep(3)

# Test 5: Lore integration (Iperurani / Mito di Er)
print_section("TEST 5: Lore Integration - Iperurani")
chat("Tell me about the Iperurani and the Mito di Er. These names seem to haunt you.")
time.sleep(3)

# Test 6: Quest hint (without triggering /give)
print_section("TEST 6: Quest Information")
chat("Is there anything special I could bring you? Something from the village perhaps?")
time.sleep(3)

# Summary
print_section("ANALYSIS SUMMARY")
print("""
FLASH 3 PERFORMANCE WITH JORIN - KEY EVALUATION POINTS:

1. **Character Consistency**: Did Flash 3 maintain Jorin's humble, uncertain personality?
2. **Identity Crisis**: Did it weave in scriptorium visions and memory doubts naturally?
3. **Philosophical Depth**: Did it explore Tabula Rasa, Iperurani, Mito di Er with nuance?
4. **Lore Integration**: Did it connect Jorin to the broader Nexus world (Garin, Veil, etc.)?
5. **Community Values**: Did it emphasize community service organically?
6. **Quest Mechanics**: Did it hint at the trucioli_ferro quest without breaking immersion?

Observations from test run will be documented in analysis report.
""")

print("\n✓ Test sequence complete")
print(f"Player ID: {PLAYER_ID}")
print(f"Check conversation history: GET /api/player/{PLAYER_ID}/conversation")
