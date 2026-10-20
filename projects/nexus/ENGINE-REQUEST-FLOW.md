# Flusso delle richieste

[Tutti i progetti](../README.md) · [Nexus](README.md) · Motore: [panoramica](ENGINE.md), [flusso delle richieste](ENGINE-REQUEST-FLOW.md), [comandi](ENGINE-COMMANDS.md), [prompt](ENGINE-PROMPT.md), [meccaniche](ENGINE-MECHANICS.md), [storage e configurazione](ENGINE-STORAGE-CONFIG.md) · Pipeline: [panoramica](PIPELINE.md), [digest](PIPELINE-DIGEST.md), [derivazione](PIPELINE-DERIVE.md) · Lore: [il Velo](VEIL.md), [mondo](VEIL-WORLD.md), [luoghi](VEIL-PLACES.md), [NPC](VEIL-NPCS.md), [fazioni](VEIL-FACTIONS.md), [missioni](VEIL-MISSIONS.md)

Cosa succede quando un client invia `POST /api/chat`, poi come viene classificato l'input, e i due hook LSL `/sense` e `/leave`.
I componenti sono descritti nella [panoramica del motore](ENGINE.md).

## Un messaggio di chat

```mermaid
sequenceDiagram
  participant C as Client (LSL, curl, MCP)
  participant A as app.py
  participant G as game_system_api
  participant P as command_processor
  participant R as typesafe_router
  participant S as ChatSession e session_utils
  participant L as llm_wrapper
  participant D as archivio documenti
  C->>A: POST /api/chat player_id, message, npc_name, area
  A->>A: verifica il token bearer, ripulisce l'id del giocatore
  A->>G: get_player_system(player_id)
  G->>D: carica stato, inventario, profilo, cronologia
  A->>G: controllo del cancello finale
  opt viene indicata un'area
    A->>G: esegue "/go area"
  end
  opt l'NPC non è quello corrente
    A->>G: esegue "/talk npc"
    G->>S: costruisce il prompt, carica la cronologia, nota di primo incontro
  end
  A->>G: process_player_input(message)
  G->>P: process_input_revised
  alt il testo inizia con una barra
    P->>P: esegue il gestore di quel comando
  else testo libero
    P->>R: classifica l'intento in un thread, attende fino a 1,2 s
    Note over P,L: se non è un comando sicuro, il dialogo parte in modo speculativo
    P->>S: ChatSession.ask(message)
    S->>L: messaggi con il prompt di sistema per primo
    L-->>S: risposta dell'NPC
  end
  P-->>G: nuovo stato e risposta
  G->>G: gestisce i tag: notecard, oggetti, teletrasporto
  G->>D: salva stato e inventario
  G-->>A: npc_response e messaggi di sistema
  A->>A: compone sl_commands
  A-->>C: npc_response, sl_commands, system_messages, llm_stats
```

Note:

- Una richiesta verso un luogo o un NPC bloccato (l'NPC finale prima dell'apertura del cancello) restituisce **403** con `locked: true`.
- Il profilo del giocatore si aggiorna in un thread in background dopo la risposta, quindi non ritarda mai la risposta.
- Ogni rotta tranne `/`, `/web`, `/game` e `/version` richiede `Authorization: Bearer <NEXUS_AUTH_TOKEN>`.

## Come si classifica un messaggio

```mermaid
flowchart TD
  IN["input del giocatore"] --> SL{"inizia con una barra?"}
  SL -->|sì| H["gestore da command_handlers_map"]
  SL -->|no| NLP["controllo dell'intento in un thread<br/>typesafe_router, provider in ordine"]
  NLP --> Q{"finito entro 1,2 s e<br/>un comando con confidenza almeno 0,7?"}
  Q -->|sì| H2["esegue quel comando<br/>mostrato come 'Interpreted as: /comando'"]
  Q -->|no| DLG["dialogo con l'NPC<br/>ChatSession.ask"]
  H --> OUT["stato e messaggi di sistema"]
  H2 --> OUT
  DLG --> OUT
```

I provider di intento vengono provati nell'ordine `pplx`, `jev`, `mercury` (`TYPESAFE_PROVIDER_ORDER`); un provider che continua a
fallire viene saltato per un po' (interruttore di circuito). Un testo libero come "dammi l'infuso" diventa `/receive`; "ti do una
radice" diventa `/give`.

## Gli hook LSL

```mermaid
flowchart LR
  A["un avatar si avvicina al prim dell'NPC"] -->|"POST /sense"| S1["costruisce la sessione di chat dell'NPC<br/>prima visita: saluto predefinito<br/>visita successiva: uno dei saluti di ritorno"]
  S1 --> S2["il saluto viene aggiunto anche alla cronologia dell'NPC"]
  S2 -->|"JSON message e sl_commands"| LSL["l'NPC lo dice ed esegue i comandi SL"]
  LSL -->|"l'avatar parla: POST /api/chat"| CHAT["flusso di chat qui sopra"]
  CHAT --> LSL
  LSL -->|"l'avatar se ne va: POST /leave"| LV["salva la conversazione<br/>con un marcatore di interruzione"]
```

Il saluto viene salvato nella cronologia perché il modello non saluti una seconda volta; `/leave` e `/api/leave_npc` salvano la
conversazione, e alla visita successiva la riprendono con un marcatore "è passato del tempo".

## Dove vive ogni passo

| Passo | File |
|---|---|
| Autenticazione, pulizia degli id, composizione di `sl_commands` | `app.py` |
| Esecuzione del turno, gestione dei tag, aggiornamento di oggetti e crediti | `game_system_api.py` |
| Barra o testo libero, thread speculativi | `command_processor.py` |
| Provider di intento | `command_interpreter.py`, `typesafe_router.py` |
| Prompt, cronologia | `session_utils.py`, `chat_manager.py` |
| Chiamata al modello | `llm_wrapper.py` |
