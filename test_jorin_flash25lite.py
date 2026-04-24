#!/usr/bin/env python3
"""Multi-turn Jorin test: TP, notecard, SL commands — Gemini 2.5 Flash Lite"""

import requests
import json
import time

BASE = "http://localhost:5000"
PLAYER = "TestPlayer_Jorin"
NAME   = "Adventurer"

def chat(msg, timeout=60):
    r = requests.post(f"{BASE}/api/chat", json={
        "player_id": PLAYER, "display_name": NAME, "message": msg
    }, timeout=timeout)
    return r.json() if r.status_code == 200 else {"error": r.text}

def sense(npc, area):
    r = requests.post(f"{BASE}/sense", json={
        "player_id": PLAYER, "display_name": NAME, "npcname": npc, "area": area
    }, timeout=60)
    return r.json() if r.status_code == 200 else {"error": r.text}

def inventory():
    r = requests.get(f"{BASE}/api/player/{PLAYER}/inventory")
    return r.json() if r.status_code == 200 else {}

def show(label, data):
    print(f"\n{'─'*70}")
    print(f"► {label}")
    print(f"{'─'*70}")
    resp = data.get("npc_response", data.get("error", ""))
    sl   = data.get("sl_commands", "")
    sys_msgs = data.get("system_messages", [])
    stats = data.get("llm_stats", {}).get("dialogue", {})

    print(f"NPC: {resp[:500]}")

    if sl:
        print(f"\nSL_COMMANDS: {sl}")
        # Check specific features
        if "teleport=" in sl or "tp=" in sl.lower():
            print("  ✓ TELEPORT found")
        else:
            print("  ✗ no teleport in sl_commands")
        if "notecard=" in sl:
            print("  ✓ NOTECARD found")
        if "anim=" in sl:
            print("  ✓ ANIMATION found")
        if "emote=" in sl or "face=" in sl:
            print("  ✓ EMOTE/FACE found")
        if "llSetText=" in sl or "llsettext=" in sl.lower():
            print("  ✓ llSetText found")
    else:
        print("\nSL_COMMANDS: (none)")

    # Check notecard in system messages too
    notecard_found = any("notecard" in str(m).lower() for m in sys_msgs)
    if sys_msgs:
        print(f"\nSYSTEM_MESSAGES: {sys_msgs}")
    if notecard_found:
        print("  ✓ NOTECARD in system_messages")

    # Also check raw npc_response for notecard tag
    if "[notecard=" in resp:
        print("  ✓ NOTECARD tag in npc_response")

    if stats:
        model = stats.get("model", "?")
        ms    = stats.get("last_call_time_ms", 0)
        tps   = stats.get("tokens_per_sec", 0)
        toks  = stats.get("total_tokens", 0)
        print(f"\nSTATS: model={model} | {ms}ms | {toks} tokens | {tps:.1f} tok/s")

# ── Reset player state and seed inventory ─────────────────────────────────────
print("="*70)
print("JORIN MULTI-TURN TEST — gemini-2.5-flash-lite")
print("Checking: TP, animations, emotes, llSetText, notecard")
print("="*70)

requests.post(f"{BASE}/reset", json={"player_id": PLAYER})
time.sleep(1)

# Seed trucioli_ferro directly via DB so the quest trade can fire
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from db_manager import DbManager
db = DbManager()
db.add_item_to_inventory(PLAYER, "Trucioli di Ferro")
print(f"Seeded inventory: Trucioli di Ferro")
time.sleep(1)

# ── Turn 1: Arrive at tavern (sense → should trigger TP in prefix) ────────────
print("\n[TURN 1] Arriving at tavern (sense)")
d = sense("Jorin", "Tavern")
show("SENSE — Jorin greets player (check TP in sl_commands)", d)
time.sleep(2)

# ── Turn 2: Ask about dreams ──────────────────────────────────────────────────
print("\n[TURN 2] Ask about dreams")
d = chat("Ciao Jorin! Ho sentito che raccogli sogni particolari. Cosa hai raccolto di recente?")
show("Ask about dream collection (check anim/emote)", d)
time.sleep(2)

# ── Turn 3: Trigger identity vision ───────────────────────────────────────────
print("\n[TURN 3] Trigger identity vision")
d = chat("Hai mai sentito parlare della Tabula Rasa o degli Iperurani?")
show("Tabula Rasa / identity vision (check emote confusione)", d)
time.sleep(2)

# ── Turn 4: Give via /give command with exact Italian name ────────────────────
print("\n[TURN 4] Give trucioli di ferro → should trigger notecard + sacred bowl")
d = chat("/give trucioli di ferro")
show("Give ferro trucioli (check NOTECARD + GIVEN_ITEMS)", d)
time.sleep(2)

# ── Turn 5: Check inventory ───────────────────────────────────────────────────
print("\n[TURN 5] Inventory check")
inv = inventory()
items   = inv.get("inventory", [])
credits = inv.get("credits", 0)
print(f"\nInventory: {items}")
print(f"Credits:   {credits}")
has_bowl = any("ciotola" in i.lower() or "bowl" in i.lower() for i in items)
print(f"Sacred bowl received: {'✓ YES' if has_bowl else '✗ NO'}")

# ── Turn 6: Ask about latte della memoria ────────────────────────────────────
print("\n[TURN 6] Ask about latte della memoria")
d = chat("Ho del latte speciale delle mucche del villaggio. Potrebbe aiutarti con le tue visioni?")
show("Latte della memoria offer (check vision response + anim)", d)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
