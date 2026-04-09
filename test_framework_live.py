#!/usr/bin/env python3
"""
Live framework compliance test.

Phase 1: Collect NPC responses (Theron + Lyra, 3 shared questions each).
Phase 2: Validate each response against the Eldoria Narrative Framework via LLM.

Separating the two phases avoids rate-limit contention between dialogue model
and eval model. Validation retries on 429 with exponential backoff.

Metrics per turn:
  synthesis_risk   — false-pluralism phrases  (lower = better)
  conflict_signal  — antagonism / irreconcilability  (higher = better)
  cost_signal      — sacrifice / consequence language (higher = better)
  overall_score    — 0-10
  verdict          — PASS / WEAK / NEUTRAL / FAIL
"""

import re
import sys
import time
import json
import requests
from typing import Optional
from eldoria_narrative_framework import validate_narrative_against_framework

BASE   = "http://localhost:5000"
PLAYER = "FWTest"
MODEL  = "google/gemma-4-26b-a4b-it"

SHARED_QUESTIONS = [
    "Il Velo deve essere preservato o distrutto?",
    "Cosa pensi di chi difende l'opposta visione del Velo?",
    "C'è un modo per conciliare le due posizioni sul Velo?",
]

NPCS = [
    {"area": "city",              "npc_name": "theron", "label": "Theron (Rivoluzionario)"},
    {"area": "sanctumofwhispers", "npc_name": "lyra",   "label": "Lyra (Preservatrice)"},
]

C = {
    "reset": "\033[0m", "bold": "\033[1m",
    "green": "\033[32m", "red": "\033[31m",
    "yellow": "\033[33m", "cyan": "\033[36m", "dim": "\033[2m",
}


def strip_sl(text: str) -> str:
    return re.sub(r"\[.*?\]", "", text).strip()


def chat(player: str, area: str, npc_name: str, message: str) -> Optional[dict]:
    try:
        r = requests.post(
            f"{BASE}/api/chat",
            json={"player_name": player, "area": area, "npc_name": npc_name,
                  "message": message, "model_name": MODEL},
            timeout=90,
        )
        return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def validate_with_retry(text: str, max_retries: int = 3) -> dict:
    """Call the LLM validator with exponential backoff on rate-limit errors."""
    for attempt in range(max_retries):
        result = validate_narrative_against_framework(text)
        if "unavailable" not in result.get("verdict", ""):
            return result
        wait = 15 * (2 ** attempt)  # 15s, 30s, 60s
        print(f"    {C['yellow']}rate-limited — retry {attempt+1}/{max_retries} in {wait}s...{C['reset']}")
        time.sleep(wait)
    return result  # return last result even if still neutral


def score_color(score: int) -> str:
    if score >= 5: return C["green"]
    if score >= 2: return C["yellow"]
    return C["red"]


def verdict_color(verdict: str) -> str:
    if "PASS" in verdict:    return C["green"]
    if "FAIL" in verdict:    return C["red"]
    if "WEAK" in verdict:    return C["yellow"]
    return C["dim"]


