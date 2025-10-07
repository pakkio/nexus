import requests
import time

API_URL = "http://localhost:5000/api/chat"
SENSE_URL = "http://localhost:5000/sense"
LEAVE_URL = "http://localhost:5000/leave"
PLAYER_NAME = "TestPlayerLSL"
NPC_NAME = "Erasmus"
AREA = "Liminal Void"

def lsl_touch(player_name, npc_name, area):
    payload = {"name": player_name, "npcname": npc_name, "area": area}
    try:
        response = requests.post(SENSE_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"\n[LSL TOUCH] {player_name} touches {npc_name} in {area}")
        print(f"NPC: {data.get('npc_response', '[No response]')}")
        return data
    except Exception as e:
        print(f"Error in LSL touch: {e}")
        return None

def lsl_leave(player_name):
    payload = {"name": player_name}
    try:
        response = requests.post(LEAVE_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"\n[LSL LEAVE] {player_name} leaves")
        print(f"System: {data.get('message', '[No message]')}")
        return data
    except Exception as e:
        print(f"Error in LSL leave: {e}")
        return None

def chat_turn(player_name, npc_name, area, message, turn):
    payload = {
        "player_name": player_name,
        "npc_name": npc_name,
        "area": area,
        "message": message
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"\nTurn {turn}:")
        print(f"Player: {message}")
        print(f"{npc_name}: {data.get('npc_response', '[No response]')}")
        if data.get('system_messages'):
            print(f"System: {data['system_messages']}")
        return data
    except Exception as e:
        print(f"Error in chat turn {turn}: {e}")
        return None

def main():
    # 1. First touch (LSL)
    lsl_touch(PLAYER_NAME, NPC_NAME, AREA)
    time.sleep(1)

# 2. Three-turn dialog
    dialog = [
        "Salve Erasmus. Cosa significa davvero l'oblio per te?",
        "Perché non temi la trasformazione che l'oblio porta?",
        "Cosa succede a chi accoglie il cambiamento invece di opporvisi?"
    ]
    for i, msg in enumerate(dialog, 1):
        chat_turn(PLAYER_NAME, NPC_NAME, AREA, msg, i)
        time.sleep(1)


    # 3. Leave (LSL)
    lsl_leave(PLAYER_NAME)
    time.sleep(1)

    # 4. Second touch (LSL)
    lsl_touch(PLAYER_NAME, NPC_NAME, AREA)
    time.sleep(1)

    # 5. Ask memory/coherence question
    memory_check = "Ti ricordi la nostra ultima conversazione?"
    chat_turn(PLAYER_NAME, NPC_NAME, AREA, memory_check, "Memory Check")

if __name__ == "__main__":
    main()
