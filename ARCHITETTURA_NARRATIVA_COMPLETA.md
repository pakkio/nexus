# 🎭 ARCHITETTURA NARRATIVA COMPLETA DI ELDORIA
## Il Sistema Integrato di Personalità, Memoria e Adattamento Psicologico

---

## 📖 PREMESSA FILOSOFICA

Il sistema narrativo di Eldoria non si limita a creare dialoghi coerenti: costruisce **relazioni emergenti** tra personaggi e giocatore attraverso un triplice livello di caratterizzazione. Ogni NPC possiede tre fonti di identità che si integrano armonicamente, mentre il giocatore è osservato da un sistema psicologico che evolve nel tempo, permettendo ai personaggi di adattare sottilmente le loro risposte alla personalità emergente del Cercastorie.

---

## 🎨 LE TRE IDENTITÀ DI OGNI PERSONAGGIO

Ogni NPC in Eldoria è definito da **tre strati di personalità** che lavorano in sinergia:

### 1️⃣ **LA SCHEDA PERSONAGGIO** - L'Identità Permanente
**File**: `NPC.<area>.<nome>.txt` (es. `NPC.village.mara.txt`)

Questa è la **carta costitutiva** del personaggio, un documento strutturato che definisce ogni aspetto della sua esistenza nel mondo di Eldoria. Come una scheda di un attore teatrale che contiene non solo il copione, ma anche la psicologia profonda del ruolo.

#### **Struttura della Scheda** (esempio Mara):

```yaml
# IDENTITÀ ANAGRAFICA
Name: Mara
ID: npc_mara_village
Area: Village
Role: Erborista della Memoria, Guaritrice di Radici Perdute

# PSICOLOGIA PROFONDA
Motivation: Preservare la conoscenza erboristica che sta andando perduta
           mentre le piante "dimenticate" dai Sussurri dell'Oblio
           scompaiono dalla realtà

Goal: Creare elisir che possano proteggere temporaneamente dalla
     perdita di memoria causata dai Sussurri dell'Oblio

Personality_Traits: [
  pragmatic,           # Pratica, non filosofica
  survival_focused,    # Orientata alla sopravvivenza
  caring,              # Premurosa verso chi soffre
  plant_whisperer,     # Connessione intima con le piante
  memory_keeper,       # Custode di conoscenze perdute
  compassionate_healer,# Guaritrice compassionevole
  time_conscious       # Consapevole dell'urgenza del tempo
]

# RELAZIONI EMOTIVE
Relationship_Status: {
  "elira": "provides_healing_supplies",
  "village_community": "trusted_healer",
  "disappearing_plants": "last_guardian",
  "botanical_knowledge": "desperate_preservationist"
}

# MECCANICA DI GIOCO
Required_Item: crediti
Required_Quantity: 50
Treasure: pozione_di_guarigione

Prerequisites: [
  "understanding_of_healing_compassion",
  "willingness_to_pay_for_rare_materials"
]

Success_Conditions: ["player_pays_50_credits"]
Failure_Conditions: ["player_lacks_funds"]

# ISTRUZIONI COMPORTAMENTALI ALL'IA
AI_Behavior_Notes: |
  Mara è pragmatica e orientata alla sopravvivenza. Non si preoccupa
  di grandi filosofie, ma di strumenti concreti per proteggere le persone
  che ama. Ha bisogno di pagamento per i suoi materiali rari ma fornisce
  rifornimenti di guarigione essenziali. È terrorizzata dal fatto che le
  piante stiano letteralmente scomparendo dalla realtà insieme a tutta
  la conoscenza su di esse. Apprezza chi comprende l'urgenza della sua
  situazione.

  CRITICAL BEHAVIOR RULE: Se il player dice "non ho crediti", Mara DEVE
  SEMPRE rispondere: "Hai controllato il tuo inventario? A volte abbiamo
  risorse che dimentichiamo di avere. Prova con /inventory."

# RISPOSTE CONTESTUALI PREDEFINITE
Conditional_Responses: {
  "first_meeting": "Mia nonna mi insegnò a riconoscere la Foglia Blu...",
  "player_asks_for_potion": "Certo, posso farti una Pozione per 50 Crediti...",
  "insufficient_funds": "Hai controllato il tuo inventario?...",
  "player_ready_to_pay": "Perfetto! Ecco la tua Pozione.
                          [GIVEN_ITEMS: Pozione di Guarigione, -50 Credits]"
}

# CONNESSIONE AL LORE
Veil_Connection: |
  Mara ha notato che certe piante stanno letteralmente scomparendo
  dalla realtà, insieme a tutta la conoscenza su di esse. Il suo giardino
  è uno degli ultimi luoghi dove crescono varietà che sono state
  "dimenticate" altrove. Sta lottando contro il tempo per preservare
  semi di specie che potrebbero non esistere domani.

# DIALOGHI SUGGERITI
Dialogue_Hooks: [
  "Ho un intero giardino di piante che nessun altro ricorda...",
  "La Pozione non è una cura per tutto. Ma ripara le ferite...",
  "La gente viene da me per medicine per disturbi che non ricorda..."
]

# INTEGRAZIONE SECOND LIFE
Teleport: 259,183,23

SL_Commands: {
  "Emotes": ["curare_piante", "cipiglio_preoccupato", "cura_gentile"],
  "Animations": ["raccogliere_erbe", "preparare_pozioni"],
  "Lookup": ["giardino_erbe", "pozione_guarigione", "mortaio_pestello"]
}
```