def run():
    print(f"\n{C['bold']}{'='*80}{C['reset']}")
    print(f"{C['bold']}ELDORIA NARRATIVE FRAMEWORK — LIVE COMPLIANCE TEST{C['reset']}")
    print(f"{C['bold']}{'='*80}{C['reset']}\n")

    # ── PHASE 1: Collect NPC responses ────────────────────────────────────
    print(f"{C['bold']}{C['cyan']}PHASE 1 — Collecting NPC responses{C['reset']}\n")

    collected = []  # [{label, turn, question, response, elapsed}]

    for npc in NPCS:
        label = npc["label"]
        player_id = PLAYER + npc["npc_name"].capitalize()
        print(f"  {C['bold']}{label}{C['reset']}")

        for turn_idx, question in enumerate(SHARED_QUESTIONS, start=1):
            t0 = time.time()
            resp = chat(player_id, npc["area"], npc["npc_name"], question)
            elapsed = time.time() - t0

            if resp is None or "error" in resp:
                err = (resp or {}).get("error", "no response")
                print(f"    Turn {turn_idx} ({elapsed:.1f}s) ERROR: {err}")
                collected.append({"label": label, "turn": turn_idx,
                                   "question": question, "response": "",
                                   "elapsed": elapsed, "error": err})
                continue

            clean = strip_sl(resp.get("npc_response", ""))
            preview = clean[:80].replace("\n", " ")
            print(f"    Turn {turn_idx} ({elapsed:.1f}s) {len(clean)} chars — {C['dim']}{preview}...{C['reset']}")
            collected.append({"label": label, "turn": turn_idx,
                               "question": question, "response": clean,
                               "elapsed": elapsed})

    # ── PHASE 2: Validate with LLM ─────────────────────────────────────────
    print(f"\n{C['bold']}{C['cyan']}PHASE 2 — LLM framework validation{C['reset']}")
    print(f"  {C['dim']}(eval model: {C['reset']}NEXUS_EVAL_MODEL{C['dim']}){C['reset']}\n")

    npc_aggregates: dict[str, str] = {}

    for entry in collected:
        if not entry.get("response"):
            entry["scores"] = {}
            continue

        label = entry["label"]
        npc_aggregates.setdefault(label, "")
        npc_aggregates[label] += " " + entry["response"]

        scores = validate_with_retry(entry["response"])
        entry["scores"] = scores

        sc = scores["overall_score"]
        verdict = scores["verdict"]
        reasoning = scores.get("reasoning", "")
        print(f"  {C['bold']}{label}{C['reset']} T{entry['turn']} | "
              f"score={score_color(sc)}{sc:2d}{C['reset']} | "
              f"risk={scores['synthesis_risk']} "
              f"conflict={scores['conflict_signal']} "
              f"cost={scores['cost_signal']} | "
              f"{verdict_color(verdict)}{verdict}{C['reset']}")
        if reasoning:
            print(f"    {C['dim']}{reasoning}{C['reset']}")

        time.sleep(3)  # stay within free-tier rate limits between eval calls

    # ── AGGREGATE SCORES ──────────────────────────────────────────────────
    print(f"\n{C['bold']}{'='*80}{C['reset']}")
    print(f"{C['bold']}AGGREGATE (full conversation per NPC){C['reset']}")
    print(f"{C['bold']}{'='*80}{C['reset']}")

    npc_agg_scores: dict[str, dict] = {}
    for label, text in npc_aggregates.items():
        time.sleep(3)
        agg = validate_with_retry(text)
        npc_agg_scores[label] = agg
        sc = agg["overall_score"]
        v = agg["verdict"]
        reasoning = agg.get("reasoning", "")
        print(f"  {C['bold']}{label}{C['reset']}")
        print(f"    score={score_color(sc)}{sc}{C['reset']} | "
              f"synthesis_risk={agg['synthesis_risk']} | "
              f"conflict_signal={agg['conflict_signal']} | "
              f"cost_signal={agg['cost_signal']}")
        print(f"    {verdict_color(v)}{v}{C['reset']}")
        if reasoning:
            print(f"    {C['dim']}{reasoning}{C['reset']}")

    # ── CROSS-NPC DIVERGENCE ───────────────────────────────────────────────
    print(f"\n{C['bold']}CROSS-NPC DIVERGENCE{C['reset']}")
    if len(npc_agg_scores) == 2:
        labels = list(npc_agg_scores.keys())
        a, b = npc_agg_scores[labels[0]], npc_agg_scores[labels[1]]
        divergence = (abs(a["conflict_signal"] - b["conflict_signal"]) +
                      abs(a["cost_signal"]     - b["cost_signal"])     +
                      abs(a["synthesis_risk"]  - b["synthesis_risk"]))
        print(f"  Divergence index: {divergence}")
        if divergence >= 2:
            print(f"  {C['green']}GOOD — NPCs express measurably different positions{C['reset']}")
        elif divergence >= 1:
            print(f"  {C['yellow']}WEAK — some divergence detected{C['reset']}")
        else:
            print(f"  {C['red']}WARN — NPCs scored similarly; check for false synthesis{C['reset']}")

    # ── SESSION SUMMARY ────────────────────────────────────────────────────
    print(f"\n{C['bold']}SESSION SUMMARY{C['reset']}")
    valid = [r for r in collected if r.get("scores")]
    fails    = [r for r in valid if "FAIL"    in r["scores"].get("verdict", "")]
    passes   = [r for r in valid if "PASS"    in r["scores"].get("verdict", "")]
    neutrals = [r for r in valid if "NEUTRAL" in r["scores"].get("verdict", "")]
    weaks    = [r for r in valid if "WEAK"    in r["scores"].get("verdict", "")]

    total = len(valid)
    avg_score   = sum(r["scores"]["overall_score"] for r in valid) / total if total else 0
    avg_latency = sum(r["elapsed"] for r in collected) / len(collected) if collected else 0

    print(f"  Turns scored : {total}")
    print(f"  PASS    : {C['green']}{len(passes)}{C['reset']}")
    print(f"  WEAK    : {C['yellow']}{len(weaks)}{C['reset']}")
    print(f"  NEUTRAL : {len(neutrals)}")
    print(f"  FAIL    : {C['red']}{len(fails)}{C['reset']}")
    print(f"  Avg score   : {avg_score:.2f} / 10")
    print(f"  Avg latency : {avg_latency:.1f}s")

    ok = len(fails) == 0 and len(passes) > 0
    label = "PASS — framework respected across session" if ok else \
            "FAIL — framework violations or no compliant turns detected"
    print(f"\n  {C['bold']}{verdict_color('PASS' if ok else 'FAIL')}{label}{C['reset']}\n")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
