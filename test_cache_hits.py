#!/usr/bin/env python3
"""
Test script to demonstrate prompt caching with repeated NPC conversations.
This should show cache hits on the 2nd+ messages to the same NPC.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
PLAYER = "CacheTester"

def api_call(endpoint, data):
    """Make API call and return response."""
    response = requests.post(f"{BASE_URL}/{endpoint}", json=data)
    return response.json()

def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if "response" in response:
        print(response["response"])
    else:
        print(json.dumps(response, indent=2))
    print()

# Reset game
print("Resetting game...")
reset_response = api_call("reset", {"key": "1234"})
print(f"✓ Reset: {reset_response.get('message', 'OK')}")

# Talk to Mara 5 times with different messages
# The /api/chat endpoint handles area/NPC switching automatically
messages = [
    "Hello Mara! What do you sell?",
    "Tell me about the healing potions you have.",
    "What else can you tell me about your wares?",
    "Do you know anything about the sacred bowl quest?",
    "Thank you for your help!"
]

print("\n" + "="*60)
print("  STARTING MULTI-TURN CONVERSATION WITH MARA")
print("  (Watch for cache hits in logs after message 1)")
print("="*60)

for i, message in enumerate(messages, 1):
    print(f"\n--- Message {i}/5 to Mara ---")
    print(f"Player: {message}")

    talk_response = api_call("api/chat", {
        "player_id": PLAYER,
        "npc_name": "Mara",
        "area": "Village",
        "message": message
    })

    if "error" in talk_response:
        print(f"\nERROR: {talk_response.get('error')}")
        continue

    print(f"\nMara: {talk_response.get('npc_response', 'ERROR')}")

    # Check LLM stats if available (from dialogue model)
    if "llm_stats" in talk_response:
        llm_stats = talk_response["llm_stats"]
        if "dialogue" in llm_stats:
            dialogue_stats = llm_stats["dialogue"]
            tokens_in = dialogue_stats.get("last_tokens_in", 0)
            tokens_out = dialogue_stats.get("last_tokens_out", 0)
            call_time = dialogue_stats.get("last_call_time_ms", 0)
            print(f"\n📊 LLM Stats: {tokens_in} tokens in, {tokens_out} tokens out, {call_time}ms")

            # Note: Cache stats are logged server-side in /tmp/flask_api.log
            # We'll check the logs after the test to see cache hits

    # Small delay between messages
    time.sleep(2)

print("\n" + "="*60)
print("  TEST COMPLETE - Check /tmp/game_api.log for cache stats")
print("="*60)
