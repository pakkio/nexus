#!/usr/bin/env python3
"""
Compare Gemini Flash 3 vs 2.5 Flash performance in Nexus RPG
Tests dialogue quality, response time, and reasoning capabilities
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Simple Greeting",
        "player_id": "FlashTest1",
        "npc": "Elira",
        "area": "Forest",
        "messages": [
            "Ciao Elira, come stai?",
        ]
    },
    {
        "name": "Complex Reasoning",
        "player_id": "FlashTest2",
        "npc": "Elira",
        "area": "Forest",
        "messages": [
            "Elira, ho bisogno di capire la connessione tra i Tessitori e il Velo. Puoi spiegarmi la filosofia profonda dietro questa relazione?",
        ]
    },
    {
        "name": "Multi-turn Conversation",
        "player_id": "FlashTest3",
        "npc": "Boros",
        "area": "Mountain",
        "messages": [
            "Ciao Boros, cosa sai dell'equilibrio?",
            "Come posso trovare il mio equilibrio personale?",
            "Quali sono le pratiche che consigli?"
        ]
    }
]

def reset_conversation(player_id):
    """Reset conversation history for a player"""
    try:
        response = requests.delete(f"{BASE_URL}/api/player/{player_id}/conversation/reset")
        return response.status_code == 200
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return False

def test_model_with_scenario(model_name, scenario):
    """Test a specific model with a test scenario"""
    player_id = f"{scenario['player_id']}_{model_name.replace('/', '_')}"

    print(f"\n{'='*80}")
    print(f"Testing: {scenario['name']} with {model_name}")
    print(f"{'='*80}")

    # Reset conversation
    reset_conversation(player_id)

    results = {
        "model": model_name,
        "scenario": scenario['name'],
        "messages": [],
        "total_time": 0,
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "errors": []
    }

    # Initialize with /sense
    try:
        sense_start = time.time()
        sense_response = requests.post(f"{BASE_URL}/sense", json={
            "player_id": player_id,
            "display_name": "Tester",
            "npcname": scenario['npc'],
            "area": scenario['area']
        })
        sense_time = time.time() - sense_start

        if sense_response.status_code == 200:
            sense_data = sense_response.json()
            print(f"\n[SENSE] ({sense_time:.2f}s)")
            print(f"NPC: {sense_data.get('npc_response', 'N/A')}")
        else:
            results['errors'].append(f"Sense failed: {sense_response.text}")
            return results
    except Exception as e:
        results['errors'].append(f"Sense error: {str(e)}")
        return results

    # Send each message
    for i, message in enumerate(scenario['messages'], 1):
        try:
            chat_start = time.time()
            chat_response = requests.post(f"{BASE_URL}/api/chat", json={
                "player_id": player_id,
                "display_name": "Tester",
                "message": message,
                "npc_name": scenario['npc'],
                "area": scenario['area']
            }, timeout=60)
            chat_time = time.time() - chat_start

            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                npc_response = chat_data.get('npc_response', '')
                llm_stats = chat_data.get('llm_stats', {})

                # Extract stats
                dialogue_stats = llm_stats.get('dialogue', {})
                tokens_in = dialogue_stats.get('last_tokens_in', 0)
                tokens_out = dialogue_stats.get('last_tokens_out', 0)
                llm_time = dialogue_stats.get('last_call_time_ms', 0) / 1000

                results['total_time'] += chat_time
                results['total_tokens_in'] += tokens_in
                results['total_tokens_out'] += tokens_out

                message_result = {
                    "turn": i,
                    "player_message": message,
                    "npc_response": npc_response,
                    "response_time": chat_time,
                    "llm_time": llm_time,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "tokens_per_sec": dialogue_stats.get('tokens_per_sec', 0)
                }
                results['messages'].append(message_result)

                print(f"\n[Turn {i}] ({chat_time:.2f}s total, {llm_time:.2f}s LLM)")
                print(f"Player: {message}")
                print(f"NPC: {npc_response[:200]}{'...' if len(npc_response) > 200 else ''}")
                print(f"Tokens: {tokens_in} in, {tokens_out} out ({dialogue_stats.get('tokens_per_sec', 0):.1f} tok/s)")
            else:
                results['errors'].append(f"Turn {i} failed: {chat_response.text}")
                print(f"\n[ERROR Turn {i}] {chat_response.text}")
        except Exception as e:
            results['errors'].append(f"Turn {i} error: {str(e)}")
            print(f"\n[ERROR Turn {i}] {str(e)}")

    return results

def compare_models():
    """Compare Gemini Flash 3 vs 2.5 Flash"""

    models_to_test = [
        "google/gemini-2.5-flash",
        "google/gemini-3-flash-preview"
    ]

    # Note: We can't change the model dynamically via API, so we need to test with current model
    # and document which model is being used

    print("\n" + "="*80)
    print("GEMINI FLASH MODEL COMPARISON TEST")
    print("="*80)
    print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    # Get current server config
    try:
        health = requests.get(f"{BASE_URL}/health").json()
        print(f"Server Version: {health.get('version', 'Unknown')}")
        print(f"Server Time: {health.get('server_time', 'Unknown')}")
    except:
        print("Could not get server health info")

    all_results = []

    print("\n" + "="*80)
    print("IMPORTANT: This test uses the currently configured model in .env")
    print("You need to run this script twice:")
    print("1. First with OPENROUTER_DEFAULT_MODEL=google/gemini-2.5-flash")
    print("2. Then with OPENROUTER_DEFAULT_MODEL=google/gemini-3-flash-preview")
    print("="*80)

    # Check which model is currently active by making a test call
    try:
        test_response = requests.post(f"{BASE_URL}/api/chat", json={
            "player_id": "ModelCheck",
            "message": "hi",
            "npc_name": "Elira",
            "area": "Forest"
        }, timeout=30)

        if test_response.status_code == 200:
            current_model = test_response.json().get('llm_stats', {}).get('dialogue', {}).get('model', 'Unknown')
            print(f"\nCurrent Active Model: {current_model}")
        else:
            current_model = "Unknown"
    except:
        current_model = "Unknown"

    # Run all scenarios with current model
    for scenario in TEST_SCENARIOS:
        results = test_model_with_scenario(current_model, scenario)
        results['timestamp'] = datetime.now().isoformat()
        all_results.append(results)
        time.sleep(2)  # Brief pause between scenarios

    # Save results
    output_file = f"flash_comparison_results_{current_model.replace('/', '_')}_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Model Tested: {current_model}")
    print(f"Scenarios Completed: {len(all_results)}")

    for result in all_results:
        print(f"\n{result['scenario']}:")
        print(f"  Total Time: {result['total_time']:.2f}s")
        print(f"  Messages: {len(result['messages'])}")
        print(f"  Tokens In: {result['total_tokens_in']}")
        print(f"  Tokens Out: {result['total_tokens_out']}")
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")

    print(f"\nResults saved to: {output_file}")
    print("\nTo complete the comparison:")
    print(f"1. Note current model: {current_model}")
    print("2. Update .env with the other model")
    print("3. Restart the server: pkill -f app.py && python3 app.py &")
    print("4. Run this script again")
    print("5. Compare the two JSON output files")

if __name__ == "__main__":
    compare_models()
