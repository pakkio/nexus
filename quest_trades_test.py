from quest_trades import validate_grant

ELIRA, MARA, BOROS = "NPC.forest.elira", "NPC.village.mara", "NPC.mountain.boros"
POTION_GIVEN = {"type": "item", "item_name": "pozione di guarigione", "npc_code": ELIRA}


def test_stray_copied_tag_from_wrong_npc_rejected():
    ok, rej, own = validate_grant(ELIRA, ["Pozione di Guarigione", "-50 Credits"], None, {}, 220)
    assert ok == [] and len(rej) == 2 and not own


def test_item_without_delivery_rejected():
    ok, rej, own = validate_grant(BOROS, ["Minerale di Ferro Antico"], None, {}, 220)
    assert ok == [] and not own


def test_delivery_this_turn_grants_item():
    trade = {"type": "item", "item_name": "Seme della Foresta", "npc_code": BOROS}
    ok, rej, own = validate_grant(BOROS, ["Minerale di Ferro Antico"], trade, {}, 220)
    assert ok == ["Minerale di Ferro Antico"] and own and not rej


def test_delivery_remembered_from_earlier_turn():
    ok, _, own = validate_grant(ELIRA, ["Seme della Foresta"], None, {"_delivered_NPC.forest.elira": True}, 0)
    assert own and ok == ["Seme della Foresta"]


def test_delivery_to_other_npc_does_not_count():
    trade = {"type": "item", "item_name": "pozione di guarigione", "npc_code": "NPC.village.garin"}
    _, _, own = validate_grant(ELIRA, ["Seme della Foresta"], trade, {}, 220)
    assert not own


def test_mara_sale_needs_exact_price_and_funds():
    ok, _, own = validate_grant(MARA, ["Pozione di Guarigione", "-50 Credits"], None, {}, 220)
    assert own and ok == ["Pozione di Guarigione", "-50 Credits"]
    ok, rej, own = validate_grant(MARA, ["Pozione di Guarigione", "-50 Credits"], None, {}, 10)
    assert ok == [] and not own
    ok, rej, own = validate_grant(MARA, ["Pozione di Guarigione", "-5 Credits"], None, {}, 220)
    assert ok == ["Pozione di Guarigione"] and rej


def test_non_quest_npc_untouched():
    ok, rej, own = validate_grant("NPC.liminalvoid.erasmus", ["Visione del Vuoto Fertile"], None, {}, 0)
    assert ok == ["Visione del Vuoto Fertile"] and not rej
