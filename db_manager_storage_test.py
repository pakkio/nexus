"""DbManager must behave identically on the file and SQLite storage backends."""
import json
import os
import shutil

import pytest

from db_manager import DbManager
from doc_store import FileDocStore, SqliteDocStore
from migrate_to_sqlite import migrate

NPC = {"name": "Elira", "area": "Forest", "role": "Guardiana", "treasure": "seme_della_foresta"}
NPC2 = {"name": "Mara", "area": "Village", "role": "Erborista", "is_default_npc": True}
LOC = {"id": "forest", "name": "Forest", "area_type": "wild", "access_level": "open"}


@pytest.fixture(params=["file", "sqlite"])
def db(request, tmp_path):
    d = DbManager(use_mockup=True, mockup_dir=str(tmp_path), storage=request.param)
    d.store.put("NPCs", "NPC.forest.elira", dict(NPC))
    d.store.put("NPCs", "NPC.village.mara", dict(NPC2))
    d.store.put("Locations", "forest", dict(LOC))
    d.store.put("Storyboards", "Storyboard.Test", {"name": "Test", "description": "d"})
    return d


def test_static_lookups(db):
    assert db.get_storyboard()["name"] == "Test"
    assert db.get_npc("forest", "ELIRA")["code"] == "NPC.forest.elira"
    assert db.get_npc_by_code("NPC.village.mara")["name"] == "Mara"
    assert db.get_npc_by_name("mara")["area"] == "Village"
    assert db.get_default_npc("Village")["name"] == "Mara"
    assert [n["code"] for n in db.list_npcs_by_area()] == ["NPC.forest.elira", "NPC.village.mara"]
    assert db.get_areas() == ["Forest"]
    assert db.get_location("forest")["name"] == "Forest"
    assert db.get_location_by_name("forest")["id"] == "forest"
    assert db.list_locations()[0]["id"] == "forest"
    assert db.get_npc("nowhere", "nobody") is None


def test_player_state_credits_and_flags(db):
    assert db.get_player_credits("p1") == 220                    # default created on first read
    db.save_player_state("p1", {"player_credits_cache": 170, "current_area": "Forest",
                                "plot_flags": {"_reward_given_x": True}})
    st = db.load_player_state("p1")
    assert st["credits"] == 170 and st["current_area"] == "Forest"
    assert st["plot_flags"] == {"_reward_given_x": True}
    assert db.update_player_credits("p1", -50, {}) is True
    assert db.get_player_credits("p1") == 120
    assert db.update_player_credits("p1", -500, {}) is False     # cannot go negative
    assert db.get_player_credits("p1") == 120


def test_inventory(db):
    assert db.load_inventory("p1") == []
    assert db.add_item_to_inventory("p1", "Pozione di Guarigione") is True
    assert db.add_item_to_inventory("p1", "Seme della Foresta") is True
    assert db.find_item_by_partial_name("p1", "pozione")
    assert db.remove_item_from_inventory("p1", "Pozione di Guarigione") is True
    assert db.load_inventory("p1") == ["seme della foresta"]


def test_profile_default_and_roundtrip(db):
    prof = db.load_player_profile("p1")
    prof["core_traits"]["honor"] = 9
    db.save_player_profile("p1", prof)
    assert db.load_player_profile("p1")["core_traits"]["honor"] == 9


def test_conversations(db):
    hist = [{"role": "user", "content": "ciao"}, {"role": "assistant", "content": "salve"}]
    db.save_conversation("p1", "NPC.forest.elira", hist)
    db.save_conversation("p1", "NPC.village.mara", hist[:1])
    db.save_conversation("p10", "NPC.forest.elira", hist)
    assert db.load_conversation("p1", "NPC.forest.elira") == hist
    assert db.load_conversation("p1", "missing") == []
    got = db.get_conversation_history("p1")
    assert sorted(c["npc_code"] for c in got) == ["NPC.forest.elira", "NPC.village.mara"]
    assert len(db.get_conversation_history("p1", "NPC.forest.elira")) == 1
    info = db.get_player_storage_info("p1")
    assert info["conversations"]["npc_count"] == 2
    assert len(db.get_all_conversations_for_analysis("p1")) == 2
    assert db.save_conversation_analysis("p1", "analysis text") is True
    assert "analysis text" in db.get_conversation_analysis("p1")["analysis"]
    assert db.clear_conversations("p1") is True
    assert db.get_conversation_history("p1") == []
    assert len(db.get_conversation_history("p10")) == 1          # other players untouched


def test_reset_clears_player_data_but_keeps_world(db):
    db.save_player_state("p1", {"player_credits_cache": 5})
    db.add_item_to_inventory("p1", "x item")
    db.save_conversation("p1", "NPC.forest.elira", [{"role": "user", "content": "a"}])
    db.reset_database()
    assert db.store.get("PlayerState", "p1") is None
    assert db.store.get("Inventory", "p1") is None
    assert db.get_conversation_history("p1") == []
    assert db.get_npc_by_code("NPC.forest.elira") is not None


def test_migration_preserves_everything(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "out" / "n.db"
    f = DbManager(use_mockup=True, mockup_dir=str(src), storage="file")
    f.store.put("NPCs", "NPC.forest.elira", dict(NPC))
    f.save_player_state("p1", {"player_credits_cache": 170, "plot_flags": {"a": True}})
    f.add_item_to_inventory("p1", "Seme della Foresta")
    f.save_conversation("p1", "NPC.forest.elira", [{"role": "user", "content": "è ñ"}])
    f.save_conversation_analysis("p1", "txt")
    assert migrate(str(src), str(dst)) == 0
    s = DbManager(use_mockup=True, mockup_dir=str(src), storage="sqlite",)
    s.store = SqliteDocStore(str(dst))
    assert s.load_player_state("p1")["credits"] == 170
    assert s.load_inventory("p1") == ["seme della foresta"]
    assert s.load_conversation("p1", "NPC.forest.elira")[0]["content"] == "è ñ"
    assert s.get_npc_by_code("NPC.forest.elira")["name"] == "Elira"
    assert "txt" in s.get_conversation_analysis("p1")["analysis"]
    assert migrate(str(src), str(dst)) == 2                      # refuses to overwrite without --force
    assert migrate(str(src), str(dst), force=True) == 0
