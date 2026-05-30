#!/usr/bin/env python3
"""Test sacred bowl quest with cache monitoring."""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
PLAYER = "QuestCacheTester"

def api_call(endpoint, data):
    response = requests.post(f"{BASE_URL}/{endpoint}", json=data)
    return response.json()

print("="*70)
print("  SACRED BOWL QUEST - CACHE ANALYSIS")
print("="*70)

# Reset
print("\nResetting game...")
api_call("reset", {"key": "1234"})

# Quest steps
steps = [
    ("Mara", "Village", "Ciao Mara, vorrei comprare una pozione di guarigione."),
    ("Elira", "Forest", "Ciao Elira, ecco la pozione di guarigione per te."),
    ("Boros", "Mountain", "Ciao Boros, ho il Seme della Foresta da Elira."),
    ("Garin", "Village", "Ciao Garin, ho il Minerale di Ferro Antico."),
    ("Jorin", "Tavern", "Ciao Jorin, ho i Trucioli di Ferro da Garin."),
    ("Syra", "Ancient Ruins", "Ciao Syra, ho la Ciotola dell'Offerta Sacra.")
]

for i, (npc, area, msg) in enumerate(steps, 1):
    print(f"\n{'='*70}")
    print(f"  STEP {i}/6: {npc} ({area})")
    print(f"{'='*70}")
    print(f"Message: {msg}")
    
    response = api_call("api/chat", {
        "player_id": PLAYER,
        "npc_name": npc,
        "area": area,
        "message": msg
    })
    
    npc_response = response.get('npc_response', 'ERROR')
    print(f"\n{npc}: {npc_response[:200]}...")
    
    # Small delay
    time.sleep(1)

print("\n" + "="*70)
print("  QUEST COMPLETE - Check logs for cache statistics")
print("="*70)