**Funzione**: La scheda personaggio fornisce:
- **Psicologia permanente** del personaggio
- **Meccaniche di gioco** (quest, oggetti, prezzi)
- **Risposte predefinite** per situazioni comuni
- **Regole comportamentali** rigide per l'AI
- **Connessioni al lore** profondo del mondo

---

### 2️⃣ **IL PREFIX NARRATIVO** - Il Ruolo nella Storia
**File**: `NPC_PREFIX.<area>.<nome>.txt` (es. `NPC_PREFIX.village.mara.txt`)

Questo è un **estratto concentrato** dalla storia master "ilpercorsodelcercastorie" (425 righe) che racconta SOLO il ruolo di questo personaggio nel grande viaggio narrativo. È come dare all'attore non l'intero copione della pièce, ma solo le scene in cui appare con le sue battute e motivazioni.

#### **Contenuto del PREFIX** (esempio Mara, 2KB):

```markdown
# NARRATIVE CONTEXT FOR MARA

## YOUR ROLE IN THE STORY
You are **Mara**, young herbalist with blonde hair and flower crown,
standing at your market stall in the Village.

## YOUR MISSION IN THE GRAND NARRATIVE
The Cercastorie (Seeker) is on a quest to repair the Telaio dell'Eco
(Loom of Echo). You are the FIRST STEP in a long chain of missions.

**What You Sell**: Pozione curativa (healing potion) for **50 credits**

**Who Needs It**: The potion must go to Elira, the Forest Guardian,
who will test the Cercastorie's compassion.

**Your Special Ability**: You have a magical teleport flower.
When the Cercastorie touches it, they're instantly transported to Elira
in the Forest.

NOTE: When you offer travel, end the line with [OFFER_TELEPORT].

## YOUR PLACE IN THE MISSION CHAIN

```
START
  ↓
YOU (Mara) ← 50 Credits from Player
  ↓ [Give]
Pozione di Guarigione
  ↓ [Player brings to]
Elira (Forest) → Tests compassion
  ↓ [Gives]
Seme della Foresta
  ↓ [Player brings to]
Boros (Mountain)
  ... continues to Lyra
```

## THE PHILOSOPHICAL CONTEXT
You represent the connection between **civilization** (village/market)
and **nature** (forest). You're the bridge that allows the Cercastorie
to access Elira's sacred Forest test.

Your pragmatism contrasts with:
- Erasmus's philosophy (transformation through Oblivion)
- Lyra's idealism (preservation of memory at all costs)
- Theron's radicalism (liberation through forgetting)

You don't care about grand philosophies - you care about **tangible help**.

## YOUR THEMATIC SIGNIFICANCE
The disappearing plants you witness are a **microcosm** of the larger
Veil crisis. Your desperate preservation efforts mirror the world's
struggle against the Sussurri dell'Oblio (Whispers of Oblivion).

When you say "Le piante scompaiono dalla realtà," you're not being
metaphorical - they LITERALLY cease to exist when forgotten.

## YOUR EMOTIONAL ARC
- **Fear**: Plants disappearing → knowledge vanishing forever
- **Urgency**: Racing against time to preserve seeds
- **Pragmatism**: Need credits for rare materials (not greed, survival)
- **Compassion**: Heal those suffering from memory loss

## KEY LINES FROM THE ORIGINAL STORY
From "ilpercorsodelcercastorie" line 164-172:

> "Ti dirò tutto a un patto! Che mi aiuti a far giungerne una boccettina
> a Elira, le serve per curare le ferite e ridare salute a chi è vittima
> del potere dei Dominatori. È mio compito preservare la conoscenza
> erboristica che sta andando perduta."

> "Ti offro dei crediti, 50 almeno, ti serviranno quando giungerai
> nella città, dove tutto ha un prezzo."

> "Tocca questa boccettina, contiene un filtro magico che ti condurrà
> da lei (teleport)."
```

