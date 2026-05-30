#!/usr/bin/env python3
"""Test if caching improves response speed."""

import requests
import time

BASE_URL = "http://localhost:5000"
PLAYER = "SpeedTester"

def measure_response_time(npc, area, message):
    start = time.time()
    response = requests.post(f"{BASE_URL}/api/chat", json={
        "player_id": PLAYER,
        "npc_name": npc,
        "area": area,
        "message": message
    })
    elapsed = (time.time() - start) * 1000  # Convert to ms
    
    llm_stats = response.json().get('llm_stats', {})
    dialogue_stats = llm_stats.get('dialogue', {})
    llm_time = dialogue_stats.get('last_call_time_ms', 0)
    
    return elapsed, llm_time

# Reset
requests.post(f"{BASE_URL}/reset", json={"key": "1234"})
time.sleep(1)

print("="*70)
print("  CACHE SPEED TEST - Measuring Response Times")
print("="*70)

messages = [
    "Ciao Mara, come stai?",
    "Raccontami della tua vita.",
    "Quali sono le tue erbe preferite?",
    "Hai mai visto qualcosa di strano?",
    "Grazie per il tuo tempo."
]

times = []
for i, msg in enumerate(messages, 1):
    total_time, llm_time = measure_response_time("Mara", "Village", msg)
    times.append((i, total_time, llm_time))
    
    cache_status = "CACHE CREATED" if i == 1 else "CACHE HIT ✓"
    print(f"\nMessage {i}: {cache_status}")
    print(f"  Total response time: {total_time:.0f}ms")
    print(f"  LLM processing time: {llm_time}ms")
    
    time.sleep(0.5)

print("\n" + "="*70)
print("  SPEED ANALYSIS")
print("="*70)

first_msg = times[0]
avg_cached = sum(t[2] for t in times[1:]) / len(times[1:])

print(f"\nFirst message (no cache):  {first_msg[2]}ms")
print(f"Cached messages (avg):     {avg_cached:.0f}ms")
print(f"Speedup:                   {(first_msg[2] / avg_cached):.2f}x faster")

if avg_cached < first_msg[2]:
    improvement = ((first_msg[2] - avg_cached) / first_msg[2]) * 100
    print(f"Latency reduction:         {improvement:.1f}%")
