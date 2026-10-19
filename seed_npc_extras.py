#!/usr/bin/env python3
"""Write the tracked NPC extras into the configured document store.

    python seed_npc_extras.py [--root database]

Sources (next to this script):
  NPC_BUSINESS_CARDS.json  -> business_card      (the "biglietto da visita" notecard)
  NPC_EXTRAS.json          -> teleport, notecard_feature

Honours NEXUS_STORAGE / NEXUS_SQLITE_PATH like the server does. Only those fields of NPCs
already in the store are touched; running it twice changes nothing. The NPC files in
database/ are not tracked, so run this after re-importing NPCs.
"""
import argparse
import json
import os

from doc_store import make_store

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def seed(root: str) -> int:
    wanted = {}   # npc key -> {field: value}
    for key, text in _load("NPC_BUSINESS_CARDS.json").items():
        wanted.setdefault(key, {})["business_card"] = text
    for key, fields in _load("NPC_EXTRAS.json").items():
        wanted.setdefault(key, {}).update(fields)

    store = make_store(root)
    changed = 0
    for key, fields in wanted.items():
        npc = store.get("NPCs", key)
        if npc is None:
            print(f"  {key}: not in store, skipped")
            continue
        diff = [f for f, v in fields.items() if npc.get(f) != v]
        if diff:
            npc.update(fields)
            store.put("NPCs", key, npc)
            changed += 1
            print(f"  {key}: updated {', '.join(diff)}")
    print(f"{changed} of {len(wanted)} NPCs updated")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="database")
    raise SystemExit(seed(ap.parse_args().root))
