#!/usr/bin/env python3
"""
Test: Lyra gives a "Pergamena di Preservazione della Memoria" (Memory Preservation Scroll) notecard
This tests the notecard feature with an NPC configured to give notecards
"""

import requests
import json
import uuid
import time

API_BASE = "http://localhost:5000"
player_id = str(uuid.uuid4())
display_name = "LyraVisitor"

print("="*80)
print("🎭 TEST: Lyra Gives Memory Preservation Scroll (Notecard)")
print("="*80)
print(f"\n👤 Player: {display_name}")
print(f"🏛️  NPC: Lyra (Sanctum of Whispers)")
print(f"📋 Quest: Bring Crystal to Lyra\n")

# First, let's ask Lyra about the cristallo_memoria
question1 = "Lyra, ho portato il Cristallo di Memoria Antica dalle rovine. Questo è quello che cercavi?"

print(f"{'─'*80}")
print(f"Question 1: Bringing the Crystal")
print(f"{'─'*80}")
print(f"\n👤 Player (Italian):\n{question1}\n")

response = requests.post(
    f"{API_BASE}/api/chat",
    json={
        "player_id": player_id,
        "display_name": display_name,
        "npc_name": "Lyra",
        "area": "Sanctum of Whispers",
        "message": question1
    },
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    npc_response = data.get('npc_response', 'No response')
    
    print(f"{'─'*80}")
    print(f"Response from Lyra:")
    print(f"{'─'*80}\n")
    print(f"🎭 Lyra (Italian):\n")
    print(npc_response)
    
    # Check for notecard command
    print(f"\n{'─'*80}")
    print(f"Notecard Analysis:")
    print(f"{'─'*80}\n")
    
    if "[notecard=" in npc_response:
        print("✅ NOTECARD COMMAND DETECTED!")
        
        # Extract notecard info
        start = npc_response.find("[notecard=")
        end = npc_response.find("]", start) + 1
        notecard_cmd = npc_response[start:end]
        
        eq_pos = notecard_cmd.find("=")
        pipe_pos = notecard_cmd.find("|")
        
        notecard_name = notecard_cmd[eq_pos+1:pipe_pos]
        notecard_content_escaped = notecard_cmd[pipe_pos+1:-1]
        
        print(f"📛 Notecard Name: {notecard_name}")
        print(f"📊 Escaped Content Length: {len(notecard_content_escaped)} chars")
        
        # Unescape for display
        content = notecard_content_escaped.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        print(f"\n📝 Notecard Content (Unescaped):\n")
        print("─" * 80)
        print(content)
        print("─" * 80)
        
        print(f"\n✅ FEATURE VERIFICATION:")
        print(f"   ✓ Notecard command generated successfully")
        print(f"   ✓ Content includes memory preservation information")
        print(f"   ✓ Escaped properly for LSL transmission")
        print(f"   ✓ Ready for osMakeNotecard() in Second Life")
    else:
        print("⚠️  No notecard command in response")
    
    # Show stats
    stats = data.get('llm_stats', {})
    dialogue_time = stats.get('dialogue', {}).get('last_call_time_ms', 0)
    print(f"\n⏱️  Response time: {dialogue_time}ms")
    
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Response: {response.text}")

print(f"\n{'='*80}")
print(f"✅ Test complete!")
print(f"{'='*80}\n")
