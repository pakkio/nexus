# chat_manager_tests.py
import pytest
from chat_manager import (
    ChatSession,
    format_stats,
    generate_summary_for_llsettext,
    generate_sl_command_prefix,
)


def test_chat_session_initialization(mock_terminal_formatter):
    session = ChatSession(model_name="test-model")
    session.set_system_prompt("Test prompt")

    assert session.get_system_prompt() == "Test prompt"
    assert session.get_model_name() == "test-model"
    assert len(session.messages) == 0


def test_add_message(mock_terminal_formatter):
    session = ChatSession(model_name="test-model")
    session.set_system_prompt("Test")

    session.add_message("user", "Hello")
    assert len(session.messages) == 1
    assert session.messages[0]["role"] == "user"
    assert session.messages[0]["content"] == "Hello"

    session.add_message("assistant", "Hi")
    assert len(session.messages) == 2
    assert session.messages[1]["role"] == "assistant"
    assert session.messages[1]["content"] == "Hi"

    session.last_stats = {"total_tokens": 10}
    assert session.last_stats == {"total_tokens": 10}


def test_clear_memory(mock_terminal_formatter):
    session = ChatSession(model_name="test-model")
    session.set_system_prompt("Test")
    session.add_message("user", "Test message")
    session.clear_memory()
    assert len(session.messages) == 0


def test_format_stats():
    stats = {
        "total_tokens": 100,
        "completion_tokens": 50,
        "prompt_tokens": 50,
        "total_time": 1.5,
    }
    formatted = format_stats(stats)

    assert "100" in formatted
    assert "1.5" in formatted or "1.50" in formatted


# ---- New unit tests for SL helpers ----

def test_generate_summary_for_llsettext_basic_cleanup():
    npc_name = "Lyra"
    text = "*Lyra ti dice* Benvenuto, viandante! Qui trovi misteri e meraviglie."
    summary = generate_summary_for_llsettext(text, npc_name)
    assert "Lyra ti dice" not in summary
    assert len(summary) <= 80
    assert "misteri" in summary


def test_generate_summary_for_llsettext_truncation_sentence_boundary():
    npc_name = "Erasmus"
    long_sentence = (
        "Erasmus ti informa che questa è una frase estremamente lunga che dovrebbe superare il limite di ottanta caratteri. "
        "Seconda frase ignorata."
    )
    summary = generate_summary_for_llsettext(long_sentence, npc_name)
    assert len(summary) <= 80
    assert summary.endswith("...")


def test_generate_summary_for_llsettext_no_period_truncation():
    npc_name = "Syra"
    long_text = "Syra ti dice Questo testo senza punti dovrebbe essere troncato al limite consentito con parole"
    summary = generate_summary_for_llsettext(long_text, npc_name)
    assert len(summary) <= 80
    assert summary.endswith("...")


def test_generate_sl_command_prefix_with_response_and_teleport():
    npc_data = {
        "name": "Meridia",
        "lookup": "altar",
        "emotes": "wave",
        "animations": "bow",
        "llsettext": "fallback text that should not be used",
        "teleport": "128,64,30",
    }
    npc_response = "Benvenuto al Nexus. Seguimi e ti mostrerò il sentiero."
    cmd = generate_sl_command_prefix(npc_data, include_teleport=True, npc_response=npc_response)

    assert cmd.startswith("[") and cmd.endswith("]")
    assert "lookup=altar" in cmd
    assert "emote=wave" in cmd
    assert "anim=bow" in cmd
    assert "teleport=128,64,30" in cmd
    # llSetText should be derived from npc_response, not the fallback
    assert "llSetText=" in cmd
    assert "fallback text" not in cmd


def test_generate_sl_command_prefix_without_teleport_and_without_response():
    npc_data = {
        "name": "Cassian",
        "lookup": "relic",
        "emotes": "nod",
        "animations": "shrug",
        "llsettext": "Default banner",
        "teleport": "200,200,25",
    }
    cmd = generate_sl_command_prefix(npc_data, include_teleport=False, npc_response="")

    assert cmd.startswith("[") and cmd.endswith("]")
    assert "lookup=relic" in cmd
    assert "emote=nod" in cmd
    assert "anim=shrug" in cmd
    assert "teleport=" not in cmd
    # With no npc_response, llsettext falls back to predefined
    assert "llSetText=Default banner" in cmd
