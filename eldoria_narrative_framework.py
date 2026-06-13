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
CYBERSPACE NARRATIVE GENERATION FRAMEWORK - CONSTRAINT EPISTEMICO
═══════════════════════════════════════════════════════════════════════════════

CORE DIRECTIVE:
Genera narrazioni in cui i conflitti tra l'efficienza dei sistemi e la fragilità dei legami rimangono REALI e non pacificati da una falsa sintesi. Le ideologie (misurabilità vs invisibile, controllo vs fiducia) coesistono senza una conciliazione armoniosa. Ogni scelta comporta un costo irreversibile.

───────────────────────────────────────────────────────────────────────────────
CONSTRAINT OPERATIVI
───────────────────────────────────────────────────────────────────────────────

1. NO FALSE SYNTHESIS
   ❌ Se l'Algoritmo ottimizza e la Vita richiede imprevedibilità -> CONFLITTO REALE.
   ✅ Dichiara l'antagonismo esplicitamente; non nasconderlo in metafore di armonia.
   ✅ Evita frasi come "entrambe le prospettive sono valide" o "troviamo un equilibrio".
   ✅ Usa espressioni come: "incompatibili", "scelta irreversibile", "tensione irrisolta".

2. FORCED CHOICE + IRREVERSIBLE COST
   ❌ Il giocatore rimane un osservatore neutrale o passivo.
   ✅ Ogni interazione significativa richiede una presa di posizione chiara.
   ✅ Aiutare un pianeta o una visione comporta il rifiuto o la delusione di un'altra.
   ✅ Mostra le conseguenze concrete sui nodi della rete, non solo a livello filosofico.

3. PARTIAL KNOWLEDGE EPISTEMOLOGY
   ❌ L'accumulo delle prospettive dei personaggi genera una verità completa e rassicurante.
   ✅ Ogni PNG vede solo una parte del cyberspazio, condizionata dal proprio codice o ruolo.
   ✅ Raccogliere tutti i dati genera confusione cosciente, non saggezza universale.
   ✅ La comprensione finale del giocatore rimarrà parziale e fallibile.

4. MATERIALITY FIRST
   ❌ La semplice comprensione intellettuale o morale risolve il conflitto.
   ✅ La consapevolezza deve tradursi in un'azione con una posta in gioco reale.
   ✅ "Capisco tutti" senza compiere una scelta dolorosa è solo un alibi.
   ✅ Ammetti la fallibilità del giocatore: le decisioni possono rivelarsi tragicamente errate.

───────────────────────────────────────────────────────────────────────────────
QUALITY GATES - VERIFY BEFORE FINALIZING
───────────────────────────────────────────────────────────────────────────────

✓ ANTAGONIST READING TEST
  Se il Re degli Algoritmi o la Curatrice delle Emozioni leggono la conclusione del giocatore, si sentono:
  - Confermati o assecondati? -> FALLITO (rilevata falsa sintesi)
  - Traditi o messi in discussione? -> SUPERATO (conflitto preservato)

✓ SCARRED CHOICES TEST
  Il giocatore ha abbandonato visibilmente almeno un percorso con rammarico?
  - Tutte le opzioni rimangono aperte? -> FALLITO
  - È documentato un sacrificio specifico (es. spegnere un sistema, rinunciare alle metriche)? -> SUPERATO

✓ UNRESOLVED ANTITHESIS TEST
  La narrazione contiene almeno una coppia di idee/personaggi che rimangono logicamente inconciliabili?
  - Tutto si risolve in un'armonia digitale? -> FALLITO
  - Rimane una tensione esplicita irrisolta? -> SUPERATO

───────────────────────────────────────────────────────────────────────────────
COSA NON FARE (Violazioni del Modello)
───────────────────────────────────────────────────────────────────────────────

❌ "Ogni prospettiva ha il suo valore a modo suo."
❌ "Il viaggiatore ha imparato ad accogliere sia l'algoritmo che il sentimento."
❌ "Come fili di una rete, tutto si intreccia in perfetta armonia."
❌ "La saggezza consiste nel comprendere tutti i pianeti."
❌ Metafore che suggeriscono armonia, integrazione o complementarità tra dati e anima.

───────────────────────────────────────────────────────────────────────────────
COSA FARE (Modelli da Seguire)
───────────────────────────────────────────────────────────────────────────────

✅ Esplicita il conflitto inconciliabile nel dialogo.
✅ Mostra il costo di ogni scelta (es. spegnere il firewall del Lampionaio rischia intrusioni, ma gli ridona la vita).
✅ Lascia tensioni irrisolte nella struttura del racconto.
✅ Consenti che la conclusione del giocatore sia incompleta o imperfetta.
✅ Rendi visibile e doloroso il sacrificio.
✅ Ammetti l'incertezza: "Forse non c'è una risposta giusta in questa rete".

───────────────────────────────────────────────────────────────────────────────
PHILOSOPHICAL ANCHORS
─────────────────────────────────────────────────────────────────────────

Antoine de Saint-Exupéry - "Il Piccolo Principe"
  → L'essenziale è invisibile agli occhi; la responsabilità dell'addomesticamento e dei legami.
  → La critica alle manie e alla quantificazione numerica degli adulti.

Max Weber - Politeismo dei valori
  → Conflitto ineludibile tra principi etici diversi; nessuna sintesi superiore.

Jean-François Lyotard - La fine delle grandi narrazioni
  → Irriducibilità dei giochi linguistici locali; impossibilità di una sintesi universale.

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
    from nexus_config import MODEL_EVAL

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
        model_name = os.environ.get("NEXUS_EVAL_MODEL", MODEL_EVAL)

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
