#!/usr/bin/env python3
"""Write the NPC business cards (NPC_BUSINESS_CARDS.json) into the configured document store.

    python seed_business_cards.py [--root database]

Honours NEXUS_STORAGE / NEXUS_SQLITE_PATH like the server does. Only the `business_card`
field of NPCs already in the store is touched; running it twice changes nothing.
"""
import argparse
import json
import os

from doc_store import make_store


def seed(root: str, cards_path: str) -> int:
    with open(cards_path, encoding="utf-8") as f:
        cards = json.load(f)
    store = make_store(root)
    changed = 0
    for key, text in cards.items():
        npc = store.get("NPCs", key)
        if npc is None:
            print(f"  {key}: not in store, skipped")
        elif npc.get("business_card") != text:
            npc["business_card"] = text
            store.put("NPCs", key, npc)
            changed += 1
            print(f"  {key}: updated")
    print(f"{changed} of {len(cards)} NPC cards written")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="database")
    ap.add_argument("--cards", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "NPC_BUSINESS_CARDS.json"))
    a = ap.parse_args()
    raise SystemExit(seed(a.root, a.cards))
