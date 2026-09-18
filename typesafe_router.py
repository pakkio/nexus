"""TypeSafe System One (Jev) fast-path for structured decisions.

Jev does NOT generate strings -- it returns typed Choice/Score/Noul answers
with calibrated confidence. Use it for routing/classification, keep LLMs
(OpenRouter) for dialogue/narrative generation.

Primary consumer: command_interpreter.interpret_user_intent().
Convention mirrors its return dict:
  {is_command, inferred_command, confidence, original_input, reasoning, provider}
"""
import os
import re
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL_DEFAULT = "jev-latest"

_intent_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 120


def is_typesafe_enabled() -> bool:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    if os.environ.get("TYPESAFE_ENABLED", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def get_model() -> str:
    return os.environ.get("TYPESAFE_MODEL", MODEL_DEFAULT)


def system_one(state: Any, questions: Dict[str, Any],
               model: Optional[str] = None,
               timeout: float = 15.0) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Raw System One call. Returns (answers|None, meta). Never raises."""
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        return None, {"error": "TYPESAFE_API_KEY not set", "provider": "typesafe"}
    start = time.time()
    try:
        resp = requests.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"state": state, "model": model or get_model(), "questions": questions},
            timeout=timeout,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        if resp.status_code != 200:
            logger.warning(f"[TypeSafe] HTTP {resp.status_code}: {resp.text[:200]}")
            return None, {"error": f"HTTP {resp.status_code}", "elapsed_ms": elapsed_ms, "provider": "typesafe"}
        data = resp.json()
        meta = {"elapsed_ms": elapsed_ms, "provider": "typesafe",
                "model": data.get("model"), "usage": data.get("usage")}
        return data.get("answers"), meta
    except Exception as e:
        logger.warning(f"[TypeSafe] call failed: {e}")
        return None, {"error": str(e), "elapsed_ms": int((time.time() - start) * 1000), "provider": "typesafe"}


INTENT_QUESTIONS: Dict[str, Any] = {
    "intent": {
        "type": "choice",
        "instructions": "The player's primary intent in this text RPG. 'dialogue' means talking/acting in-character with the current NPC (including asking them questions, mentioning other characters, describing future plans, picking up or examining things). All other options are explicit system commands.",
        "criteria": {
            "dialogue": "In-character speech, questions to the NPC, talking ABOUT other NPCs, future plans ('vado da X'), picking up/examining/environment actions, polite requests ('hai qualcosa?', 'mi puoi dare?')",
            "go": "Wants to move/travel to another area ('vado in taverna', 'andiamo al villaggio')",
            "talk": "Wants to START a conversation with a specific NPC here and now ('parla con Jorin', '/talk Boros')",
            "give": "Wants to GIVE/OFFER a specific item or credits to the NPC ('ti do la moneta', 'eccoti la spada', 'offro 50 crediti')",
            "receive": "Direct/imperative demand for an item ('dammi il diario', 'voglio quel libro', 'passami la chiave')",
            "inventory": "Wants to see inventory/belongings ('cosa ho con me?', 'inventario')",
            "who": "Wants to know who is here, as a SYSTEM query (not asking the NPC about other characters)",
            "areas": "Wants the list of visitable areas",
            "help": "Wants help with commands/what they can do",
            "hint": "EXPLICIT request for the wise guide consultation ('/hint', 'consulta la guida', 'dammi un consiglio')",
            "exit": "Wants to leave/quit ('esco', 'basta', 'fine')",
        },
    },
    "is_future_plan": {
        "type": "noul",
        "instructions": "The player is talking ABOUT going to / talking to someone later (future plans like 'vado da Boros', 'andro da Lyra'), not issuing a command now",
    },
    "is_npc_discussion": {
        "type": "noul",
        "instructions": "The player asks the CURRENT npc about another character ('parlami di Theron', 'chi e Boros?', 'cosa sai di Lyra?')",
    },
    "is_collection_action": {
        "type": "noul",
        "instructions": "The player picks up, takes, touches or examines something in the environment ('raccolgo la piaga', 'prendo il campione', 'tocco l'oggetto')",
    },
}


def _extract_go_area(user_input: str, game_state: Dict[str, Any]) -> Optional[str]:
    from command_interpreter import get_italian_area_mapping
    input_lower = user_input.lower()
    available = game_state.get("available_areas", []) or []
    mapping = get_italian_area_mapping()
    # direct match on known area names first
    for area in available:
        if area.lower() in input_lower:
            return area
    for it_name, en_name in mapping.items():
        if it_name in input_lower and en_name in available:
            return en_name
    return None


def _extract_after(user_input: str, patterns: List[str]) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, user_input, re.IGNORECASE)
        if m:
            val = (m.group(1) or "").strip().strip("'\".,!?")
            # drop leading italian articles for items
            val = re.sub(r"^(il|lo|la|i|gli|le|un|uno|una|l')\s+", "", val, flags=re.IGNORECASE)
            if val:
                return val
    return None


def _map_answers_to_intent(user_input: str, game_state: Dict[str, Any],
                           answers: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    intent_ans = (answers.get("intent") or {})
    intent = intent_ans.get("choice", "dialogue")
    confidence = float(intent_ans.get("confidence", 0.0) or 0.0)
    probs = intent_ans.get("probabilities", {})
    future = float((answers.get("is_future_plan") or {}).get("noul", 0.0) or 0.0)
    npc_disc = float((answers.get("is_npc_discussion") or {}).get("noul", 0.0) or 0.0)
    collect = float((answers.get("is_collection_action") or {}).get("noul", 0.0) or 0.0)

    # Disambiguation guards (speculative fan-out pattern): these are DIALOGUE, not commands
    if intent == "talk" and (future > 0.7 or npc_disc > 0.7):
        return {"is_command": False, "inferred_command": None, "confidence": max(confidence, future, npc_disc),
                "original_input": user_input,
                "reasoning": f"TypeSafe: talk overridden by future_plan={future:.2f}/npc_discussion={npc_disc:.2f}",
                "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}
    if intent in ("give", "receive") and collect > 0.7:
        return {"is_command": False, "inferred_command": None, "confidence": collect,
                "original_input": user_input,
                "reasoning": f"TypeSafe: collection action, not give/receive ({collect:.2f})",
                "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}
    if intent == "who" and npc_disc > 0.7:
        return {"is_command": False, "inferred_command": None, "confidence": npc_disc,
                "original_input": user_input,
                "reasoning": "TypeSafe: asking NPC about others = dialogue",
                "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}
    if intent == "hint" and re.search(r"cosa (devo fare|mi consigli)|come procedo|quale missione|ho bisogno di aiuto",
                                      user_input, re.IGNORECASE):
        return {"is_command": False, "inferred_command": None, "confidence": confidence,
                "original_input": user_input,
                "reasoning": "TypeSafe: generic help request to current NPC = dialogue, not /hint",
                "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}

    if intent == "dialogue":
        return {"is_command": False, "inferred_command": None, "confidence": confidence,
                "original_input": user_input,
                "reasoning": f"TypeSafe intent=dialogue ({confidence:.2f})",
                "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}

    # Slot filling in code (Jev returns no strings): same generic convention as rule fallback
    if intent == "go":
        area = _extract_go_area(user_input, game_state)
        cmd = f"/go {area}" if area else "/areas"
    elif intent == "talk":
        name = _extract_after(user_input, [
            r"(?:parla con|parlare con|voglio parlare con|talk to|speak with|speak to|parlo con)\s+([A-Za-zÀ-ÿ' ]+)",
        ])
        cmd = f"/talk {name.strip().title()}" if name else "/talk <npc>"
    elif intent == "give":
        item = _extract_after(user_input, [
            r"(?:ti do|do la|do il|eccoti|offro|regalo|consegno|tieni|prendi|ecco [a-z ]*?)\s+(.+)",
        ])
        cmd = f"/give {item}" if item else "/give item"
    elif intent == "receive":
        item = _extract_after(user_input, [
            r"(?:dammi|passami|voglio|devo avere)\s+(.+)",
        ])
        cmd = f"/receive {item.strip().title()}" if item else "/receive item"
    else:
        cmd = {"inventory": "/inventory", "who": "/who", "areas": "/areas",
               "help": "/help", "hint": "/hint", "exit": "/exit"}.get(intent, "/help")

    return {"is_command": True, "inferred_command": cmd, "confidence": confidence,
            "original_input": user_input,
            "reasoning": f"TypeSafe intent={intent} ({confidence:.2f}) probs={ {k: round(v, 2) for k, v in (probs or {}).items() if v > 0.05} }",
            "provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}


def interpret_intent_typesafe(user_input: str, game_state: Dict[str, Any],
                              confidence_threshold: float = 0.7) -> Optional[Dict[str, Any]]:
    """Fast-path intent classification. Returns None when unavailable/failing.

    Returns dict compatible with interpret_user_intent, plus provider='typesafe'.
    Low-confidence results are still returned (caller applies threshold);
    None means 'fall through to LLM/rules'.
    """
    if not is_typesafe_enabled():
        return None
    # short-TTL cache: repeated identical inputs in a session are common
    cache_key = f"{user_input.strip().lower()}|{game_state.get('current_area')}|{str(game_state.get('available_areas'))}"
    cached = _intent_cache.get(cache_key)
    if cached and (time.time() - cached["_ts"]) < _CACHE_TTL:
        out = dict(cached["result"])
        out["reasoning"] = out.get("reasoning", "") + " (cached)"
        return out

    state = {
        "player_input": user_input,
        "current_area": game_state.get("current_area"),
        "current_npc": (game_state.get("current_npc") or {}).get("name") if isinstance(game_state.get("current_npc"), dict) else game_state.get("current_npc"),
        "in_hint_mode": game_state.get("in_lyra_hint_mode", False),
        "available_areas": game_state.get("available_areas", []),
    }
    answers, meta = system_one(state, INTENT_QUESTIONS)
    if not answers or "intent" not in answers:
        return None
    try:
        result = _map_answers_to_intent(user_input, game_state, answers, meta)
        _intent_cache[cache_key] = {"result": result, "_ts": time.time()}
        return result
    except Exception as e:
        logger.warning(f"[TypeSafe] mapping failed: {e}")
        return None


def choose_wise_guide_typesafe(story_description: str, npc_names: List[str]) -> Optional[Tuple[str, float]]:
    """Choice-based guide selection. Returns (name, confidence) or None."""
    if not is_typesafe_enabled() or not npc_names:
        return None
    # Jev Choice cardinality caps at 255; NPC lists are far smaller.
    criteria = {name: f"Candidate NPC named {name}" for name in sorted(set(npc_names))}
    answers, _meta = system_one(
        {"story": story_description[:2000], "note": "Pick the designated wise guide. Erasmus is the designated starting guide if present."},
        {"guide": {"type": "choice", "instructions": "Which NPC is the wise guide (Erasmus if present, else NONE)?", "criteria": {**criteria, "NONE": "No suitable guide"}}},
    )
    if not answers or "guide" not in answers:
        return None
    g = answers["guide"]
    if g.get("choice") in (None, "NONE"):
        return None
    if g.get("choice") in criteria:
        return g["choice"], float(g.get("confidence", 0.0) or 0.0)
    return None


# ---------------------------------------------------------------------------
# Item duplicate arbiter (fallback only).
# Deterministic rules (aliases, token-set match) run first and decide every
# observed case. Jev is consulted ONLY when a granted name shares tokens with
# an owned item without matching it (e.g. future paraphrases like
# "Seme del Bosco" vs "seme della foresta"). Merges require high confidence;
# quest completion logic never consults Jev (deterministic by design).
# ---------------------------------------------------------------------------

ITEM_MERGE_CONF_THRESHOLD = 0.8


def resolve_item_duplicate(new_name: str, inventory_names: List[str],
                           threshold: float = ITEM_MERGE_CONF_THRESHOLD
                           ) -> Tuple[Optional[str], float]:
    """Decide whether a granted item duplicates something owned.

    Returns (existing_name, confidence) to merge, or (None, confidence)
    to keep it as a new entry. Never raises; None means 'add as new'.
    """
    if not is_typesafe_enabled() or not new_name or not inventory_names:
        return None, 0.0
    try:
        options = {n: f"Already owned item: {n}" for n in list(dict.fromkeys(inventory_names))[:60]}
        options["__NEW__"] = ("A genuinely distinct item. Choose this whenever "
                              "in doubt: merging different objects is worse than a duplicate.")
        answers, meta = system_one(
            {"granted_item": new_name,
             "note": "The game just granted this item. Same object under different wording merges; otherwise it stays new."},
            {"match": {"type": "choice",
                       "instructions": "Is the granted item the same object as one already owned, only worded differently?",
                       "criteria": options}},
        )
        if not answers or "match" not in answers:
            return None, 0.0
        m = answers["match"]
        conf = float(m.get("confidence", 0.0) or 0.0)
        if m.get("choice") in (None, "__NEW__") or conf < threshold:
            return None, conf
        if m["choice"] in options:
            return m["choice"], conf
        return None, conf
    except Exception as e:
        logger.warning(f"[TypeSafe] item arbiter failed: {e}")
        return None, 0.0


# ---------------------------------------------------------------------------
# Player profiling: traits + leaning + veil perception.
# 8 core traits -> 8 parallel Scores (absolute 0-4 level, mapped to 1-10 in
# code, delta vs current value). Leaning + veil -> closed-set Choices, which
# also fixes free-string drift that downstream mechanics can't match.
# Open-ended narrative fields (patterns/tags/notes) stay on the LLM.
# ---------------------------------------------------------------------------

PROFILE_TRAITS = ("curiosity", "caution", "empathy", "skepticism",
                  "pragmatism", "aggression", "deception", "honor")

TRAIT_INSTRUCTIONS = {
    "curiosity": "How curious and inquisitive the player is: asks questions, explores, seeks lore",
    "caution": "How cautious and careful the player is: hesitates, weighs risks, avoids rash moves",
    "empathy": "How empathetic and compassionate the player is toward NPCs and their feelings",
    "skepticism": "How skeptical the player is: doubts claims, challenges authority, questions motives",
    "pragmatism": "How pragmatic and deal-oriented the player is: negotiates, seeks practical outcomes",
    "aggression": "How aggressive or confrontational the player is: threats, anger, demands",
    "deception": "How deceptive or manipulative the player is: lies, tricks, hidden agendas",
    "honor": "How honorable the player is: keeps promises, fairness, respect for others",
}

TRAIT_LEVELS = ["trait absent or minimal", "trait slightly present",
                "trait moderately present", "trait strongly present",
                "trait dominant in this interaction"]

# Closed veil set = exactly the values game mechanics understand
# (handle_sussurri.calculate_sussurri_resistance + consequence_system).
VEIL_CHOICES = {
    "protective_trust": "Trusts the Veil as protection, defends memory against the Oblivion",
    "neutral_curiosity": "Neutral, curious about the Veil without commitment",
    "growing_doubt": "Doubts about the Veil are growing, tempted by Oblivion ideas",
    "active_skepticism": "Actively skeptical of the Veil, leans toward doubting memory itself",
}

LEANING_CHOICES = {
    "progressist": "Pro-Oblivion: favors forgetting, tabula rasa, liberation from the past",
    "conservator": "Pro-Veil: favors preserving memory, protection, continuity",
    "neutral": "No clear alignment either way",
}

# Deltas smaller than this are treated as noise (no trait change).
TRAIT_NOISE_GATE = 0.5
# Categorical switches below this confidence are ignored (avoids flip-flop).
CATEGORICAL_CONF_THRESHOLD = 0.6


def _score_to_trait_value(score: float) -> float:
    """Map Jev Score level 0-4 onto the 1-10 trait scale."""
    return max(1.0, min(10.0, round(1.0 + float(score) * 2.25, 1)))


def profile_scores_typesafe(previous_profile: Dict[str, Any],
                            interaction_log: List[Dict[str, str]],
                            player_actions_summary: List[str],
                            current_npc_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fast-path profile numerics. Returns suggestion-dict fragment or None.

    Fragment keys match get_profile_update_suggestions_from_llm() output:
    trait_adjustments (deltas vs current values, as the applier expects),
    updated_veil_perception, updated_philosophical_leaning.
    Caller merges with LLM narrative fields.
    """
    if not is_typesafe_enabled():
        return None
    try:
        current_traits = (previous_profile or {}).get("core_traits", {}) or {}
        recent = interaction_log[-6:] if interaction_log else []
        convo = "\n".join(f"{m.get('role', '?')}: {m.get('content', '')}" for m in recent)
        actions = "\n".join(f"- {a}" for a in (player_actions_summary or []))
        traits_txt = ", ".join(f"{t}={current_traits.get(t, 5)}" for t in PROFILE_TRAITS)
        state = {
            "recent_conversation": convo[:3000] or "(no conversation yet)",
            "player_actions": actions[:1500] or "(no recorded actions)",
            "current_traits_1_to_10": traits_txt,
            "current_npc": current_npc_name or "unknown",
            "current_leaning": (previous_profile or {}).get("philosophical_leaning", "neutral"),
            "current_veil": (previous_profile or {}).get("veil_perception", "neutral_curiosity"),
        }
        questions: Dict[str, Any] = {
            f"trait_{t}": {"type": "score", "instructions": f"{TRAIT_INSTRUCTIONS[t]}. Judge ONLY what the player showed in THIS interaction.",
                           "criteria": TRAIT_LEVELS}
            for t in PROFILE_TRAITS
        }
        questions["leaning"] = {
            "type": "choice",
            "instructions": "The player's philosophical alignment shown in THIS interaction (pro-Oblivion vs pro-Veil vs neither)",
            "criteria": LEANING_CHOICES,
        }
        questions["veil"] = {
            "type": "choice",
            "instructions": "The player's attitude toward the Veil shown in THIS interaction",
            "criteria": VEIL_CHOICES,
        }
        answers, meta = system_one(state, questions)
        if not answers:
            return None

        out: Dict[str, Any] = {"provider": "typesafe", "elapsed_ms": meta.get("elapsed_ms")}
        adjustments: Dict[str, float] = {}
        for t in PROFILE_TRAITS:
            ans = answers.get(f"trait_{t}") or {}
            if "score" not in ans:
                continue
            target = _score_to_trait_value(ans["score"])
            try:
                current = float(current_traits.get(t, 5))
            except (TypeError, ValueError):
                current = 5.0
            delta = round(target - current, 1)
            if abs(delta) >= TRAIT_NOISE_GATE:
                # applier adds the adjustment to the current value
                adjustments[t] = delta
        if adjustments:
            out["trait_adjustments"] = adjustments

        leaning = answers.get("leaning") or {}
        if (leaning.get("choice") in LEANING_CHOICES
                and float(leaning.get("confidence", 0) or 0) >= CATEGORICAL_CONF_THRESHOLD):
            out["updated_philosophical_leaning"] = leaning["choice"]

        veil = answers.get("veil") or {}
        if (veil.get("choice") in VEIL_CHOICES
                and float(veil.get("confidence", 0) or 0) >= CATEGORICAL_CONF_THRESHOLD):
            out["updated_veil_perception"] = veil["choice"]

        out["analysis_notes"] = (
            f"[TypeSafe] scored {len(adjustments)} trait(s), "
            f"leaning={out.get('updated_philosophical_leaning', 'unchanged')}, "
            f"veil={out.get('updated_veil_perception', 'unchanged')}"
        )
        return out
    except Exception as e:
        logger.warning(f"[TypeSafe] profile scoring failed: {e}")
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("enabled:", is_typesafe_enabled(), "| model:", get_model())
    ans, meta = system_one("vado in taverna", {"t": {"type": "noul", "instructions": "Does the player want to move to another area?"}})
    print("meta:", meta)
    print("answers:", ans)
