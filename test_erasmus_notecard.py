#!/usr/bin/env python3
"""
Test: Erasmus gives an antefatto (story context) notecard
Verifies the notecard feature works with the 8KB context system
"""

import requests
import json
import uuid
import time

API_BASE = "http://localhost:5000"
player_id = str(uuid.uuid4())
display_name = "NotecardTester"

print("="*80)
print("🎭 TEST: Erasmus Antefatto Notecard")
print("="*80)
print(f"\n👤 Player: {display_name}")
print(f"🏛️  NPC: Erasmus (Liminal Void)")
print(f"📝 Request: Antefatto/Story Context Notecard\n")

# Question that should prompt Erasmus to give a notecard with antefatto
question = "Erasmus, mi dai un documento con tutta la storia e il contesto di Eldoria? Mi servirebbe per capire meglio il mondo."

print(f"{'─'*80}")
print(f"Question to Erasmus:")
print(f"{'─'*80}")
print(f"\n👤 Player (Italian):\n{question}\n")

response = requests.post(
    f"{API_BASE}/api/chat",
    json={
        "player_id": player_id,
        "display_name": display_name,
        "npc_name": "Erasmus",
        "area": "Liminal Void",
        "message": question
    },
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    npc_response = data.get('npc_response', 'No response')
    
    print(f"{'─'*80}")
    print(f"Response from Erasmus:")
    print(f"{'─'*80}\n")
    print(f"🎭 Erasmus (Italian):\n")
    print(npc_response)
    
    # Check for notecard command in response
    print(f"\n{'─'*80}")
    print(f"Analysis:")
    print(f"{'─'*80}\n")
    
    if "[notecard=" in npc_response:
        print("✅ NOTECARD COMMAND DETECTED")
        
        # Extract notecard command
        start = npc_response.find("[notecard=")
        end = npc_response.find("]", start) + 1
        notecard_cmd = npc_response[start:end]
        print(f"\n📋 Notecard Command:\n{notecard_cmd[:150]}...\n")
        
        # Parse the command
        notecard_content_start = notecard_cmd.find("|") + 1
        notecard_content = notecard_cmd[notecard_content_start:-1]
        print(f"📊 Notecard Content Length: {len(notecard_content)} chars")
        print(f"📊 Notecard Content (first 300 chars):\n{notecard_content[:300]}...\n")
    else:
        print("⚠️  No notecard command in response")
        print("    (Erasmus may have chosen to respond differently)")
    
    # Show stats
    stats = data.get('llm_stats', {})
    dialogue_time = stats.get('dialogue', {}).get('last_call_time_ms', 0)
    print(f"⏱️  Response time: {dialogue_time}ms")
    
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Response: {response.text}")

print(f"\n{'='*80}")
print(f"✅ Test complete!")
print(f"{'='*80}\n")
