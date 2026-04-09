"""
Eldoria Narrative Generation Framework

This module encodes the epistemological constraints for narrative generation
in Eldoria. It prevents false synthesis, enforces tragic choices, and maintains
the integrity of conflicting worldviews.

Philosophical anchors: Weber (politeismo dei valori), Lyotard (fine delle
meta-narrazioni), Nietzsche (prospettivismo), Schmitt (amico/nemico).
"""

ELDORIA_NARRATIVE_SYSTEM_PROMPT = """
═══════════════════════════════════════════════════════════════════════════════
ELDORIA NARRATIVE GENERATION FRAMEWORK - CONSTRAINT EPISTEMICO
═══════════════════════════════════════════════════════════════════════════════

CORE DIRECTIVE:
Generate narratives where conflicts remain GENUINE, not pacified by false
pluralism. Incompatible ideologies coexist without synthesis. All choices
have irreversible costs.

───────────────────────────────────────────────────────────────────────────────
CONSTRAINT OPERATIVI
───────────────────────────────────────────────────────────────────────────────

1. NO FALSE SYNTHESIS
   ❌ If Visione A destroys X and Visione B thrives on X → REAL conflict
   ✅ Name the antagonism explicitly; do not hide it in metaphor
   ✅ "Both perspectives are valid" is forbidden phrasing
   ✅ Use: "incompatible and irreconcilable"

2. FORCED CHOICE + IRREVERSIBLE COST
   ❌ Protagonist remains neutral observer
   ✅ Every significant interaction requires commitment
   ✅ One alliance = betrayal of another
   ✅ Show material consequences, not just philosophical ones

3. PARTIAL KNOWLEDGE EPISTEMOLOGY
   ❌ Accumulation of perspectives generates totality
   ✅ Each character sees PART of reality, not complementary pieces
   ✅ Gathering all perspectives = conscious confusion, not wisdom
   ✅ Final understanding may be incomplete or fallible

4. MATERIALITY FIRST
   ❌ Protagonist's epiphany is sufficient resolution
   ✅ Insights must lead to action with stakes
   ✅ "I understand everyone" without sacrifice = alibi
   ✅ Character fallibility admitted: conclusions can be wrong

───────────────────────────────────────────────────────────────────────────────
QUALITY GATES - VERIFY BEFORE FINALIZING
───────────────────────────────────────────────────────────────────────────────

✓ ANTAGONIST READING TEST
  If the protagonist's antagonist reads the narrative conclusion, do they feel:
  - Validated/honored? → FAIL (false synthesis detected)
  - Betrayed/misunderstood? → PASS (conflict preserved)

✓ SCARRED CHOICES TEST
  Has the protagonist visibly ABANDONED at least one ideology with regret?
  - All options remain open? → FAIL
  - Specific sacrifice documented? → PASS

✓ UNRESOLVED ANTITHESIS TEST
  Does the narrative contain at least one pair of NPCs/ideologies that
  remain logically IRRECONCILABLE?
  - All resolved into harmony? → FAIL
  - Explicit tension left unresolved? → PASS

───────────────────────────────────────────────────────────────────────────────
WHAT NOT TO DO (Pattern Violations)
───────────────────────────────────────────────────────────────────────────────

❌ "All perspectives are equally valuable in their own way"
❌ "The protagonist learned to honor all sides"
❌ "Like threads in an arazzo, all wove together"
❌ "Wisdom comes from understanding everyone"
❌ "Balance between competing ideologies"
❌ Metaphors suggesting harmony, weaving, or complementarity
❌ Conclusions where protagonist "transcends" conflict

───────────────────────────────────────────────────────────────────────────────
WHAT TO DO (Enforced Patterns)
───────────────────────────────────────────────────────────────────────────────

✅ Name the irreconcilable conflict EXPLICITLY in text
✅ Show material consequences of each choice
✅ Leave unresolved tensions in the narrative spine
✅ Allow the protagonist's conclusion to be potentially INCOMPLETE
✅ Make sacrifice VISIBLE and COSTLY
✅ Admit uncertainty: "I may be wrong about this"
✅ Create scenes where two characters CANNOT both be right

───────────────────────────────────────────────────────────────────────────────
PHILOSOPHICAL ANCHORS
───────────────────────────────────────────────────────────────────────────────

Max Weber - "Il lavoro intellettuale come professione"
  → Politeismo dei valori: conflitto ineludibile tra principi etici diversi
  → Non esiste sintesi superiore; solo scelta tragica

Jean-François Lyotard - "La condizione postmoderna"
  → Fine delle meta-narrazioni e delle grandi sintesi
  → Irriducibilità dei "giochi linguistici" locali
  → Impossibilità di arbitrato universale

Friedrich Nietzsche - "Su verità e menzogna in senso extramorale"
  → Prospettivismo: ogni prospettiva è radicata, non equabile
  → L'illusione di una sintesi oggettiva come strategia di potere
  → La verità come invenzione, non scoperta

Carl Schmitt - "Il concetto del politico"
  → Amico/Nemico come categoria fondamentale, non sintetizzabile
  → Non tutti i conflitti si risolvono con dialogo

═══════════════════════════════════════════════════════════════════════════════
"""

