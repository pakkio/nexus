#!/usr/bin/env python3
import requests
import json

# Simula la richiesta che hai fatto in Second Life
response = requests.post(
    'http://localhost:5000/api/chat',
    json={
        'player_id': 'LorenzaTest',
        'npc_name': 'elira',
        'area': 'Forest',
        'message': 'notecard'
    }
)

data = response.json()
npc_response = data.get('npc_response', '')
sl_commands = data.get('sl_commands', '')

print("=== RISPOSTA NPC (dialogo pulito) ===")
print(npc_response)
print(f"\nLunghezza dialogo: {len(npc_response)} caratteri\n")

print("\n" + "="*80)
print("=== SL_COMMANDS (comandi per LSL) ===")
print(f"Lunghezza totale: {len(sl_commands)} caratteri")
print(sl_commands)

print("\n" + "="*80)
print("=== ANALISI NOTECARD ===")
if 'notecard=' in sl_commands:
    idx = sl_commands.find('notecard=')

    # Cerca la fine del notecard (carattere ])
    end_idx = sl_commands.find(']', idx)

    if end_idx != -1:
        notecard_full = sl_commands[idx:end_idx+1]
        print(f"✓ Notecard COMPLETO con ] finale")
        print(f"  Lunghezza: {len(notecard_full)} caratteri")

        # Estrai nome e contenuto
        pipe_idx = notecard_full.find('|')
        if pipe_idx != -1:
            name = notecard_full[9:pipe_idx]  # Salta "notecard="
            content = notecard_full[pipe_idx+1:-1]  # Rimuovi ] finale

            print(f"  Nome: {name}")
            print(f"  Contenuto ({len(content)} caratteri):")
            print()
            print(content)
    else:
        print(f"✗ NOTECARD TRONCATO - manca ] finale!")
        print(f"  Trovato 'notecard=' a posizione {idx}")
        print(f"  Lunghezza sl_commands: {len(sl_commands)}")
        print(f"\n  Ultimi 200 caratteri di sl_commands:")
        print(f"  ...{sl_commands[-200:]}")

        # Mostra cosa c'è dopo notecard=
        remaining = sl_commands[idx:]
        print(f"\n  Contenuto da 'notecard=' in poi ({len(remaining)} char):")
        print(remaining)
else:
    print("✗ Nessun notecard trovato in sl_commands")
