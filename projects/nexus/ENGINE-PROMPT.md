# Assemblaggio del prompt

[Tutti i progetti](../README.md) · [Nexus](README.md) · Motore: [panoramica](ENGINE.md), [flusso delle richieste](ENGINE-REQUEST-FLOW.md), [comandi](ENGINE-COMMANDS.md), [prompt](ENGINE-PROMPT.md), [meccaniche](ENGINE-MECHANICS.md), [storage e configurazione](ENGINE-STORAGE-CONFIG.md) · Pipeline: [panoramica](PIPELINE.md), [digest](PIPELINE-DIGEST.md), [derivazione](PIPELINE-DERIVE.md) · Lore: [il Velo](VEIL.md), [mondo](VEIL-WORLD.md), [luoghi](VEIL-PLACES.md), [NPC](VEIL-NPCS.md), [fazioni](VEIL-FACTIONS.md), [missioni](VEIL-MISSIONS.md)

Come si costruisce il **prompt di sistema** di un NPC quando inizia una conversazione (`/talk`, oppure `/sense` da LSL). È il punto
in cui il [lore](VEIL-WORLD.md) arriva ai personaggi: qui si leggono i file prodotti dalla [pipeline](PIPELINE.md).
Codice: `session_utils.build_system_prompt` e `load_and_prepare_conversation`.

```mermaid
flowchart TD
  subgraph sources["Sorgenti"]
    S1["ANTEFATTO.txt<br/>da lore.txt, max 800 caratteri"]
    S2["NARRATIVE_FRAMEWORK.txt<br/>vincoli narrativi"]
    S3["record NPC: notecard_feature"]
    S4["record NPC: business_card"]
    S5["NPC_PREFIX.area.nome.txt<br/>da lore.txt"]
    S6["record NPC: ruolo, movente, obiettivo,<br/>tesoro, suggerimento, saluti"]
    S7["SYSPROMPT.toml<br/>etichette del mondo"]
    S8["stato del giocatore: inventario, crediti,<br/>profilo, conversazioni precedenti"]
    S9["veil_finale.py"]
  end
  subgraph prompt["Prompt di sistema, all'incirca in quest'ordine"]
    B1["1. Antefatto"]
    B2["2. Vincoli narrativi"]
    B3["3. Regole della notecard e GIVE_NOTECARD"]
    B4["4. Biglietto da visita e GIVE_CARD"]
    B5["5. Contesto narrativo personalizzato (il prefisso)"]
    B6["6. Personaggio: ruolo, movente, obiettivo, tesoro"]
    B7["7. Saluto già pronunciato, risposte condizionali, nomi"]
    B8["8. Regole di comportamento, modalità breve"]
    B9["9. Capacità di teletrasporto e NPC noti"]
    B10["10. Contesto del mondo e regole linguistiche"]
    B11["11. Inventario, crediti, profilo del giocatore"]
    B12["12. Regole del finale (solo l'NPC finale)"]
  end
  S1 --> B1
  S2 --> B2
  S3 --> B3
  S4 --> B4
  S5 --> B5
  S6 --> B6
  S6 --> B7
  S7 --> B10
  S8 --> B11
  S9 --> B12
  B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8 --> B9 --> B10 --> B11 --> B12
  B12 --> TRIM["taglia a 16 KB<br/>le sezioni marcate OBBLIGATORIE, CRITICHE, NOTECARD restano"]
  TRIM --> FM{"nessuna cronologia salvata<br/>per questo giocatore e questo NPC?"}
  FM -->|sì| NOTE["aggiunge la nota di primo incontro:<br/>mai dire che il giocatore è tornato"]
  FM -->|no| HIST["carica la cronologia,<br/>aggiunge un marcatore di ripresa se c'è stata una pausa"]
  NOTE --> CS["ChatSession"]
  HIST --> CS
```

## Cosa viene dal lore

| Parte del prompt | File | Prodotto da | Pagina del lore |
|---|---|---|---|
| Antefatto (il mondo in 800 caratteri) | `ANTEFATTO.txt` | la riga `Antefatto:` di `lore.txt` [01] | [Mondo](VEIL-WORLD.md) |
| Contesto narrativo personalizzato | `NPC_PREFIX.<area>.<nome>.txt` | `lore.txt` [05] [06] [07] [08] [09] | [NPC](VEIL-NPCS.md), [luoghi](VEIL-PLACES.md), [missioni](VEIL-MISSIONS.md) |
| Ruolo, movente, obiettivo, tesoro, suggerimento | record NPC nell'archivio | `lore.txt` [07], scritto da `just lore` | [NPC](VEIL-NPCS.md) |
| Biglietto da visita e notecard | `NPC_BUSINESS_CARDS.json`, `NPC_EXTRAS.json` | contenuto scritto a mano, caricato da `seed_npc_extras.py` | [NPC](VEIL-NPCS.md) |

Cosa contiene un file di prefisso: ruolo e luogo dell'NPC, movente e obiettivo, ciò che custodisce, come trattare il giocatore, il
posto nella catena di missioni (chi viene prima e dopo), la fazione e il prezzo di quella via, ciò che non si può conciliare, e
ciò che un NPC può o non può sapere.

## Parti che ancora non vengono dal lore

`NARRATIVE_FRAMEWORK.txt` e `SYSPROMPT.toml` descrivono ancora un vecchio mondo "Cyberspazio" e non sono generati da `lore.txt`.
È la probabile origine di parole come "algoritmo" o "server" che compaiono nel parlato degli NPC; il lore le vieta
([termini](VEIL-WORLD.md#termini)). Vedi le lacune note nella [panoramica della pipeline](PIPELINE.md#lacune-note).

## Instradamento verso il modello

```mermaid
flowchart LR
  M["nome del modello da config.ini"] --> Q{"di che tipo?"}
  Q -->|"claude haiku 4.5"| AN["API Anthropic<br/>ripiega su OpenRouter"]
  Q -->|"nome semplice con deepseek,<br/>senza barra"| DS["API DeepSeek<br/>richiede DEEPSEEK_API_KEY"]
  Q -->|"qualunque nome con una barra,<br/>es. deepseek/deepseek-v4.1-flash-1017"| OR["OpenRouter"]
```
