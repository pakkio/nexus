#!/usr/bin/env python3
"""
Test script for the modified /api/chat endpoint that accepts npc_name parameter.
"""

import requests
import json

def test_chat_endpoint():
    """Test the modified chat endpoint with different scenarios."""
    base_url = "http://localhost:5000"
    player_id = "test_player"
    
    test_cases = [
        {
            "name": "Chat with specific NPC",
            "data": {
                "message": "Hello there!",
                "npc_name": "Eldara"
            }
        },
        {
            "name": "Chat without NPC name (current NPC)",
            "data": {
                "message": "Tell me about this place"
            }
        },
        {
            "name": "Chat with different NPC",
            "data": {
                "message": "What quests do you have?",
                "npc_name": "Marcus"
            }
        },
        {
            "name": "Chat with non-existent NPC",
            "data": {
                "message": "Hello",
                "npc_name": "NonExistentNPC"
            }
        }
    ]
    
    print("Testing modified /api/chat endpoint...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Request: {json.dumps(test_case['data'], indent=2)}")
        
        try:
            response = requests.post(
                f"{base_url}/api/chat/{player_id}",
                json=test_case['data'],
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to server. Make sure it's running on port 5000")
            print("Start server with: python app.py")
            break
        except Exception as e:
            print(f"ERROR: {str(e)}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_chat_endpoint()