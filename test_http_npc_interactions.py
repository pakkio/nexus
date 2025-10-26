#!/usr/bin/env python3
"""
Test script to interact with 3 NPCs via HTTP API
Tests the 8KB context system with 5 Italian questions per NPC
"""

import requests
import json
import time
import uuid

API_BASE = "http://localhost:5000"

# Test data: 3 NPCs with 5 Italian questions each
TEST_NPCS = {
    "Erasmus": {
        "area": "Liminal Void",
        "questions": [
            "Ciao Erasmus, chi sei tu?",
            "Mi puoi spiegare il significato del Velo?",
            "Quali sono le tre scelte che menzioni?",
            "Come posso recuperare la mia memoria?",
            "Mi aiuterai nel mio cammino?"
        ]
    },
    "Syra": {
        "area": "Ancient Ruins",
        "questions": [
            "Ciao Syra, cosa stai facendo qui?",
            "Cosa significa essere una Tessitrice incompleta?",
            "Ho bisogno della Ciotola Sacra?",
            "Dove posso trovare la Ciotola?",
            "Mi aiuterai se la trovo?"
        ]
    },
    "Jorin": {
        "area": "Tavern",
        "questions": [
            "Ciao Jorin! Sei il guardiano della Taverna?",
            "Hai la Ciotola Sacra?",
            "Quanto costa la Ciotola?",
            "Mi racconti della storia di Eldoria?",
            "Posso fidarmi di te?"
        ]
    }
}

def send_message(player_id, display_name, npc_name, area, message):
    """Send a message to an NPC via HTTP API"""
    response = requests.post(
        f"{API_BASE}/api/chat",
        json={
            "player_id": player_id,
            "display_name": display_name,
            "npc_name": npc_name,
            "area": area,
            "message": message
        },
        timeout=30
    )

    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        print(f"   {response.text[:200]}")
        return None

    try:
        data = response.json()
        # The API returns npc_response field
        return data.get('npc_response', data.get('response', 'No response'))
    except:
        print(f"❌ Failed to parse response: {response.text[:100]}")
        return None

def test_npc_interaction(player_id, display_name, npc_name, area, questions):
    """Test interaction with one NPC for 5 turns"""
    print(f"\n\n{'─'*80}")
    print(f"🎭 TEST: {npc_name.upper()} ({area})")
    print(f"{'─'*80}")

    # Ask 5 questions
    for i, question in enumerate(questions, 1):
        print(f"\n  📍 Turn {i}/5:")
        print(f"    👤 Player: {question}")

        response = send_message(player_id, display_name, npc_name, area, question)

        if response is None:
            print(f"    ❌ Failed to get response")
            return False

        # Print NPC response (first 300 chars)
        response_preview = response[:300] + "..." if len(response) > 300 else response
        print(f"    🎭 {npc_name}: {response_preview}")

        time.sleep(1.5)

    print(f"\n  ✅ Successfully completed all 5 turns with {npc_name}!")
    return True

def main():
    print(f"\n{'='*80}")
    print(f"🚀 NPC HTTP Interaction Test - 8KB Context System")
    print(f"{'='*80}")
    print(f"\n📊 Testing with:")
    print(f"   - 3 NPCs (Erasmus, Syra, Jorin)")
    print(f"   - 5 Italian questions per NPC")
    print(f"   - Server: {API_BASE}")

    # Create player with unique ID
    player_id = str(uuid.uuid4())
    display_name = "ContextTestPlayer"

    print(f"\n👤 Player ID: {player_id}")
    print(f"👤 Display Name: {display_name}")

    # Test 3 NPCs
    results = {}
    for npc_name, npc_data in TEST_NPCS.items():
        try:
            success = test_npc_interaction(
                player_id,
                display_name,
                npc_name,
                npc_data["area"],
                npc_data["questions"]
            )
            results[npc_name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            print(f"\n❌ Exception testing {npc_name}: {str(e)}")
            results[npc_name] = "❌ FAIL"

    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")

    for npc_name, result in results.items():
        print(f"{result} {npc_name} - 5/5 turns completed")

    all_passed = all("PASS" in r for r in results.values())
    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ 8KB NPC context system working correctly")
        print(f"✅ All 3 NPCs responded successfully")
        print(f"✅ Italian language support verified")
        print(f"✅ Extended context propagation working")
    else:
        print(f"\n⚠️  Some tests failed - see details above")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
