# 🎮 GUIDA RAPIDA AL SISTEMA NARRATIVO

## 📌 I TRE STRATI DI OGNI PERSONAGGIO

### 1️⃣ **SCHEDA** (`NPC.village.mara.txt`) - Chi è?
```
✓ Psicologia permanente
✓ Tratti caratteriali
✓ Meccaniche di gioco (quest, prezzi)
✓ Risposte predefinite situazionali
✓ Regole comportamentali rigide
```

### 2️⃣ **PREFIX** (`NPC_PREFIX.village.mara.txt`) - Quale ruolo ha?
```
✓ Estratto dalla storia master (ilpercorsodelcercastorie)
✓ Posizione nella catena di missioni
✓ Significato tematico/filosofico
✓ Arco emotivo narrativo
✓ Citazioni dalla storia originale
```

### 3️⃣ **PROMPT DINAMICO** (generato al volo) - Come si adatta al giocatore?
```
✓ SCHEDA + PREFIX + Regole gioco
✓ Modalità attive (brief, hint, teleport)
✓ ⭐ PROFILO PSICOLOGICO del giocatore ⭐
```

---

## 🧠 PROFILO PSICOLOGICO DEL GIOCATORE

### **Cosa Traccia**:
```python
{
  "core_traits": {            # Tratti caratteriali 1-10
    "curiosity": 8,
    "aggression": 4.5,
    "empathy": 6,
    "pragmatism": 7
  },

  "decision_patterns": [      # Pattern osservati
    "verbally_confrontational",
    "seeks_direct_answers"
  ],

  "philosophical_leaning": "progressist",  # Pro-Oblio/Pro-Velo/Neutro

  "key_experiences": [        # Eventi significativi
    "confronted_theron",
    "aided_syra"
  ],

  "llm_analysis_notes": "Il Cercastorie mostra frustrazione crescente..."
}
```

### **Come Funziona**:
1. **Osserva** azioni del giocatore ogni turno
2. **Chiede all'AI** di analizzare psicologia
3. **Aggiorna** tratti e pattern
4. **Distilla** insight per ogni NPC specifico
5. **Adatta** risposte NPC in base al profilo

---

## 🔄 FLUSSO COMPLETO DI UNA CONVERSAZIONE

```
┌─────────────────┐
│ Player scrive   │ "Voglio la pozione"
└────────┬────────┘
         ↓
┌────────────────────────────────────────┐
│ Sistema carica:                        │
│ 1. SCHEDA Mara (psicologia base)       │
│ 2. PREFIX Mara (ruolo nella storia)    │
│ 3. Profilo player (psicologia dinamica)│
└────────┬───────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│ LLM distilla profilo → insight:        │
│ "Player pragmatico, scettico verso     │
│  autorità, apprezza risposte dirette"  │
└────────┬───────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│ Costruisce PROMPT (8-12KB):            │
│ • PREFIX narrativo                     │
│ • SCHEDA personaggio                   │
│ • Regole gioco                         │
│ • ⭐ Insight psicologici ⭐            │
└────────┬───────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│ LLM genera risposta ADATTATA:          │
│ "Costa 50 crediti - non avidità, ma    │
│  sopravvivenza. Le piante scompaiono.  │
│  Vedo che sei pratico - azione         │
│  concreta, non filosofia vuota."       │
│                                        │
│ [GIVEN_ITEMS: Pozione, -50 Credits]   │
└────────┬───────────────────────────────┘
         ↓
┌────────────────────────────────────────┐
│ Sistema processa:                      │
│ • Rimuove [GIVEN_ITEMS]                │
│ • Dà pozione, toglie 50 crediti        │
│ • Osserva azione player                │
│ • Aggiorna profilo psicologico         │
└────────────────────────────────────────┘
```

---

## 💡 PERCHÉ TRE STRATI?

### **SCHEDA** = Identità permanente
- "Mara è sempre pragmatica"
- "Vende sempre pozione per 50 crediti"
- Non cambia mai

### **PREFIX** = Ruolo narrativo fisso
- "Mara è il primo passo della catena"
- "La pozione va a Elira"
- Estratto dalla storia master

### **PROFILO PLAYER** = Adattamento dinamico
- "Questo player è scettico → sottolinea onestà"
- "Questo player è filosofico → aggiungi riflessioni"
- Cambia ogni conversazione

---

## 🎯 ESEMPI DI ADATTAMENTO

### **Player Aggressivo (aggression: 8/10)**:
```
Mara risponde: "50 crediti. Prendere o lasciare. Le piante scompaiono
e io devo sopravvivere. Se non ti va, cerca altrove."

[Tono più brusco, meno spiegazioni]
```

### **Player Compassionevole (empathy: 9/10)**:
```
Mara risponde: "Costa 50 crediti... lo so, è molto. Ma le piante
stanno scomparendo letteralmente dalla realtà. Mia nonna... non
ricorda più le erbe che mi insegnò. Sto lottando per preservare
quello che resta. Questa pozione aiuterà Elira a curare chi soffre."

[Tono emotivo, condivide vulnerabilità]
```

### **Player Filosofico (curiosity: 9/10, philosophical)**:
```
Mara risponde: "La pozione costa 50 crediti. Sai, c'è una domanda
che mi perseguita: se una pianta scompare dalla realtà quando viene
dimenticata, è mai esistita davvero? Mia nonna mi insegnò la Foglia
Blu... ieri non c'era. Non morta - mai esistita. Cosa vuol dire
'esistere' in un mondo dove il Velo si sfilaccia?"

[Aggiunge riflessioni filosofiche]
```

---

## 📊 FILE COINVOLTI

| File | Cosa Contiene | Dimensione |
|------|---------------|------------|
| `ilpercorsodelcercastorie` | Storia master completa | 425 righe |
| `NPC.village.mara.txt` | Scheda personaggio Mara | ~123 righe |
| `NPC_PREFIX.village.mara.txt` | Contesto narrativo Mara | ~45 righe (2KB) |
| `session_utils.py:build_system_prompt()` | Costruttore prompt finale | Genera 8-12KB |
| `player_profile_manager.py` | Profilo psicologico player | JSON ~1-2KB |
| Database | Salvataggio profilo | PlayerProfiles table |

---

## 🔧 COMANDI CHIAVE NEL CODICE

### **Carica PREFIX**:
```python
prefix = _load_npc_narrative_prefix(npc['area'], npc['name'])
# Cerca: NPC_PREFIX.village.mara.txt
```

### **Distilla Profilo**:
```python
insights = get_distilled_profile_insights_for_npc(
    player_profile, npc_data, story, llm_wrapper
)
# Output: "Player pragmatico - sottolinea urgenza pratica"
```

### **Costruisci Prompt**:
```python
prompt = build_system_prompt(npc, story, game_session_state)
# Combina: SCHEDA + PREFIX + Regole + Profilo
```

### **Aggiorna Profilo**:
```python
suggestions = get_profile_update_suggestions_from_llm(
    profile, interaction_log, actions
)
profile = apply_llm_suggestions_to_profile(profile, suggestions)
```

---

## ✨ MAGIA DEL SISTEMA

Il giocatore **non vede** mai:
- ❌ Il PREFIX narrativo
- ❌ Le note AI_Behavior
- ❌ Il suo profilo psicologico
- ❌ Gli insight distillati

Ma **percepisce**:
- ✅ NPC che reagiscono alla sua personalità
- ✅ Conversazioni che "risuonano" con il suo stile
- ✅ Relazioni che evolvono organicamente
- ✅ Storia che si adatta alle sue scelte psicologiche

**È come se gli NPC ti conoscessero davvero.**