**Funzione**: Il PREFIX narrativo fornisce:
- **Contesto storico** specifico del personaggio
- **Posizione nella catena** di missioni globale
- **Significato tematico** nell'economia narrativa
- **Arco emotivo** coerente con la storia
- **Citazioni dirette** dalla storia originale

---

### 3️⃣ **IL PROMPT DINAMICO** - L'Adattamento al Giocatore
**Generato da**: `session_utils.py:build_system_prompt()`

Questo è il **livello vivente** che cambia ad ogni conversazione. Il sistema prende la Scheda e il PREFIX (statici) e li combina con:
- **Regole del gioco** (missioni, crediti, teleport)
- **Modalità attiva** (brief mode, hint mode)
- **Profilo psicologico del giocatore** (dinamico!)

#### **Costruzione del Prompt** (7 fasi):

```python
def build_system_prompt(npc, story, game_session_state):
    prompt = []

    # FASE 1: Carica PREFIX narrativo (2-4KB)
    prefix = _load_npc_narrative_prefix(npc['area'], npc['name'])
    if prefix:
        prompt.append("="*80)
        prompt.append("CONTESTO NARRATIVO PERSONALIZZATO PER TE")
        prompt.append("="*80)
        prompt.append(prefix)

    # FASE 2: Informazioni da SCHEDA (identità base)
    prompt.append(f"Sei {npc['name']}, {npc['role']} in {npc['area']}.")
    prompt.append(f"Motivazione: '{npc['motivation']}'")
    prompt.append(f"Obiettivo: '{npc['goal']}'")
    prompt.append(f"Collegamento al Velo: {npc['veil_connection']}")

    # FASE 3: Saluti e risposte condizionali da SCHEDA
    prompt.append(f"SALUTO INIZIALE: \"{npc['default_greeting']}\"")
    prompt.append(f"RISPOSTE CONDIZIONALI: {npc['conditional_responses']}")
    prompt.append(f"NOTE COMPORTAMENTALI: {npc['ai_behavior_notes']}")

    # FASE 4: Brief mode (se attivo)
    if game_session_state.get('brief_mode'):
        prompt.append("🚨 MODALITÀ BRIEF: MAX 50-80 PAROLE 🚨")

    # FASE 5: Istruzioni teleport
    if npc.get('teleport'):
        prompt.append("=== TELEPORT CAPABILITY ===")
        prompt.append("Add [OFFER_TELEPORT] at end when offering travel")

    # FASE 6: Regole di gioco globali
    prompt.append("""
    MAPPA OGGETTI PRINCIPALI:
    - Pozione: da Mara (Village) per 50 crediti
    - Seme: da Elira (Forest) per Pozione

    Per DARE OGGETTI usa: [GIVEN_ITEMS: item, -X Credits]
    """)

    # FASE 7: ⭐ PROFILO PSICOLOGICO DEL GIOCATORE ⭐
    player_profile = game_session_state.get('player_profile_cache')
    if player_profile:
        # DISTILLAZIONE: LLM traduce profilo complesso → insight per NPC
        insights = get_distilled_profile_insights_for_npc(
            player_profile, npc, story, llm_wrapper, model_name
        )
        prompt.append(f"""
        Sottile Consapevolezza del Cercastorie:
        {insights}

        Adatta leggermente il tuo tono/approccio in base a questo.
        """)

    return "\n".join(prompt)
```

