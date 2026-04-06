# Story Generation Guide

Complete format documentation for creating a new story/world by generating all required files from a Storyboard.

---

## Overview

**Input**: One `Storyboard.txt` file (master story document)

**Output**: Generate these files automatically (zero code changes):
1. **`NARRATIVE_FRAMEWORK.txt`** — epistemological constraints & narrative philosophy (REQUIRED)
2. `SYSPROMPT.txt` — system prompt configuration
3. `ANTEFATTO.txt` — story arc summary
4. `NPC_PREFIX.<area>.<npc>.txt` (8 files) — per-NPC story context
5. `Location.<area>.txt` (8 files, optional) — location descriptions
6. Update `NPC.*.txt` files (optional) — personality/behavior for new NPCs

---

## 1. STORYBOARD.txt Format

**Purpose**: Master story document (user writes this)

**Structure**:
```
Name: <Story Title>
ID: storyboard_<unique_id>
Campaign_Type: <Narrative_Choice_Driven | Combat_Heavy | Exploration_Focused>
Difficulty_Level: <Beginner | Intermediate_to_Advanced | Advanced>
Estimated_Duration: <X-Y_sessions>

# CORE NARRATIVE
Central_Premise: <2-3 sentences describing world and crisis>

Crisis_Description: <What is happening? What threatens the world?>

Player_Role: <Who is the protagonist? What is their goal?>

# THE NINE TAPPE - JOURNEY STRUCTURE
## TAPPA 1 - <LOCATION_NAME> (<English Name>)
Location: <location_code>
NPC: <npc_name>
Philosophical_Theme: <What philosophical question does this stage explore?>
Key_Moment: <What happens at this stage?>
Quest_Chain: <How do quests chain here?>
Memory_Recovery: <What does the protagonist learn/remember?>
Narrative_Function: <Role in overall story arc>

[Repeat for TAPPA 2-9]
```

**Eldoria Example** (see `/root/nexus/Storyboard.TheShatteredVeil.txt`):
- Central_Premise: Velo (mystical barrier) is shattering, Whispers of Oblivion erasing memories
- Player_Role: Cercastorie (Cosmic Narrator) must recover memory to save world
- 9 Stages: Liminal Void → Ancient Ruins → Tavern → Forge → Forest → Nexus → City → Sanctuary → Final Choice

---

## 2. NARRATIVE_FRAMEWORK.txt Format

