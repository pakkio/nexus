#!/usr/bin/env python3
import requests
import json

# Test con richiesta specifica per la mappa
response = requests.post(
    'http://localhost:5000/api/chat',
    json={
        'player_id': 'TestMappa',
        'npc_name': 'elira',
        'area': 'Forest',
        'message': 'mi daresti la mappa del viaggio del cercastorie?'
    }
)

data = response.json()
npc_response = data.get('npc_response', '')
sl_commands = data.get('sl_commands', '')

print("=== RISPOSTA NPC ===")
print(f"Lunghezza: {len(npc_response)} caratteri")
print(npc_response[:500])
print("\n...\n")

print("\n=== SL COMMANDS ===")
if 'notecard=' in sl_commands:
    idx = sl_commands.find('notecard=')
    end_idx = sl_commands.find(']', idx)

    if end_idx != -1:
        notecard_full = sl_commands[idx:end_idx+1]
        print(f"✓ Notecard COMPLETO")
        print(f"Lunghezza: {len(notecard_full)} caratteri")

        # Estrai contenuto
        pipe_idx = notecard_full.find('|')
        if pipe_idx != -1:
            content = notecard_full[pipe_idx+1:-1]  # Rimuovi ] finale
            print(f"Contenuto notecard ({len(content)} char):")
            print(content)
    else:
        print(f"✗ Notecard TRONCATO - no ] finale")
        print(f"Inizio: {sl_commands[idx:idx+200]}")
else:
    print("Nessun notecard trovato")
    print(f"sl_commands: {sl_commands}")