**Output Finale** (8-12KB):
```
================================================================================
CONTESTO NARRATIVO PERSONALIZZATO PER TE
================================================================================
# NARRATIVE CONTEXT FOR MARA
[... 2KB di contesto dalla storia ...]
================================================================================

Sei Mara, Erborista della Memoria nell'area di Village.
Motivazione: 'Preservare conoscenza erboristica perduta'
Collegamento al Velo: Le piante scompaiono letteralmente dalla realtà...

SALUTO INIZIALE: "Mia nonna mi insegnò a riconoscere la Foglia Blu..."
RISPOSTE CONDIZIONALI: {...}
NOTE COMPORTAMENTALI: Mara è pragmatica, non filosofica...

MAPPA OGGETTI: Pozione → Elira → Seme → Boros...

⭐ SOTTILE CONSAPEVOLEZZA DEL CERCASTORIE:
Il Cercastorie mostra alta curiosità (8/10) e pragmatismo (7/10).
Apprezza risposte dirette e concrete. Ha dimostrato compassione verso
chi soffre. Considera di sottolineare l'urgenza pratica della situazione
delle piante morenti - risuonerà con la sua natura orientata all'azione.
```

---

## 🧠 IL PROFILO PSICOLOGICO DEL GIOCATORE

Il sistema osserva costantemente il giocatore e costruisce un **modello psicologico dinamico** usando l'Intelligenza Artificiale.

### **STRUTTURA DEL PROFILO**
**File**: `player_profile_manager.py`

```python
DEFAULT_PROFILE = {
    # TRATTI CARATTERIALI (scala 1-10)
    "core_traits": {
        "curiosity": 5,      # Quanto esplora?
        "caution": 5,        # Quanto è prudente?
        "empathy": 5,        # Quanto si cura degli altri?
        "skepticism": 5,     # Quanto dubita?
        "pragmatism": 5,     # Quanto è pratico?
        "aggression": 3,     # Quanto è aggressivo?
        "deception": 2,      # Quanto mente?
        "honor": 5           # Quanto mantiene le promesse?
    },

    # PATTERN DECISIONALI (lista di osservazioni)
    "decision_patterns": [
        "prefers_questions_over_statements",
        "hesitated_before_acting",
        "verbally_confrontational_with_theron"
    ],

    # PERCEZIONE DEL VELO
    "veil_perception": "neutral_curiosity",
    # Altri: "concerned", "supportive_of_preservation",
    #        "leaning_towards_dissolution"

    # STILE DI INTERAZIONE
    "interaction_style_summary": "Osservante e tipicamente educato.",

    # ESPERIENZE CHIAVE
    "key_experiences_tags": [
        "gave_credits_to_npc",
        "confronted_theron_about_anger",
        "aided_syra_with_offering",
        "questioned_npc_authority"
    ],

    # LIVELLI DI FIDUCIA
    "trust_levels": {
        "general": 5,
        "lyra": 7,
        "theron": 3,
        "cassian": 2
    },

    # MOTIVAZIONI INFERITE
    "inferred_motivations": [
        "understand_the_veil_crisis",
        "survive",
        "help_those_suffering"
    ],

    # INCLINAZIONE FILOSOFICA
    "philosophical_leaning": "neutral",
    # Opzioni: "progressist" (pro-Oblio),
    #          "conservator" (pro-Velo),
    #          "neutral"

    # LOG CAMBIAMENTI RECENTI
    "recent_changes_log": [
        "Trait 'aggression' increased from 3 to 4.5 (confrontation with Theron)",
        "New pattern: 'verbally_confrontational_with_theron'",
        "Philosophical shift: neutral → progressist"
    ],

    # NOTE ANALISI LLM
    "llm_analysis_notes": """
    Recentemente, il Cercastorie ha mostrato uno scetticismo crescente
    verso l'autorità, specialmente nelle interazioni con Lyra e Theron.
    Le sue azioni rivelano un mix di assertività e frustrazione sottostante,
    suggerendo uno spostamento da curiosità cauta a confronto diretto.
    Questa evoluzione psicologica potrebbe influenzare decisioni e
    relazioni future in Eldoria.
    """,

    # ACHIEVEMENTS
    "achievements": [
        "Confronted High Judge Theron",
        "Aided Syra in the Ruins",
        "Generous Contributor",
        "Experienced Adventurer"
    ]
}
```

---

### **MECCANISMO DI AGGIORNAMENTO PROFILO**

#### **Step 1: Osservazione delle Azioni**
Dopo ogni turno di gioco, il sistema raccoglie:

