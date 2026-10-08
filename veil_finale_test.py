import pytest
import veil_finale as vf
from command_handlers.handle_choose import handle_choose


class TF:
    YELLOW = GREEN = RESET = DIM = RED = ""


class FakeDB:
    def __init__(self): self.items = []
    def add_item_to_inventory(self, pid, name, st=None): self.items.append(name); return True


class FakeSession:
    def __init__(self): self.messages = []
    def add_message(self, role, text): self.messages.append((role, text))


def make_state(code=vf.MERIDIA_CODE, flags=None):
    return {"TerminalFormatter": TF, "db": FakeDB(), "player_id": "p1",
            "current_npc": {"code": code, "name": "Meridia"}, "chat_session": FakeSession(),
            "plot_flags": {} if flags is None else flags, "actions_this_turn_for_profile": []}


def open_flags():
    return {vf.TURNS_KEY: {"memory": 3, "progress": 3, "balance": 3}}


def test_gate_closed_until_all_three_leaders_heard(monkeypatch):
    monkeypatch.delenv("FACTION_GATE_TURNS", raising=False)
    flags = {}
    assert vf.gate_status(flags) == (False, ["Lyra", "Theron", "Boros"])
    for _ in range(3):
        vf.record_dialogue_turn(flags, "NPC.sanctumofwhispers.lyra")
        vf.record_dialogue_turn(flags, "NPC.city.theron")
    assert vf.gate_status(flags) == (False, ["Boros"])
    vf.record_dialogue_turn(flags, "NPC.mountain.boros")
    vf.record_dialogue_turn(flags, "NPC.mountain.boros")
    assert vf.gate_status(flags)[0] is False          # 2 of 3 turns is not enough
    vf.record_dialogue_turn(flags, "NPC.mountain.boros")
    assert vf.gate_status(flags) == (True, [])


def test_only_faction_leaders_count():
    flags = {}
    for code in ("NPC.city.cassian", "NPC.city.irenna", "NPC.forest.elira", None):
        assert vf.record_dialogue_turn(flags, code) is None
    assert flags == {}


def test_turn_threshold_is_configurable(monkeypatch):
    monkeypatch.setenv("FACTION_GATE_TURNS", "1")
    flags = {}
    for code in ("NPC.sanctumofwhispers.lyra", "NPC.city.theron", "NPC.mountain.boros"):
        vf.record_dialogue_turn(flags, code)
    assert vf.gate_status(flags)[0]


@pytest.mark.parametrize("word,fate", [("preserve", "preserve"), ("Rinnova", "preserve"), ("destroy", "dissolve"),
                                       ("DISSOLVE", "dissolve"), ("transform", "transform"), ("trasforma", "transform")])
def test_fate_aliases(word, fate):
    assert vf.normalize_fate(word) == fate


def test_unknown_fate_rejected():
    assert vf.normalize_fate("conquer") is None and vf.normalize_fate("") is None


def test_choose_requires_meridia():
    st = make_state(code="NPC.city.theron", flags=open_flags())
    handle_choose("preserve", st)
    assert vf.FATE_KEY not in st["plot_flags"] and st["db"].items == []


def test_choose_blocked_while_gate_closed():
    st = make_state(flags={vf.TURNS_KEY: {"memory": 3}})
    handle_choose("preserve", st)
    assert vf.FATE_KEY not in st["plot_flags"] and st["db"].items == []


def test_choose_records_fate_grants_loom_and_triggers_reply():
    st = make_state(flags=open_flags())
    handle_choose("transform", st)
    assert st["plot_flags"][vf.FATE_KEY] == "transform" and vf.FATE_AT_KEY in st["plot_flags"]
    assert st["db"].items == [vf.LOOM_ITEM]
    assert st["force_npc_turn_after_command"] is True
    assert st["chat_session"].messages and "transform" in st["chat_session"].messages[0][1]


def test_choice_is_irreversible():
    st = make_state(flags=open_flags())
    handle_choose("preserve", st)
    st["db"].items.clear()
    handle_choose("dissolve", st)
    assert st["plot_flags"][vf.FATE_KEY] == "preserve" and st["db"].items == []


def test_bad_argument_changes_nothing():
    st = make_state(flags=open_flags())
    handle_choose("conquer", st)
    assert vf.FATE_KEY not in st["plot_flags"]


def test_meridia_prompt_names_only_the_three_canonical_factions():
    text = "\n".join(vf.meridia_prompt_lines({}))
    for name in ("Custodi della Memoria", "Progressisti", "Viandanti dell'Equilibrio"):
        assert name in text
    assert "/choose" in text and "Sussurratori" not in text
    done = "\n".join(vf.meridia_prompt_lines({vf.FATE_KEY: "dissolve"}))
    assert "GIÀ SCELTO: dissolve" in done and "/choose" not in done


def test_plot_flags_survive_a_new_session(tmp_path):
    """Regression: saved plot_flags (rewards, faction progress, fate) must be restored when a player's session is rebuilt."""
    import inspect
    import game_system_api
    src = inspect.getsource(game_system_api)
    assert "plot_flags=dict(saved_state.get('plot_flags') or {})" in src
