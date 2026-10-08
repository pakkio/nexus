import os, tempfile, time
import pytest
from doc_store import FileDocStore, SqliteDocStore, make_store


@pytest.fixture(params=["file", "sqlite"])
def store(request, tmp_path):
    return make_store(str(tmp_path), backend=request.param)


def test_put_get_delete_roundtrip(store):
    doc = {"name": "Elira", "area": "Forest", "note": "è ñ 日本"}
    store.put("NPCs", "NPC.forest.elira", doc)
    assert store.get("NPCs", "NPC.forest.elira") == doc
    store.delete("NPCs", "NPC.forest.elira")
    assert store.get("NPCs", "NPC.forest.elira") is None


def test_missing_returns_none(store):
    assert store.get("PlayerState", "nobody") is None
    assert store.meta("PlayerState", "nobody") is None


def test_items_sorted_and_filtered_by_prefix(store):
    store.put("ConversationHistory", "p1/NPC.a", [{"role": "user", "content": "x"}])
    store.put("ConversationHistory", "p1/NPC.b", [])
    store.put("ConversationHistory", "p10/NPC.a", [{"role": "user", "content": "y"}])
    store.put("ConversationHistory", "P1/NPC.a", [{"role": "user", "content": "case"}])
    keys = [k for k, *_ in store.items("ConversationHistory", "p1")]
    assert keys == ["p1/NPC.a", "p1/NPC.b"]       # no p10, no case-insensitive P1
    assert len(store.items("ConversationHistory")) == 4


def test_meta_has_mtime_and_size(store):
    store.put("PlayerProfiles", "p1", {"a": 1})
    mtime, size = store.meta("PlayerProfiles", "p1")
    assert abs(mtime - time.time()) < 5 and size > 0


def test_text_kind(store):
    store.put("ConversationAnalysis", "p1", "line1\nline2")
    assert store.get("ConversationAnalysis", "p1") == "line1\nline2"


def test_inventory_and_delete_kind(store):
    store.put("Inventory", "p1", ["a", "b"])
    store.put("Inventory", "p2", ["c"])
    store.put("PlayerState", "p1", {"credits": 5})
    assert store.delete_kind("Inventory") == 2
    assert store.get("Inventory", "p1") is None
    assert store.get("PlayerState", "p1") == {"credits": 5}


def test_delete_conversations_of_one_player(store):
    store.put("ConversationHistory", "p1/NPC.a", [1])
    store.put("ConversationHistory", "p2/NPC.a", [2])
    store.delete_kind("ConversationHistory", "p1")
    assert store.get("ConversationHistory", "p1/NPC.a") is None
    assert store.get("ConversationHistory", "p2/NPC.a") == [2]


@pytest.mark.parametrize("bad", ["../x", "a/../b", "", "/abs", "a\\b"])
def test_unsafe_keys_rejected(store, bad):
    with pytest.raises(ValueError):
        store.put("PlayerState", bad, {})


def test_sqlite_persists_across_instances(tmp_path):
    p = str(tmp_path / "n.db")
    SqliteDocStore(p).put("PlayerState", "p1", {"credits": 7})
    assert SqliteDocStore(p).get("PlayerState", "p1") == {"credits": 7}