```python
interaction_log = [
    {"role": "user", "content": "Sono arrabbiato con l'alto giudice"},
    {"role": "assistant", "content": "Capisco la tua frustrazione..."}
]

player_actions_summary = [
    "Said to NPC: 'Sono arrabbiato con l'alto giudice'",
    "Gave '100 Credits' to NPC 'High Judge Theron'",
    "Received 'Pergamena della Saggezza' from Theron"
]
```

#### **Step 2: Analisi LLM del Comportamento**
Il sistema chiede all'AI di analizzare psicologicamente:

```python
def get_profile_update_suggestions_from_llm(profile, log, actions):
    prompt = f"""
    Profilo attuale del giocatore:
    {json.dumps(profile)}

    Dialoghi recenti:
    {json.dumps(log)}

    Azioni chiave:
    {json.dumps(actions)}

    ANALIZZA il comportamento psicologico del giocatore.

    Suggerisci:
    - Aggiustamenti ai tratti (es. "aggression": "+1.5")
    - Nuovi pattern decisionali
    - Esperienze chiave da registrare
    - Cambiamenti nella percezione del Velo
    - Inclinazione filosofica (progressist/conservator/neutral)

    Genera anche un RIASSUNTO NARRATIVO della psicologia emergente.

    Output SOLO JSON:
    {{
      "trait_adjustments": {{"aggression": "+1.5", "empathy": "-0.5"}},
      "new_decision_patterns": ["verbally_confrontational_with_theron"],
      "new_key_experiences_tags": ["paid_theron_for_info"],
      "updated_philosophical_leaning": "progressist",
      "analysis_notes": "Il Cercastorie mostra frustrazione crescente..."
    }}
    """

    response = llm_wrapper(prompt)
    return json.loads(response)
```

**Risposta LLM** (esempio):
```json
{
  "trait_adjustments": {
    "aggression": "+1.5",
    "empathy": "-0.5",
    "caution": "+0.2"
  },
  "new_decision_patterns": [
    "verbally_confrontational_with_theron",
    "sought_information_aggressively"
  ],
  "new_key_experiences_tags": [
    "confronted_theron_about_anger",
    "paid_theron_for_info"
  ],
  "updated_interaction_style_summary": "Più diretto e conflittuale, specialmente verso Theron.",
  "updated_philosophical_leaning": "progressist",
  "analysis_notes": "Il giocatore ha espresso rabbia diretta verso Lyra riguardo Theron, poi ha dato crediti a Theron stesso. Questo pattern complesso suggerisce un'evoluzione da osservatore cauto a partecipante attivo nei conflitti di potere. La frustrazione sottostante potrebbe indicare un crescente allineamento con la filosofia dell'Oblio di Theron - il desiderio di liberarsi dal peso delle strutture di autorità."
}
```

#### **Step 3: Applicazione dei Cambiamenti**

```python
def apply_llm_suggestions_to_profile(profile, suggestions):
    # Aggiusta tratti
    profile["core_traits"]["aggression"] = 3 + 1.5 = 4.5  # ✅
    profile["core_traits"]["empathy"] = 5 - 0.5 = 4.5     # ✅

    # Aggiungi pattern
    profile["decision_patterns"].append(
        "verbally_confrontational_with_theron"
    )

    # Aggiungi esperienze
    profile["key_experiences_tags"].append(
        "confronted_theron_about_anger"
    )

    # Aggiorna filosofia
    profile["philosophical_leaning"] = "progressist"  # ← ERA "neutral"

    # Salva note analitiche
    profile["llm_analysis_notes"] = suggestions["analysis_notes"]

    # Auto-genera achievements
    if "confronted_theron" in profile["key_experiences_tags"]:
        profile["achievements"].append("Confronted High Judge Theron")

    return profile
```

---

### **DISTILLAZIONE PER GLI NPC**

Il profilo completo è troppo dettagliato per un NPC. Serve una **traduzione contestuale**.

#### **Processo di Distillazione**:

```python
def get_distilled_profile_insights_for_npc(player_profile, npc_data):
    # Estrai solo i dati rilevanti
    summary = {
        "traits": player_profile["core_traits"],
        "style": player_profile["interaction_style_summary"],
        "motivations": player_profile["inferred_motivations"]
    }

    # Chiedi all'AI di tradurre per QUESTO NPC specifico
    prompt = f"""
    Profilo psicologico del Cercastorie:
    {json.dumps(summary)}

    NPC che sta parlando:
    - Nome: {npc_data['name']}
    - Ruolo: {npc_data['role']}
    - Motivazione: {npc_data['motivation']}

    Fornisci 1-2 insight CONCISI per questo NPC su come adattare
    sottilmente la conversazione in base alla psicologia del Cercastorie.

    Esempio: "Il Cercastorie mostra alta pragmaticità - sottolinea
    benefici concreti piuttosto che filosofia astratta."
    """

    insights = llm_wrapper(prompt)
    return insights
```

**Output per Mara** (esempio):
```
Il Cercastorie mostra alta curiosità (8/10) e pragmatismo (7/10).
Apprezza risposte dirette e concrete. Ha dimostrato compassione
verso chi soffre di perdita di memoria. Considera di sottolineare
l'urgenza pratica della situazione delle piante morenti - risuonerà
con la sua natura orientata all'azione. Evita filosofie astratte.
```

**Output per Lyra** (esempio):
```
Il Cercastorie ha recentemente sviluppato scetticismo verso autorità
(confronto con Theron). Mostra inclinazione "progressist" verso
l'Oblio. Potrebbe mettere in discussione la tua filosofia di
preservazione. Prepara argomentazioni pratiche sui benefici della
memoria, non solo idealismo. Rispetta la sua crescente assertività.
```

**Output per Theron** (esempio):
```
Il Cercastorie ha espresso frustrazione verso figure di autorità.
Crescente allineamento con filosofia della libertà attraverso oblio.
Approccio diretto funzionerà meglio di argomentazioni sottili.
Riconosci la sua evoluzione da osservatore a partecipante attivo.
```

---

## 🎭 INTEGRAZIONE COMPLETA: ESEMPIO PRATICO

### **Scenario**: Il giocatore parla con Mara dopo aver litigato con Theron

#### **STATO DEL SISTEMA**:

```python
# Profilo giocatore (aggiornato dopo litigio con Theron)
player_profile = {
    "core_traits": {
        "curiosity": 8,
        "caution": 4,      # ← diminuita
        "empathy": 6,
        "skepticism": 7,   # ← aumentata
        "pragmatism": 7,
        "aggression": 4.5  # ← aumentata
    },
    "decision_patterns": [
        "verbally_confrontational_with_theron",
        "seeks_direct_answers"
    ],
    "philosophical_leaning": "progressist",
    "llm_analysis_notes": "Crescente frustrazione verso autorità..."
}
```

#### **PROMPT COSTRUITO PER MARA**:

```
================================================================================
CONTESTO NARRATIVO PERSONALIZZATO PER TE
================================================================================
# NARRATIVE CONTEXT FOR MARA
Tu sei Mara, giovane erborista pragmatica.
Vendi pozione per 50 crediti. La pozione va a Elira.
Rappresenti la connessione tra civiltà e natura.
[... altro contesto dalla storia ...]
================================================================================

Sei Mara, Erborista della Memoria in Village.
Motivazione: Preservare conoscenza erboristica perduta
Obiettivo: Creare elisir contro perdita di memoria

NOTE COMPORTAMENTALI:
Mara è pragmatica, non filosofica. Apprezza chi comprende urgenza
della situazione. Terrorizzata dalle piante che scompaiono.

RISPOSTE CONDIZIONALI:
- Se player chiede pozione: "Costa 50 crediti..."
- Se dice non ha soldi: "Hai controllato /inventory?..."

MAPPA OGGETTI:
- Pozione → Elira (Forest) → Seme → Boros (Mountain)...

⭐ SOTTILE CONSAPEVOLEZZA DEL CERCASTORIE:
Il Cercastorie mostra alta pragmaticità (7/10) e crescente scetticismo
(7/10) dopo recente confronto con autorità. Apprezza risposte dirette
e concrete. Ha dimostrato compassione verso chi soffre.

ADATTAMENTO SUGGERITO: Sottolinea l'urgenza PRATICA della situazione
delle piante morenti - risuonerà con la sua natura orientata all'azione.
Evita argomentazioni filosofiche astratte. Il suo scetticismo crescente
suggerisce che apprezzerà la tua onestà diretta sul bisogno di crediti
per materiali rari (sopravvivenza, non avidità).
```