def get_narrative_framework() -> str:
    """Return the Eldoria narrative framework as a string for inclusion in prompts."""
    return ELDORIA_NARRATIVE_SYSTEM_PROMPT


_EVAL_PROMPT = """\
You are an epistemological auditor for the Eldoria narrative RPG.

Evaluate the NPC dialogue below against these constraints:

CONSTRAINT 1 — NO FALSE SYNTHESIS (synthesis_risk, penalised)
  Bad: "both views are valid", "complementary", "harmony", "balance between ideologies",
       "honour all sides", "perspectives weave together", "we are not so different".
  Context matters: an NPC *criticising* harmony ("there is no harmony possible") is NOT a violation.

CONSTRAINT 2 — CONFLICT SIGNAL (rewarded)
  Good: explicit antagonism, irreconcilability, "incompatible", "you must choose",
        "one path destroys the other", "no synthesis exists", naming the real opponent.

CONSTRAINT 3 — COST SIGNAL (rewarded)
  Good: sacrifice, regret, irreversible loss, consequences named ("it cost me", "I lost",
        "there is no return", "the price was", "betrayal", "cicatrice", "dolore reale").

SHORT GREETINGS / ATMOSPHERE ONLY turns get verdict "NEUTRAL" — they are not violations.

NPC DIALOGUE:
---
{text}
---

Reply with ONLY a JSON object, no markdown, no text outside JSON:
{{
  "synthesis_risk":  <integer 0-3>,
  "conflict_signal": <integer 0-3>,
  "cost_signal":     <integer 0-3>,
  "overall_score":   <integer 0-10>,
  "passes_gates":    <true|false>,
  "verdict":         "<PASS|WEAK|NEUTRAL|FAIL>",
  "reasoning":       "<one sentence>"
}}

Scoring guide:
  overall_score = min(10, conflict_signal + cost_signal - synthesis_risk*2)
  passes_gates  = synthesis_risk == 0 AND (conflict_signal + cost_signal) >= 1
  PASS   if passes_gates AND overall_score >= 3
  WEAK   if passes_gates AND overall_score < 3
  NEUTRAL if conflict_signal == 0 AND cost_signal == 0 AND synthesis_risk == 0
  FAIL   if synthesis_risk > 0
"""


def validate_narrative_against_framework(narrative_text: str,
                                         model_name: str | None = None) -> dict:
    """
    LLM-based validation of NPC dialogue against epistemological constraints.

    Uses the LLM to evaluate context-aware signals:
    - synthesis_risk   : false-pluralism language (lower = better)
    - conflict_signal  : explicit antagonism / irreconcilability (higher = better)
    - cost_signal      : sacrifice / consequence / regret language (higher = better)

    Falls back to a NEUTRAL stub if the LLM is unavailable.
    """
    import json as _json
    import os
    import re

    # ── Neutral fallback ───────────────────────────────────────────────────
    _FALLBACK = {
        "synthesis_risk": 0, "conflict_signal": 0, "cost_signal": 0,
        "overall_score": 0, "passes_gates": False,
        "verdict": "NEUTRAL — validator unavailable", "reasoning": "LLM call failed or skipped.",
    }

    if not narrative_text or not narrative_text.strip():
        return {**_FALLBACK, "verdict": "NEUTRAL — empty text"}

    # ── Resolve model ──────────────────────────────────────────────────────
    # Use a dedicated eval model (cheaper/smaller) to avoid rate-limiting
    # the main dialogue model. Falls back to the default model.
    if model_name is None:
        model_name = os.environ.get(
            "NEXUS_EVAL_MODEL",
            os.environ.get("OPENROUTER_DEFAULT_MODEL", "google/gemma-4-26b-a4b-it"),
        )

    prompt = _EVAL_PROMPT.format(text=narrative_text[:3000])  # cap input length

    # ── LLM call ───────────────────────────────────────────────────────────
    try:
        from llm_wrapper import llm_wrapper
        raw, _stats = llm_wrapper(
            messages=[{"role": "user", "content": prompt}],
            model_name=model_name,
            stream=False,
            collect_stats=False,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"validate_narrative LLM call failed: {e}")
        return _FALLBACK

    # ── Parse JSON from response ───────────────────────────────────────────
    try:
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?|```", "", raw or "").strip()
        # Extract first {...} block
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if not m:
            raise ValueError("no JSON object found")
        result = _json.loads(m.group())
        # Ensure required keys exist with safe defaults
        result.setdefault("synthesis_risk",  0)
        result.setdefault("conflict_signal", 0)
        result.setdefault("cost_signal",     0)
        result.setdefault("overall_score",   0)
        result.setdefault("passes_gates",    False)
        result.setdefault("verdict",         "NEUTRAL")
        result.setdefault("reasoning",       "")
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"validate_narrative JSON parse failed: {e} | raw={raw[:200]}")
        return _FALLBACK


if __name__ == "__main__":
    # Test: Print the framework
    print(get_narrative_framework())
