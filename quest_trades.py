"""Authoritative quest-trade table and grant validation.

The LLM decides *what an NPC says*; this module decides *what an NPC may give*.
A [GIVEN_ITEMS: ...] tag emitted by the model is checked against the table:

* a quest item may only come from the NPC that owns it;
* an NPC that wants something in exchange only gives once the player has
  really handed it over with /give (this turn, or recorded earlier);
* only the seller (price) may charge credits, and only the listed price.

NPCs not in the table keep the previous, model-driven behaviour.
"""
import re
from typing import Dict, List, Optional, Tuple

from db_manager import items_match

# npc code -> {"gives": item, "requires": item to hand over | None, "price": credits | None}
QUEST_TRADES: Dict[str, Dict[str, Optional[object]]] = {
    "NPC.village.mara":      {"gives": "Pozione di Guarigione",      "requires": None,                        "price": 50},
    "NPC.forest.elira":      {"gives": "Seme della Foresta",         "requires": "Pozione di Guarigione",     "price": None},
    "NPC.mountain.boros":    {"gives": "Minerale di Ferro Antico",   "requires": "Seme della Foresta",        "price": None},
    "NPC.village.garin":     {"gives": "Trucioli di Ferro",          "requires": "Minerale di Ferro Antico",  "price": None},
    "NPC.tavern.jorin":      {"gives": "Ciotola dell'Offerta Sacra", "requires": "Trucioli di Ferro",         "price": None},
    "NPC.ancientruins.syra": {"gives": "Cristallo di Memoria Antica", "requires": "Ciotola dell'Offerta Sacra", "price": None},
    "NPC.city.cassian":      {"gives": "Pergamena della Saggezza",   "requires": None,                        "price": 50},
}

_QUEST_ITEMS = sorted({str(t["gives"]) for t in QUEST_TRADES.values()} |
                      {str(t["requires"]) for t in QUEST_TRADES.values() if t["requires"]})

_CREDITS_RE = re.compile(r"^(-?\d+)\s+credits?$", re.IGNORECASE)
_REMOVAL_RE = re.compile(r"^-(\d+)\s+(.+)$")


def delivered_flag_key(npc_code: str) -> str:
    return f"_delivered_{npc_code}"


def is_quest_item(name: str) -> bool:
    return any(items_match(name, q) for q in _QUEST_ITEMS)


def requirement_met(npc_code: str, trade_this_turn: Optional[dict], plot_flags: Optional[dict]) -> bool:
    """True when the player has handed this NPC the item it asks for."""
    quest = QUEST_TRADES.get(npc_code)
    if not quest or not quest["requires"]:
        return True
    if (plot_flags or {}).get(delivered_flag_key(npc_code)):
        return True
    t = trade_this_turn or {}
    return (t.get("type") == "item"
            and t.get("npc_code") in (None, npc_code)
            and items_match(t.get("item_name", ""), str(quest["requires"])))


def validate_grant(npc_code: str, raw_tokens: List[str], trade_this_turn: Optional[dict],
                   plot_flags: Optional[dict], player_credits: int) -> Tuple[List[str], List[str], bool]:
    """Filter the tokens of a [GIVEN_ITEMS:] tag.

    Returns (accepted_tokens, rejection_reasons, own_item_granted).
    NPCs absent from QUEST_TRADES are passed through untouched.
    """
    quest = QUEST_TRADES.get(npc_code)
    if not quest:
        return list(raw_tokens), [], False

    gives, price = str(quest["gives"]), quest["price"]
    accepted: List[str] = []
    rejected: List[str] = []
    credit_tokens: List[str] = []
    own_item = False

    for tok in raw_tokens:
        if _CREDITS_RE.match(tok):
            credit_tokens.append(tok)
        elif _REMOVAL_RE.match(tok):
            accepted.append(tok)          # removals only ever touch the player's own inventory
        elif items_match(tok, gives):
            if not requirement_met(npc_code, trade_this_turn, plot_flags):
                rejected.append(f"'{tok}': player has not handed over '{quest['requires']}'")
            elif price and player_credits < int(price):
                rejected.append(f"'{tok}': player has {player_credits} credits, price is {price}")
            else:
                accepted.append(gives)    # canonical spelling
                own_item = True
        elif is_quest_item(tok):
            rejected.append(f"'{tok}': not this NPC's to give")
        else:
            accepted.append(tok)          # non-quest items (lore gifts, etc.) unchanged

    for tok in credit_tokens:
        amount = int(_CREDITS_RE.match(tok).group(1))
        if price and own_item and amount == -int(price):
            accepted.append(tok)
        else:
            rejected.append(f"'{tok}': credits not allowed here (price={price}, granted={own_item})")

    return accepted, rejected, own_item