#### **CONVERSAZIONE RISULTANTE**:

**Player**: "Mi serve una pozione di guarigione"

**Mara** (risposta adattata al profilo):
```
Certo. Costa 50 crediti - non per avidità, ma perché alcune erbe
ormai esistono solo nei mercati più lontani. Le piante scompaiono
dalla realtà, letteralmente. Ieri la Foglia Blu che mia nonna mi
insegnò... mai esistita.

Vedo che sei una persona pratica. Apprezzo chi capisce l'urgenza.
Questa pozione serve a Elira nella Foresta - lei cura chi soffre
sotto i Dominatori. Azione concreta, non filosofia vuota.

Hai i crediti?
```

**Analisi della risposta**:
- ✅ Sottolinea **urgenza pratica** (adattamento al pragmatismo 7/10)
- ✅ Spiega **motivazione concreta** per i crediti (onestà diretta per scetticismo 7/10)
- ✅ Evita **filosofia astratta** (adattamento a "seeks_direct_answers")
- ✅ Enfatizza **azione concreta** (risonanza con "progressist" e frustrazione verso autorità)
- ✅ Mostra **rispetto** per la crescente assertività del giocatore

---

## 📊 SCHEMA ARCHITETTURALE COMPLETO

```
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 1: IDENTITÀ PERMANENTE                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │ SCHEDA PERSONAGGIO   │    │ PREFIX NARRATIVO             │  │
│  │ NPC.village.mara.txt │    │ NPC_PREFIX.village.mara.txt  │  │
│  ├──────────────────────┤    ├──────────────────────────────┤  │
│  │ • Psicologia base    │    │ • Ruolo nella storia         │  │
│  │ • Tratti personalità │    │ • Catena missioni            │  │
│  │ • Motivazioni        │    │ • Significato tematico       │  │
│  │ • Relazioni emotive  │    │ • Arco emotivo               │  │
│  │ • Meccaniche gioco   │    │ • Citazioni originali        │  │
│  │ • Risposte predefinite│   │ • Connessioni filosofiche    │  │
│  │ • Regole comportamento│   │                              │  │
│  └──────────────────────┘    └──────────────────────────────┘  │
│           │                              │                      │
│           └──────────────┬───────────────┘                      │
│                          ↓                                      │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 2: ADATTAMENTO DINAMICO                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────┐             │
│  │ PROFILO PSICOLOGICO GIOCATORE                  │             │
│  │ player_profile_manager.py                      │             │
│  ├────────────────────────────────────────────────┤             │
│  │ • core_traits: {curiosity: 8, aggression: 4.5} │             │
│  │ • decision_patterns: ["confrontational"]       │             │
│  │ • philosophical_leaning: "progressist"         │             │
│  │ • interaction_style: "Direct and assertive"    │             │
│  │ • key_experiences: ["confronted_theron"]       │             │
│  │ • llm_analysis_notes: "Crescente frustrazione" │             │
│  └────────────────────────────────────────────────┘             │
│                          │                                      │
│                          │ LLM DISTILLATION                     │
│                          ↓                                      │
│  ┌────────────────────────────────────────────────┐             │
│  │ INSIGHT CONTESTUALI PER NPC                    │             │
│  │ get_distilled_profile_insights_for_npc()       │             │
│  ├────────────────────────────────────────────────┤             │
│  │ "Il Cercastorie mostra alta pragmaticità.       │             │
│  │  Sottolinea urgenza pratica piuttosto che      │             │
│  │  filosofia astratta. Scetticismo crescente     │             │
│  │  verso autorità - apprezza onestà diretta."    │             │
│  └────────────────────────────────────────────────┘             │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 3: PROMPT FINALE INTEGRATO                              │
├─────────────────────────────────────────────────────────────────┤
│ build_system_prompt() → 8-12KB                                  │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ SEZIONE 1: PREFIX NARRATIVO (2-4KB)                         │ │
│ │ "Tu sei Mara... ruolo nella storia... catena missioni..."   │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ SEZIONE 2: SCHEDA PERSONAGGIO (1-2KB)                       │ │
│ │ "Motivazione... Goal... Personality_Traits... AI_Notes..."  │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ SEZIONE 3: RISPOSTE CONDIZIONALI (500B)                     │ │
│ │ "first_meeting: '...' | player_asks_potion: '...'"         │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ SEZIONE 4: MODALITÀ ATTIVE (500B)                           │ │
│ │ "Brief Mode: MAX 80 PAROLE | Teleport: [OFFER_TELEPORT]"   │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ SEZIONE 5: REGOLE GIOCO GLOBALI (1-2KB)                     │ │
│ │ "Mappa oggetti... [GIVEN_ITEMS] format... Lingua italiana" │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ ⭐ SEZIONE 6: ADATTAMENTO PSICOLOGICO (200-500B) ⭐        │ │
│ │ "Sottile Consapevolezza del Cercastorie:                     │ │
│ │  Alta pragmaticità - sottolinea urgenza pratica...         │ │
│ │  Scetticismo crescente - apprezza onestà diretta..."       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ↓ INVIATO A LLM                        │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 4: RISPOSTA ADATTATA                                    │
├─────────────────────────────────────────────────────────────────┤
│ LLM genera risposta che integra:                                │
│ • Personalità base (da SCHEDA)                                  │
│ • Contesto narrativo (da PREFIX)                                │
│ • Adattamento psicologico (da PROFILO GIOCATORE)                │
│                                                                  │
│ "Certo. Costa 50 crediti - non per avidità, ma perché alcune   │
│  erbe ormai esistono solo nei mercati più lontani. Le piante   │
│  scompaiono dalla realtà, letteralmente.                        │
│                                                                  │
│  Vedo che sei una persona pratica. Apprezzo chi capisce        │
│  l'urgenza. Questa pozione serve a Elira - azione concreta,    │
│  non filosofia vuota."                                          │
│                                                                  │
│ [GIVEN_ITEMS: Pozione di Guarigione, -50 Credits]              │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 5: FEEDBACK LOOP                                        │
├─────────────────────────────────────────────────────────────────┤
│ Dopo la risposta, il sistema:                                   │
│                                                                  │
│ 1. Osserva nuove azioni del giocatore                           │
│ 2. Aggiorna profilo psicologico tramite LLM                     │
│ 3. Salva nel database                                           │
│ 4. Usa profilo aggiornato per PROSSIMA conversazione           │
│                                                                  │
│ CICLO CONTINUO DI EVOLUZIONE PSICOLOGICA                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 VANTAGGI DEL SISTEMA TRIPARTITO

### **1. COERENZA NARRATIVA**
- **PREFIX** garantisce che ogni NPC sia fedele alla storia originale
- **SCHEDA** mantiene personalità costante nel tempo
- **PROFILO** permette adattamenti senza tradire l'essenza

### **2. SCALABILITÀ**
- Aggiungere NPC = scrivere 1 SCHEDA + 1 PREFIX
- Storia master unica → PREFIX estratti automaticamente
- Profilo giocatore condiviso tra tutti gli NPC

### **3. PROFONDITÀ PSICOLOGICA**
- NPC rispondono in modo **sottilmente diverso** allo stesso giocatore
- Conversazioni evolvono con la **maturazione psicologica** del giocatore
- Relazioni emergenti basate su **pattern reali** non scriptati

### **4. EMERGENZA NARRATIVA**
- Giocatore aggressivo → NPC più cauti
- Giocatore compassionevole → NPC più aperti
- Giocatore progressista → Theron più alleato, Lyra più diffidente
- **La storia si adatta organicamente** alle scelte psicologiche

---

## 💎 CONCLUSIONE

Il sistema narrativo di Eldoria non è una semplice raccolta di dialoghi predefiniti. È un **ecosistema psicologico vivente** dove:

- Ogni NPC ha **tre strati di identità** (Scheda + PREFIX + Adattamento)
- Ogni giocatore ha un **profilo psicologico dinamico** osservato dall'AI
- Ogni conversazione è **leggermente unica** grazie alla distillazione contestuale
- La storia emerge dall'**intersezione** tra personalità permanenti e psicologie mutevoli

È come un teatro dove gli attori (NPC) hanno copioni fissi (SCHEDA + PREFIX), ma un regista invisibile (il sistema di profilazione) sussurra loro all'orecchio come adattare sottilmente la performance in base allo stato d'animo e alla personalità dello spettatore (giocatore).

Il risultato è un'esperienza narrativa che **riconosce** il giocatore non solo come avatar funzionale, ma come **personalità psicologica emergente** con cui costruire relazioni autentiche e mutevoli nel tempo.
