#!/usr/bin/env python3
import requests
import json

response = requests.post(
    'http://localhost:5000/api/chat',
    json={'player_id': 'TestTrunc', 'npc_name': 'elira', 'area': 'Forest', 'message': 'mi daresti una guida?'}
)

data = response.json()
sl_commands = data.get('sl_commands', '')

print("=== ANALISI NOTECARD DAL SERVER ===\n")

if 'notecard=' in sl_commands:
    start = sl_commands.find('notecard=')
    end = sl_commands.find(']', start)

    if end != -1:
        full_notecard = sl_commands[start:end]
        print(f"✓ Notecard COMPLETO dal server")
        print(f"  Lunghezza: {len(full_notecard)} caratteri")
        print(f"\nInizio (primi 200 char):")
        print(full_notecard[:200])
        print(f"\n... [contenuto medio omesso] ...\n")
        print(f"Fine (ultimi 200 char):")
        print(full_notecard[-200:])

        # Conta le righe
        content_start = full_notecard.find('|')
        if content_start != -1:
            content = full_notecard[content_start+1:]
            lines = content.count('\n')
            print(f"\nRighe nel contenuto: {lines}")
    else:
        print("✗ ERRORE: notecard TRONCATO - manca ] finale")
        print(f"  Trovato: {sl_commands[start:start+300]}...")
else:
    print("✗ Nessun notecard trovato in sl_commands")
    print(f"  sl_commands: {sl_commands[:500]}")