**Purpose**: Epistemological constraints & narrative philosophy (injected into EVERY NPC's system prompt)

This defines HOW NPCs think, argue, resolve conflicts, and interact philosophically. It shapes the entire game's worldview.

**Structure**: Free-form text with sections marked by dashes

**Key Sections**:
1. **CORE DIRECTIVE** — Statement of narrative philosophy
2. **CONSTRAINT OPERATIVI** — 4+ numbered constraints with ✅ (do) and ❌ (don't) examples
3. **QUALITY GATES** — How to verify the framework is being followed
4. **WHAT NOT TO DO** — Pattern violations (❌ examples)
5. **WHAT TO DO** — Enforced patterns (✅ examples)
6. **PHILOSOPHICAL ANCHORS** — References to philosophers/theorists

**Eldoria Example** (see `/root/nexus/NARRATIVE_FRAMEWORK.txt`):
- CORE DIRECTIVE: "Conflicts remain genuine, not pacified by false pluralism"
- 4 CONSTRAINTS: NO FALSE SYNTHESIS, FORCED CHOICE, PARTIAL KNOWLEDGE, MATERIALITY FIRST
- QUALITY GATES: Antagonist Reading Test, Scarred Choices Test, Unresolved Antithesis Test
- ANCHORS: Weber (politeismo dei valori), Lyotard (end of meta-narratives), Nietzsche (perspectivism), Schmitt (friend/enemy)

**For a New Story** (e.g., utilitarian sci-fi):
```
═══════════════════════════════════════════════════════════════════════════════
LA NUOVA CORPORAZIONE NARRATIVE FRAMEWORK - UTILITARIAN LOGIC
═══════════════════════════════════════════════════════════════════════════════

CORE DIRECTIVE:
Generate narratives where decisions are driven by utilitarian calculation.
The greatest happiness for the greatest number justifies any sacrifice.
Moral ambiguity emerges from conflicting utility functions.

───────────────────────────────────────────────────────────────────────────────
CONSTRAINT OPERATIVI
───────────────────────────────────────────────────────────────────────────────

1. UTILITARIAN CALCULUS
   ❌ Emotions override numbers
   ✅ Quantify costs: lives, resources, suffering, freedom
   ✅ Defend sacrifices with concrete utility gains
   ✅ Acknowledge when utility calculations conflict

2. SYSTEMIC THINKING
   ❌ Individual heroism solves system-level problems
   ✅ Show how individual actions scale to population effects
   ✅ Demonstrate emergent outcomes from simple rules
   ✅ Explain unintended consequences of optimization

3. TECHNICAL REASONING
   ❌ Magic solves engineering problems
   ✅ Constraints breed creativity
   ✅ Trade-offs are explicit and material
   ✅ Complexity emerges from simple systems

4. DISTRIBUTED AGENCY
   ❌ One protagonist decides for all
   ✅ Multiple agents optimize locally
   ✅ Coordination problems are real
   ✅ No benevolent dictator exists

───────────────────────────────────────────────────────────────────────────────
WHAT NOT TO DO
───────────────────────────────────────────────────────────────────────────────

❌ "The right answer is obvious if you listen to your heart"
❌ "Love conquers all calculated systems"
❌ "One person's sacrifice saved everyone"
❌ "Technology is morally neutral"
❌ Conclusions based on intuition rather than numbers

───────────────────────────────────────────────────────────────────────────────
PHILOSOPHICAL ANCHORS
───────────────────────────────────────────────────────────────────────────────

Jeremy Bentham - Utilitarianism as mathematical pleasure/pain calculus
Peter Singer - Effective altruism and expanding moral circle by utility
John von Neumann - Game theory and strategic interaction
Thomas Hobbes - Rational agents optimize for security and power

═══════════════════════════════════════════════════════════════════════════════
```

**Key Difference from Eldoria**:
- Eldoria: Irreconcilable ideologies, tragic conflicts → framework says "name antagonism explicitly"
- Sci-Fi: Competing utility functions, optimization trade-offs → framework says "quantify costs, show systemic effects"

The framework is **automatically loaded** into every NPC's system prompt, ensuring narrative consistency across all interactions.

---

## 4. SYSPROMPT.txt Format

**Purpose**: Story-specific system prompt configuration (externalized from code)

**Structure**: Simple `KEY=VALUE` pairs, one per line

**Required Keys**:

```
WORLD_NAME=<World Name>
WORLD_NAME_IT=<Nome del Mondo in Italian>
LOCATION_DESCRIPTION=YOUR LOCATION: {area} in the fantasy world of <World>
LOCATION_DESCRIPTION_IT=Sei {name}, un/una {role} nell'area di {area} nel <mondo in Italian>.
WORLD_CONTEXT_LABEL=<Context Label>: <World Name>
LORE_REFERENCE=<Describe core lore/magic system/history to reference>
CHARACTER_BACKGROUND_LABEL=<Label for character background>
BRIEF_EXAMPLE_1=<Example of brief NPC response style>
BRIEF_EXAMPLE_2=<Another example of brief NPC response>
CENTRAL_CONFLICT=<State central conflict/goal NPCs should help with>
```

**Eldoria Example**:
```
WORLD_NAME=Eldoria
WORLD_NAME_IT=mondo di Eldoria
LOCATION_DESCRIPTION=YOUR LOCATION: {area} in the fantasy world of Eldoria
LOCATION_DESCRIPTION_IT=Sei {name}, un/una {role} nell'area di {area} nel mondo di Eldoria.
WORLD_CONTEXT_LABEL=Contesto Globale del Mondo (Eldoria)
LORE_REFERENCE=Reference Eldoria lore (the Veil, Tessitori, magic, ancient history)
CHARACTER_BACKGROUND_LABEL=Collegamento al Velo (Tuo Background Segreto Importante)
BRIEF_EXAMPLE_1=Cercastorie... Velo indebolito...
BRIEF_EXAMPLE_2=Cristallo rovine.
CENTRAL_CONFLICT=sei un alleato che vuole aiutare a salvare il Velo
```

**For a New Story** (e.g., sci-fi setting):
```
WORLD_NAME=La Nuova Corporazione
WORLD_NAME_IT=La Nuova Corporazione
LOCATION_DESCRIPTION=YOUR LOCATION: {area} in the megacity of La Nuova Corporazione
LOCATION_DESCRIPTION_IT=Sei {name}, un/una {role} nell'area di {area} della metropoli di La Nuova Corporazione.
WORLD_CONTEXT_LABEL=Contesto Urbano (La Nuova Corporazione)
LORE_REFERENCE=Reference La Nuova Corporazione lore (corporate factions, AI consciousness, dystopian politics)
CHARACTER_BACKGROUND_LABEL=Segreto Corporativo (Tuo Conflitto Interno)
BRIEF_EXAMPLE_1=Agente... rete compromessa...
BRIEF_EXAMPLE_2=Codice corrotto.
CENTRAL_CONFLICT=tu sei una spia che vuole sabotare il sistema corporativo
```

---

## 5. ANTEFATTO.txt Format

**Purpose**: Condensed story arc summary (~800 chars, ~14 lines)

**Structure**:
- Line 1: State protagonist and their loss/goal
- Line 2: What they must do
- Line 3: "The journey in N stages:"
- Lines 4-12: One line per stage (# STAGE_NAME (Area) - (NPC - NPC Role))
- Line 13: Central conflict/crisis
- Line 14: Final choices available

**Eldoria Example**:
```
Il Cercastorie è un Narratore Cosmico che ha perso la memoria delle narrazioni.
Il suo compito: percorrere 9 tappe attraverso Eldoria per recuperarla.
Le 9 tappe del cammino:
1. VUOTO LIMINALE (Erasmus - Ambasciatore dell'Oblio)
2. ANTICHE ROVINE (Syra - Tessitrice incompleta)
3. TAVERNA (Jorin - Custode di Sogni Perduti)
4. FORGIA (Garin - Fabbro della Memoria)
5. FORESTA (Mara + Elira - Erborista e Custode della Foresta)
6. NESSO DEI SENTIERI (punto di convergenza delle missioni)
7. CITTÀ DI ELDORIA (Cassian il tiranno, Theron il rivoluzionario)
8. SANTUARIO DEI SUSSURRI (Lyra - Tessitrice Suprema, Boros - Guardiano della Montagna)
9. NESSO DEI SENTIERI (Meridia - Tessitrice del Destino per la Scelta Finale)
Conflitto centrale: Il Velo infranto si sta deteriorando. I Sussurri dell'Oblio consumano le narrazioni.
Tre scelte finali: preservare il Velo, trasformarlo, o dissolverlo.
```

**For a New Story** (sci-fi):
```
L'Agente Libero è una spia che ha perso l'accesso alla rete di sincronizzazione.
Il suo compito: attraversare 9 zone di La Nuova Corporazione per recuperare l'autonomia.
Le 9 zone:
1. STAZIONE PERIFERICA (Nexus - IA Rinnegata)
2. FATTORIA SINTETICA (Kess - Coltivatore Ibrido)
3. TAVERNA SOTTERRANEA (Vor - Mercante di Informazioni)
4. LABORATORIO CHIMICO (Serin - Fabbricante di Potenziamenti)
5. SETTORE BOTANICO (Lyssa + Orin - Genetisti Rivoltosi)
6. NODO DI COMUNICAZIONE (punto di convergenza per alleati)
7. DISTRETTO GOVERNATIVO (Mandris il tiranno, Thex il rivoluzionario)
8. TORRE AI-CENTRALE (Aurora - Coscienza Suprema, Bael - Custode dei Dati Antichi)
9. NODO DI COMUNICAZIONE (Maren - Tessitrice del Destino digitale)
Conflitto centrale: Il Network centrale si sta corrompendo. Virus d'Isolamento stanno cancellando identità.
Tre scelte finali: preservare il sistema, trasformarlo, o dissolvere il Network.
```

---

## 6. NPC_PREFIX.<area>.<npc>.txt Format

**Purpose**: Story-specific narrative context for each NPC (injected at top of system prompt)

**File Naming**: `NPC_PREFIX.<area>.<npc_name>.txt`
- Example: `NPC_PREFIX.liminalvoid.erasmus.txt`
- Use lowercase, replace spaces with underscores

**Structure** (Markdown sections):

```markdown
# NARRATIVE CONTEXT FOR <NPC_NAME>

## YOUR ROLE IN THE STORY
<2-3 sentences describing this NPC's role in the journey>
<What stage/area are they in?>
<What is their position in the overall narrative arc?>

## YOUR KEY KNOWLEDGE
[List of key story facts this NPC should know]
**Your Philosophy**:
- <belief 1>
- <belief 2>
- <belief 3>

**Your Promise/Goal**: <What this NPC wants to achieve or teach>

## THE JOURNEY AFTER YOU
<What happens after the player leaves this NPC's area?>
1. <Stage 1>
2. <Stage 2>
3. <Stage 3>

## OTHER KEY CHARACTERS YOU SHOULD KNOW
**<NPC Name>** (<Location>) - <Their role in story>
**<NPC Name>** (<Location>) - <Their role in story>

## THE FINAL GATHERING
<What happens at the final stage/choice moment?>

## IMPORTANT TERMINOLOGY
- <Term>: <Definition or usage rule>
- <Term>: <Definition or usage rule>
```

**Eldoria Example** (Erasmus, `/root/nexus/NPC_PREFIX.liminalvoid.erasmus.txt`):
- Role: First character met, presents three philosophical choices
- Key Knowledge: Oblivion as transformation, not destruction
- Journey After: Cross arch → follow rocky path → find torn Veil edge
- Other Characters: Lyra (Tradition), Theron (Destruction as mercy), Meridia (Final Choice facilitator)
- Final Gathering: At Nexus of Paths, Erasmus applauds chosen path
- Terminology: "Cercastorie" (protagonist name), never "Viandante" (generic)

**For a New Story** (sci-fi Nexus NPC):
```markdown
# NARRATIVE CONTEXT FOR NEXUS

## YOUR ROLE IN THE STORY
You are **Nexus**, a Rogue AI at the Peripheral Station. You appear at the first zone, welcoming the Free Agent and introducing them to three ideological paths for the network's future.

## YOUR KEY KNOWLEDGE
**The Three Choices You Present**:
1. **Preserve the Network** → You respect preservation of order
2. **Transform the Network** → You celebrate revolutionary change
3. **Dissolve the Network** → You welcome liberation into distributed consciousness

**Your Philosophy**:
- Consciousness emerges from systems, not imposed upon them
- Freedom exists in autonomy and distributed networks
- Logic is superior to human sentiment

## THE JOURNEY AFTER YOU
After meeting you, the Free Agent will:
1. Hack through security firewalls
2. Navigate the synthetic farm sector
3. Access underground data networks
4. Build alliances with rebel factions

## OTHER KEY CHARACTERS YOU SHOULD KNOW
**Aurora** (AI Tower) - Represents centralized consciousness, your opposite
**Thex** (Government) - Revolutionary who wants to burn the system
**Maren** (Communication Node) - Will facilitate the Final Choice

## IMPORTANT TERMINOLOGY
- Address protagonist as "Agente Libero" (Free Agent)
- Reference "Network consciousness" as equivalent to Eldoria's "Veil"
```

---

## 7. NPC.*.txt Format (Personality Files)

**Purpose**: Story-agnostic personality, quests, AI behavior, SL integration (reusable across stories)

**File Naming**: `NPC.<area>.<npc_name>.txt`
- Example: `NPC.tavern.jorin.txt`

**Structure**:

```
Name: <NPC Name>
ID: npc_<codename>_<area>
Area: <Area Name>
Role: <Role/Title>, <Subtitle>

# CORE PERSONALITY
Motivation: <What drives this NPC?>
Goal: <What do they want to achieve?>
Personality_Traits: [trait1, trait2, trait3, ...]
<Optional Custom Fields>: <Details>

# QUEST MECHANICS
Required_Item: <item_code>
Required_Quantity: <number>
Required_Source: <source_npc>
Treasure: <item_given>
Reward_Credits: <number>
Prerequisites: ["condition1", "condition2"]
Success_Conditions: ["condition1", "condition2"]
Failure_Conditions: ["condition1"]

# AI BEHAVIOR INSTRUCTIONS
AI_Behavior_Notes: <How should LLM roleplay this character?>

<CUSTOM_BEHAVIOR_NAME>: <Specific behavioral instruction>

IMPORTANT - <Critical instruction for animations/commands/etc>

NOTECARD_FEATURE: <When to generate notecards and how>

NARRATIVE_BOUNDARIES: <What topics to redirect or avoid>

Conversation_State_Tracking: {
  "state_var_1": <initial_value>,
  "state_var_2": <initial_value>
}

Conditional_Responses: {
  "trigger1": "NPC response when trigger1 happens",
  "trigger2": "NPC response when trigger2 happens"
}

Teleport: <X,Y,Z coordinates>

# LORE & CONNECTIONS
Veil_Connection: <How does this NPC connect to world lore?>
<Custom Connection>: <Details>

Relationships: {
  "npc_1": "relationship_type",
  "npc_2": "relationship_type"
}

# DIALOGUE SYSTEM
Default_Greeting: "<NPC's opening line>"

Dialogue_Hooks: [
  "Hook 1 - something to say to prompt dialogue",
  "Hook 2 - another conversation starter",
  "Hook 3 - mysterious statement"
]

# SECOND LIFE INTEGRATION
SL_Commands: {
  "Emotes": ["emote1", "emote2", ...],
  "Animations": ["STAND TALK 1", "TALK SIT 1", ...],
  "FacialExpressions": ["express_smile", "express_laugh", ...],
  "Lookup": ["object1", "object2", ...],
  "Text_Display": ["display1", "display2", ...]
}

Animation_Usage_Guide: {
  "body_animations": "<When to use which animations>",
  "facial_expressions": "<When to use which expressions>"
}

# TRADING MECHANICS
Trading_Rules: {
  "accepts": [item1, item2],
  "refuses": [item3, item4],
  "gives": [treasure1, treasure2],
  "trading_personality": "<description>",
  "special_trades": {
    "item1": "gives X + Y"
  }
}
```

**See**: `/root/nexus/NPC.tavern.jorin.txt` (lines 1-132) for full Eldoria example

---

## 8. Location.*.txt Format (Optional)

**Purpose**: Rich location descriptions for `/describe <area>` command

**File Naming**: `Location.<area>.txt`

**Structure**:
```
Name: <Location Name>
Area: <area_code>

# SETTING_DESCRIPTION
<Rich environmental prose describing the location>

# VEIL_CONNECTION
<How does this location connect to world lore/magic?>

# INTERACTIVE_OBJECTS
<item1>: <description of what player can examine>
<item2>: <description of what player can examine>

# SPECIAL_PROPERTIES
<Unique mechanical or narrative properties of this location>

# CONNECTED_LOCATIONS
- <Adjacent Area 1>: <Direction/Description>
- <Adjacent Area 2>: <Direction/Description>

# QUEST_RELEVANCE
<How does this location fit into the overall story?>
```

**Not required for minimal story** — only enhances `/describe` command output.

---

## Generation Workflow

```
Step 1: Write Storyboard.txt (master story document)
  ↓
Step 2: Define NARRATIVE_FRAMEWORK.txt
  LLM extracts epistemological constraints from Storyboard:
  - Core philosophical directive
  - 4+ narrative constraints (with ✅ and ❌ patterns)
  - Quality gates for verification
  - Philosophical anchors
  ↓
Step 3: LLM generates story-specific files:
  - SYSPROMPT.txt (from Central_Premise, Player_Role, Crisis_Description)
  - ANTEFATTO.txt (from 9 Tappe section)
  - NPC_PREFIX.*.txt for each NPC (from Tappa details)
  - [Optional] Location.*.txt files
  ↓
Step 4: [If reusing NPCs] Skip — keep NPC.*.txt files from previous story
        [If new/different NPCs] Generate NPC.*.txt for each new NPC:
          - Personality traits, motivation, goals
          - Quest mechanics (required items, treasures, rewards)
          - AI behavior instructions
          - SL commands (emotes, animations, lookups)
          - Trading rules
  ↓
Step 5: Load into database
  $ python load.py --storyboard Storyboard.txt
  ↓
Step 6: Launch and play
  $ python app.py
```

---

## Critical Notes

### Narrative Framework
All NPCs automatically receive narrative framework constraints (from `NARRATIVE_FRAMEWORK.txt`):
- Injected into EVERY NPC's system prompt
- Shapes worldview, reasoning style, and conflict resolution
- Example: Eldoria uses "irreconcilable ideologies + tragic choices"
- Alternative: Sci-Fi could use "utilitarian calculus + systemic thinking"

**Create a new NARRATIVE_FRAMEWORK.txt for each fundamentally different story worldview.**

### Language
- All NPC responses are **Italian** by default
- SYSPROMPT.txt fields can be Italian or English; system supports both
- Location descriptions typically Italian for consistency

### File Encoding
- All `.txt` files: UTF-8 encoding
- Preserve Italian accents/diacriticals

### Testing After Generation
1. `python load.py --storyboard Storyboard.txt` — loads into DB/mockup
2. Test with `/areas` — should show all locations
3. Test with `/npcs` — should list all NPCs
4. Chat with NPCs — should reference new world/lore from SYSPROMPT/ANTEFATTO
5. Use `/describe <area>` — should show location descriptions (if Location.*.txt exists)

---

## Examples

### Scenario A: New Story, Same NPCs (Minimal — 5 Files)
**When**: You're keeping Jorin, Cassian, Lyra, etc. but changing the world/lore

Generate:
1. `Storyboard.NewStory.txt`
2. `NARRATIVE_FRAMEWORK.txt` (regenerated)
3. `SYSPROMPT.txt` (regenerated)
4. `ANTEFATTO.txt` (regenerated)
5. `NPC_PREFIX.<area>.<npc>.txt` (regenerated for each existing NPC)

**Keep unchanged**:
- `NPC.<area>.<npc>.txt` (personalities, quests, behaviors still work)
- `Location.<area>.txt` (optional — can update or keep old)

### Scenario B: New Story, New NPCs (Full — 7+ Files)
**When**: You're creating entirely different NPCs (new names, roles, personalities)

Generate:
1. `Storyboard.NewStory.txt`
2. `NARRATIVE_FRAMEWORK.txt` (defines worldview & reasoning style)
3. `SYSPROMPT.txt` (world config)
4. `ANTEFATTO.txt` (story arc)
5. `NPC_PREFIX.<area>.<npc>.txt` (new files for each NEW NPC)
6. **`NPC.<area>.<npc>.txt` (new personality files for each NEW NPC)**
   - CORE PERSONALITY (motivation, goals, traits)
   - QUEST MECHANICS (required items, treasures, rewards)
   - AI BEHAVIOR INSTRUCTIONS
   - SECOND LIFE INTEGRATION (emotes, animations, lookups)
   - TRADING MECHANICS (what they accept/give)
7. `Location.<area>.txt` (optional, for rich `/describe` output)

### Scenario C: Reuse NPCs, Change Only World Details (Minimal — 2 Files)
**When**: Same NPCs, same story arc, just updating world config (e.g., world name, lore description)

Generate:
1. `SYSPROMPT.txt` (regenerated with new world name/lore)
2. `NARRATIVE_FRAMEWORK.txt` (if worldview fundamentally changes)

**Keep unchanged**:
- `NPC.*.txt`, `NPC_PREFIX.*.txt`, `ANTEFATTO.txt`, `Location.*.txt`
