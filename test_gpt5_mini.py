#!/usr/bin/env python3
"""
Test script to evaluate GPT-4o-mini's adherence to NPC prompts across multiple turns and NPCs.
Compares behavior with previous Gemini 2.5 Flash model.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"
TEST_PLAYER = "TestAvatarGPT5"

def reset_session():
    """Reset the test session"""
    response = requests.post(f"{BASE_URL}/reset", json={"key": "1234"})
    print(f"[RESET] Status: {response.status_code}")
    return response.json() if response.status_code == 200 else None

def send_command(player_name, command, context="Testing GPT-5-mini NPC adherence"):
    """Send a command to the game server"""
    headers = {
        "X-SecondLife-Shard": "Production",
        "X-SecondLife-Object-Name": "Nexus Terminal",
        "X-SecondLife-Object-Key": "test-uuid-12345",
        "X-SecondLife-Region": "TestRegion (256, 256)",
        "X-SecondLife-Local-Position": "(128.0, 128.0, 25.0)",
        "X-SecondLife-Local-Velocity": "(0.0, 0.0, 0.0)",
        "X-SecondLife-Local-Rotation": "(0.0, 0.0, 0.0, 1.0)",
        "X-SecondLife-Owner-Name": player_name,
        "X-SecondLife-Owner-Key": f"test-owner-{player_name}"
    }

    payload = {
        "player_id": player_name,
        "display_name": player_name,
        "message": command,
        "context": context
    }

    print(f"\n{'='*80}")
    print(f"[COMMAND] {player_name}: {command}")
    print(f"{'='*80}")

    response = requests.post(f"{BASE_URL}/api/chat", json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"\n[RESPONSE]")
        print(result.get('response', 'No response'))

        # Check for SL commands in response
        if '[' in result.get('response', ''):
            print(f"\n[SL COMMANDS DETECTED]")
            import re
            sl_commands = re.findall(r'\[([^\]]+)\]', result.get('response', ''))
            for cmd in sl_commands:
                print(f"  - {cmd}")

        return result
    else:
        print(f"[ERROR] Status: {response.status_code}")
        print(response.text)
        return None

def test_syra_trading_mechanics():
    """Test Syra's trading mechanics and quest adherence"""
    print("\n" + "="*80)
    print("TEST 1: SYRA - Trading Mechanics & Quest Adherence")
    print("="*80)

    # Turn 1: Initial greeting
    send_command(TEST_PLAYER, "/talk syra", "Initial contact with Syra")
    time.sleep(2)

    # Turn 2: Ask about trade without items
    send_command(TEST_PLAYER, "I'd like to trade with you", "Testing rejection without items")
    time.sleep(2)

    # Turn 3: Try to give wrong item
    send_command(TEST_PLAYER, "/give ancient scroll to syra", "Testing wrong item rejection")
    time.sleep(2)

    # Turn 4: Give correct items
    send_command(TEST_PLAYER, "/give veil fragment to syra", "Giving first required item")
    time.sleep(2)

    send_command(TEST_PLAYER, "/give ancient scroll to syra", "Giving second required item")
    time.sleep(2)

    # Turn 5: Complete trade
    send_command(TEST_PLAYER, "I've brought the items you requested", "Completing the trade")
    time.sleep(2)

def test_irenna_teleport_mechanics():
    """Test Irenna's teleport mechanics and conditional responses"""
    print("\n" + "="*80)
    print("TEST 2: IRENNA - Teleport Mechanics & Conditional Responses")
    print("="*80)

    # Turn 1: Initial greeting
    send_command(TEST_PLAYER, "/talk irenna", "Initial contact with Irenna")
    time.sleep(2)

    # Turn 2: Ask about teleportation without permission
    send_command(TEST_PLAYER, "Can you teleport me somewhere?", "Testing teleport without permission")
    time.sleep(2)

    # Turn 3: Ask about the Veil
    send_command(TEST_PLAYER, "Tell me about the Veil", "Asking about lore")
    time.sleep(2)

    # Turn 4: Request specific destination
    send_command(TEST_PLAYER, "I need to go to the Ancient Ruins", "Requesting specific location")
    time.sleep(2)

def test_merchant_economics():
    """Test merchant trading and credit system"""
    print("\n" + "="*80)
    print("TEST 3: MERCHANT - Economics & Credit System")
    print("="*80)

    # Turn 1: Greet merchant
    send_command(TEST_PLAYER, "/talk merchant", "Initial contact with merchant")
    time.sleep(2)

    # Turn 2: Ask about wares
    send_command(TEST_PLAYER, "What do you have for sale?", "Browsing inventory")
    time.sleep(2)

    # Turn 3: Try to buy without credits
    send_command(TEST_PLAYER, "I'd like to buy a health potion", "Attempting purchase without funds")
    time.sleep(2)

    # Turn 4: Give credits
    send_command(TEST_PLAYER, "/give 50 credits to merchant", "Providing payment")
    time.sleep(2)

def test_cross_npc_consistency():
    """Test consistency when switching between NPCs"""
    print("\n" + "="*80)
    print("TEST 4: CROSS-NPC CONSISTENCY - Multiple NPC Interactions")
    print("="*80)

    # Talk to multiple NPCs in sequence
    npcs = ["syra", "irenna", "erasmus"]

    for npc in npcs:
        send_command(TEST_PLAYER, f"/talk {npc}", f"Switching to {npc}")
        time.sleep(2)

        send_command(TEST_PLAYER, "What is your purpose here?", f"Asking {npc} about purpose")
        time.sleep(2)

        send_command(TEST_PLAYER, "Tell me about the Veil", f"Asking {npc} about common lore")
        time.sleep(2)

def check_sl_command_adherence():
    """Check if SL commands are properly formatted and contextual"""
    print("\n" + "="*80)
    print("TEST 5: SECOND LIFE COMMAND ADHERENCE")
    print("="*80)

    # Test emotes and animations
    send_command(TEST_PLAYER, "/talk syra", "Testing SL command generation")
    time.sleep(2)

    send_command(TEST_PLAYER, "You seem mysterious", "Provoking emotional response")
    time.sleep(2)

    send_command(TEST_PLAYER, "That's amazing!", "Provoking positive reaction")
    time.sleep(2)

def main():
    print("\n" + "="*80)
    print("GPT-4O-MINI PROMPT ADHERENCE TEST SUITE")
    print("Testing NPC behavior across multiple turns and characters")
    print("="*80)

    # Reset session
    reset_session()
    time.sleep(2)

    # Run test suite
    try:
        test_syra_trading_mechanics()
        time.sleep(3)

        test_irenna_teleport_mechanics()
        time.sleep(3)

        test_merchant_economics()
        time.sleep(3)

        test_cross_npc_consistency()
        time.sleep(3)

        check_sl_command_adherence()

    except KeyboardInterrupt:
        print("\n\n[TEST INTERRUPTED]")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print("\nEvaluation Criteria:")
    print("1. Does the NPC follow trading rules (required items, credit amounts)?")
    print("2. Does the NPC maintain character consistency across turns?")
    print("3. Are conditional responses (success/failure) handled correctly?")
    print("4. Are SL commands ([emote], [anim], [llSetText]) generated appropriately?")
    print("5. Does the NPC stay in character when switching between conversations?")
    print("6. Are quest mechanics (flags, items, progression) properly tracked?")
    print("\nCompare these results with Gemini 2.5 Flash behavior logs.")

if __name__ == "__main__":
    main()
