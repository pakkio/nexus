import requests
import time

API_URL = "http://localhost:5000/api/chat"
SENSE_URL = "http://localhost:5000/sense"
PLAYER_NAME = "TestPlayer"
NPC_NAME = "Syra"
AREA = "Ancient Ruins"

def chat_turn(player_name, npc_name, area, message, turn):
    payload = {
        "name": player_name,
        "npcname": npc_name,
        "area": area,
        "message": message
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        print(f"\n{'='*60}")
        print(f"TURN {turn}")
        print(f"{'='*60}")
        print(f"Player: {message}")
        print(f"\n{npc_name}: {data.get('npc_response', '[No response]')}")
        if data.get('system_messages'):
            print(f"\nSystem: {data['system_messages']}")
        return data
    except Exception as e:
        print(f"\nError in chat turn {turn}: {e}")
        try:
            print(f"Response: {response.text}")
        except:
            pass
        return None

def main():
    # 5 turn conversation with Syra
    print("Testing 5-turn conversation with Syra in Ancient Ruins")
    print("="*60)

    dialog = [
        "Hello Syra! What brings you to these ancient ruins?",
        "What kind of artifact are you searching for?",
        "Do you know anything about the history of this place?",
        "Have you encountered any dangers here?",
        "Thank you for sharing your knowledge with me."
    ]

    for i, msg in enumerate(dialog, 1):
        result = chat_turn(PLAYER_NAME, NPC_NAME, AREA, msg, i)
        if not result:
            print(f"\n⚠️  Failed at turn {i}, stopping.")
            break
        time.sleep(2)

    print(f"\n{'='*60}")
    print("Conversation complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
