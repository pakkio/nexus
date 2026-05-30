#!/usr/bin/env python3
"""
Test script simulating the exact scenarios reported by your friend.

Scenario 1: Talking with Syra who mentions Boros
Scenario 2: Talking with Meridia who mentions Lyra
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def reset_player(player_name):
    """Reset player state for clean test."""
    response = requests.post(f"{BASE_URL}/reset",
                            json={"key": "1234"},
                            headers={"X-SecondLife-Owner-Name": player_name})
    print(f"Reset player {player_name}: {response.json()}")
    time.sleep(1)

def send_message(player_name, message, area="Ancient Ruins", npc_name=None):
    """Send a message to the game system."""
    headers = {
        "X-SecondLife-Owner-Name": player_name,
        "X-SecondLife-Region": f"{area} (128, 128, 25)"
    }

    data = {"player_message": message}
    if npc_name:
        data["npc_name"] = npc_name

    print(f"\n{'='*70}")
    print(f"Player: {player_name}")
    print(f"Area: {area}")
    if npc_name:
        print(f"Talking to: {npc_name}")
    print(f"Message: {message}")
    print(f"{'='*70}")

    response = requests.post(f"{BASE_URL}/talk", json=data, headers=headers)
    result = response.json()

    if result.get("status") == "success":
        npc_response = result.get("npc_response", "")
        sl_commands = result.get("sl_commands", "")

        print(f"\nNPC Response:")
        print(f"{npc_response}")
        if sl_commands:
            print(f"\nSL Commands: {sl_commands}")

        # Check for error messages that should NOT appear
        if "not found in" in npc_response.lower():
            print(f"\n❌ ERROR: Technical error message detected in NPC response!")
            print(f"   This breaks immersion and should be dialogue instead.")
            return False
        else:
            print(f"\n✓ Good: No technical errors, NPC responded naturally")
            return True
    else:
        print(f"\n❌ API Error: {result}")
        return False

def test_scenario_1_syra_mentions_boros():
    """Test Scenario 1: Syra mentions Boros, player responds about going to see him."""
    print("\n" + "="*70)
    print("SCENARIO 1: Syra mentions Boros")
    print("="*70)

    player_name = "TestPlayer Scenario1"
    reset_player(player_name)

    # Go to Ancient Ruins where Syra is
    print("\nStep 1: Going to Ancient Ruins to meet Syra...")
    send_message(player_name, "/go Ancient Ruins", area="Tavern")
    time.sleep(2)

    # Start conversation with Syra
    print("\nStep 2: Starting conversation with Syra...")
    send_message(player_name, "/talk Syra", area="Ancient Ruins", npc_name="Syra")
    time.sleep(2)

    # Syra will likely mention Boros or the quest involving other NPCs
    # Let's ask her about her quest
    print("\nStep 3: Asking about the quest (Syra will mention other NPCs)...")
    send_message(player_name, "Parlami della tua missione", area="Ancient Ruins", npc_name="Syra")
    time.sleep(2)

    # Now the critical test: Player says they're going to see Boros
    print("\nStep 4: CRITICAL TEST - Player mentions going to see Boros...")
    print("This should be interpreted as DIALOGUE, not a /talk command")
    success = send_message(player_name, "vado da Boros", area="Ancient Ruins", npc_name="Syra")
    time.sleep(2)

    return success

def test_scenario_2_meridia_mentions_lyra():
    """Test Scenario 2: Meridia mentions Lyra, player responds about going to see her."""
    print("\n" + "="*70)
    print("SCENARIO 2: Meridia mentions Lyra")
    print("="*70)

    player_name = "TestPlayer Scenario2"
    reset_player(player_name)

    # Go to Nexus of Paths where Meridia is
    print("\nStep 1: Going to Nexus of Paths to meet Meridia...")
    send_message(player_name, "/go Nexus of Paths", area="Tavern")
    time.sleep(2)

    # Start conversation with Meridia
    print("\nStep 2: Starting conversation with Meridia...")
    send_message(player_name, "/talk Meridia", area="Nexus of Paths", npc_name="Meridia")
    time.sleep(2)

    # Meridia will mention other NPCs including Lyra
    print("\nStep 3: Asking about other weavers (Meridia will mention Lyra)...")
    send_message(player_name, "Parlami degli altri Tessitori", area="Nexus of Paths", npc_name="Meridia")
    time.sleep(2)

    # Now the critical test: Player says they're going to see Lyra
    print("\nStep 4: CRITICAL TEST - Player mentions going to see Lyra...")
    print("This should be interpreted as DIALOGUE, not a /talk command")
    success = send_message(player_name, "vado da Lyra", area="Nexus of Paths", npc_name="Meridia")
    time.sleep(2)

    return success

def test_scenario_3_additional_cases():
    """Test additional edge cases with natural language."""
    print("\n" + "="*70)
    print("SCENARIO 3: Additional Edge Cases")
    print("="*70)

    player_name = "TestPlayer Scenario3"
    reset_player(player_name)

    # Go to Ancient Ruins
    send_message(player_name, "/go Ancient Ruins", area="Tavern")
    time.sleep(2)

    # Talk to Syra
    send_message(player_name, "/talk Syra", area="Ancient Ruins", npc_name="Syra")
    time.sleep(2)

    # Test various ways of mentioning other NPCs
    test_cases = [
        ("chi è Boros?", "Asking about NPC identity"),
        ("cosa sai di Jorin?", "Asking what NPC knows about someone"),
        ("andrò da Lyra dopo", "Future plan with 'dopo'"),
        ("parlami di Theron", "Asking NPC to talk about someone"),
    ]

    all_success = True
    for message, description in test_cases:
        print(f"\n\nTesting: {description}")
        success = send_message(player_name, message, area="Ancient Ruins", npc_name="Syra")
        all_success = all_success and success
        time.sleep(2)

    return all_success

def main():
    print("\n" + "="*70)
    print("Testing Friend's Reported Dialogue Issues")
    print("="*70)
    print("\nThis test simulates the exact scenarios where NPCs mention other NPCs")
    print("and the player responds by mentioning those NPCs.")
    print("\nBEFORE FIX: System showed 'NPC not found' errors")
    print("AFTER FIX: NPCs should respond naturally to these statements")
    print("="*70)

    # Run all scenarios
    scenario1_success = test_scenario_1_syra_mentions_boros()
    time.sleep(3)

    scenario2_success = test_scenario_2_meridia_mentions_lyra()
    time.sleep(3)

    scenario3_success = test_scenario_3_additional_cases()

    # Final results
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Scenario 1 (Syra/Boros): {'✓ PASS' if scenario1_success else '✗ FAIL'}")
    print(f"Scenario 2 (Meridia/Lyra): {'✓ PASS' if scenario2_success else '✗ FAIL'}")
    print(f"Scenario 3 (Edge Cases): {'✓ PASS' if scenario3_success else '✗ FAIL'}")

    if scenario1_success and scenario2_success and scenario3_success:
        print("\n✓ ALL TESTS PASSED!")
        print("\nThe bug is fixed:")
        print("- NPCs can mention other NPCs without causing errors")
        print("- Players can naturally respond with statements like 'vado da X'")
        print("- System distinguishes between dialogue and commands")
        print("- No more technical error messages breaking immersion")
        return True
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Please review the responses above for details.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
