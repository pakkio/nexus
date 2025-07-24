#!/usr/bin/env python3
"""
Test script for multi-user chat functionality with player_name in request body.
"""

import requests
import json
import time

def test_multiuser_chat():
    """Test multi-user functionality with different player names."""
    base_url = "http://localhost:5000"
    
    # Different players with their own sessions
    players = [
        {"name": "Alice", "npc": "Mara", "message": "Hello Mara! Tell me about your herbs."},
        {"name": "Bob", "npc": "Garin", "message": "Hi Garin! What's happening in the village?"},
        {"name": "Carol", "npc": "Lyra", "message": "Greetings Lyra, I seek wisdom."},
        {"name": "Dave", "npc": "Elira", "message": "Hello forest guardian, what do you protect?"}
    ]
    
    print("Testing Multi-User Chat Functionality")
    print("=" * 50)
    
    # Test each player chatting with different NPCs
    for i, player_data in enumerate(players, 1):
        print(f"\nTest {i}: {player_data['name']} talking to {player_data['npc']}")
        
        request_data = {
            "player_name": player_data["name"],
            "message": player_data["message"],
            "npc_name": player_data["npc"]
        }
        
        print(f"Request: {json.dumps(request_data, indent=2)}")
        
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json=request_data,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Player: {result.get('player_name')}")
                print(f"Current NPC: {result.get('current_npc')}")
                print(f"Current Area: {result.get('current_area')}")
                print(f"NPC Response: {result.get('npc_response', 'No response')[:100]}...")
            else:
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to server. Make sure it's running on port 5000")
            print("Start server with: python app.py")
            break
        except Exception as e:
            print(f"ERROR: {str(e)}")
        
        print("-" * 30)
        time.sleep(1)  # Small delay between requests
    
    # Test same player with different NPCs
    print("\nTesting Same Player with Different NPCs")
    print("=" * 50)
    
    alice_conversations = [
        {"npc": "Mara", "message": "How are your herbs growing?"},
        {"npc": "Theron", "message": "What news from the city?"},
        {"npc": "Boros", "message": "Tell me about the mountains."}
    ]
    
    for i, conv in enumerate(alice_conversations, 1):
        print(f"\nAlice conversation {i} with {conv['npc']}")
        
        request_data = {
            "player_name": "Alice",
            "message": conv["message"],
            "npc_name": conv["npc"]
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Successfully switched to {result.get('current_npc')} in {result.get('current_area')}")
            else:
                print(f"✗ Error: {response.text}")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
            break
        
        time.sleep(1)
    
    print("\nMulti-user testing complete!")

if __name__ == "__main__":
    test_multiuser_chat()