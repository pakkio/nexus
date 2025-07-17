#!/usr/bin/env python3
"""
Test script for Nexus Flask API endpoints.
"""

import requests
import json
import time
import sys

# API base URL
BASE_URL = "http://localhost:5000"

def test_health():
    """Test health check endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_player_session(player_id="test_player"):
    """Test player session creation and management."""
    print(f"Testing player session for {player_id}...")
    
    # Create session
    response = requests.post(f"{BASE_URL}/api/player/{player_id}/session")
    print(f"Create session - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Session created: {data.get('session_created')}")
        print(f"Initial state: {data.get('initial_state', {}).get('system_messages', [])}")
    else:
        print(f"Error: {response.text}")
    print()

def test_game_data():
    """Test game data endpoints."""
    print("Testing game data endpoints...")
    
    # Test storyboard
    response = requests.get(f"{BASE_URL}/api/game/storyboard")
    print(f"Storyboard - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Storyboard description: {data.get('description', '')[:100]}...")
    
    # Test areas
    response = requests.get(f"{BASE_URL}/api/game/areas")
    print(f"Areas - Status: {response.status_code}")
    if response.status_code == 200:
        areas = response.json().get('areas', [])
        print(f"Available areas: {len(areas)}")
    
    # Test NPCs
    response = requests.get(f"{BASE_URL}/api/game/npcs")
    print(f"NPCs - Status: {response.status_code}")
    if response.status_code == 200:
        npcs = response.json().get('npcs', [])
        print(f"Available NPCs: {len(npcs)}")
    print()

def test_player_input(player_id="test_player"):
    """Test player input processing."""
    print(f"Testing player input for {player_id}...")
    
    # Test help command
    response = requests.post(f"{BASE_URL}/api/player/{player_id}/input", 
                           json={"input": "/help"})
    print(f"Help command - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"System messages: {data.get('system_messages', [])}")
    
    # Test whereami command
    response = requests.post(f"{BASE_URL}/api/player/{player_id}/input", 
                           json={"input": "/whereami"})
    print(f"Whereami command - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Current area: {data.get('current_area')}")
        print(f"System messages: {data.get('system_messages', [])}")
    print()

def test_chat(player_id="test_player"):
    """Test chat functionality."""
    print(f"Testing chat for {player_id}...")
    
    # Test chat message
    response = requests.post(f"{BASE_URL}/api/chat/{player_id}", 
                           json={"message": "Hello!"})
    print(f"Chat - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"NPC response: {data.get('npc_response', '')}")
        print(f"Current NPC: {data.get('current_npc')}")
        print(f"System messages: {data.get('system_messages', [])}")
    print()

def test_player_data(player_id="test_player"):
    """Test player data endpoints."""
    print(f"Testing player data for {player_id}...")
    
    # Test profile
    response = requests.get(f"{BASE_URL}/api/player/{player_id}/profile")
    print(f"Profile - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Profile data: {list(data.get('profile', {}).keys())}")
    
    # Test inventory
    response = requests.get(f"{BASE_URL}/api/player/{player_id}/inventory")
    print(f"Inventory - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Inventory: {data.get('inventory', [])}")
        print(f"Credits: {data.get('credits', 0)}")
    
    # Test state
    response = requests.get(f"{BASE_URL}/api/player/{player_id}/state")
    print(f"State - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Current area: {data.get('current_area')}")
        print(f"Current NPC: {data.get('current_npc_name')}")
    print()

def test_commands():
    """Test commands endpoint."""
    print("Testing commands endpoint...")
    
    response = requests.get(f"{BASE_URL}/api/commands")
    print(f"Commands - Status: {response.status_code}")
    if response.status_code == 200:
        commands = response.json().get('commands', {})
        print(f"Command categories: {list(commands.keys())}")
        for category, cmd_list in commands.items():
            print(f"  {category}: {len(cmd_list)} commands")
    print()

def run_all_tests():
    """Run all API tests."""
    print("=== Nexus Flask API Test Suite ===\n")
    
    try:
        test_health()
        test_player_session()
        test_game_data()
        test_player_input()
        test_chat()
        test_player_data()
        test_commands()
        
        print("=== All tests completed ===")
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API server.")
        print("Make sure the Flask app is running on http://localhost:5000")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()