# craftsim: flussi di lavoro

[Tutti i progetti](../README.md) · [craftsim](README.md) · [architettura](ARCHITECTURE.md) · [flussi di lavoro](WORKFLOWS.md)

I percorsi pratici: compilare e testare, mettere su una griglia, avviare con i controlli, portare la voce in produzione.
Le fonti sono `CLAUDE.md`, `BUILDING.md`, `SELF_HOSTING.md`, `JANUS-SETUP.md` e `TEST-PLAN-VOICE.md` del repository.

## Compilare e testare

```mermaid
flowchart TD
  C["clone fresco"] --> P["./runprebuild.sh<br/>rigenera sln e csproj"]
  P --> B["dotnet build OpenSim.sln"]
  B --> T1["dotnet test tests/OpenSim.Tests/OpenSim.Tests.csproj"]
  B --> T2["dotnet test tests/CraftSim.SmokeTests/CraftSim.SmokeTests.csproj"]
  CI["CI: .github/workflows/craftsim-net10.yml"] --> BS["build.sh"]
  BS --> T1
  BS --> T2
  CI --> LG["installa libgdiplus<br/>serve a System.Drawing.Common"]
```

- `./runprebuild.sh` è il **primo comando su un clone fresco**: `OpenSim.sln` e i progetti generati non sono versionati.
- I progetti di test **non sono nella soluzione**, quindi `dotnet build OpenSim.sln` non li compila: si lanciano per percorso.
- Ultima verifica registrata in `CLAUDE.md`: compilazione senza errori né avvisi; test `OpenSim.Tests` 477/479 più 2/2 di
  `CraftSim.SmokeTests`. L'unico test che fallisce nell'esecuzione completa dipende dal carico e passa da solo.
- Una versione dell'SDK `10.0.3xx` **non** soddisfa `global.json`: serve un SDK della fascia `10.0.1xx`.

## Mettere su una griglia

```mermaid
flowchart LR
  S1["clona e compila"] --> S2["crea i file di configurazione<br/>(sono ignorati da git)"]
  S2 --> S3["avvia prima Robust"]
  S3 --> S4["poi OpenSim"]
  S4 --> S5["verifica la raggiungibilità di rete"]
  S5 --> S6["distribuisci l'URI di accesso"]
```

L'ordine conta: Robust prima, OpenSim dopo. `SELF_HOSTING.md` descrive anche il trabocchetto della `DefaultRegion` e chi può davvero
raggiungere la griglia in rete.

## Avviare con i controlli

```mermaid
flowchart TD
  A["bin/opensim.sh"] --> L["imposta LD_PRELOAD con libwrap_memcpy.so"]
  L --> PF["bin/preflight.sh<br/>solo avvisi, --strict esce con 1"]
  PF --> W{"avvisi?"}
  W -->|sì| WL["segnala: libBulletSim che richiede GLIBC_2.38,<br/>shim mancante, YEngine senza [YEngine] Enabled,<br/>TesseractDataPath errato, osJson senza [JsonStore],<br/>MySQL senza backup da 7 giorni"]
  W -->|no| R["avvia il server"]
  WL --> R
```

Si avvia con `bin/opensim.sh`, non con un semplice `dotnet OpenSim.dll`: senza lo shim la fisica fallisce con
`undefined symbol: __wrap_memcpy`.

## Voce WebRTC in produzione

```mermaid
flowchart LR
  JN["Janus: abilita audiobridge,<br/>trasporto HTTP con il base path della voce,<br/>API admin con il suo secret"] --> FA["Fase A: la base, senza voce"]
  FA --> FB["Fase B: la metà OpenSim, ancora senza backend"]
  FB --> FC["Fase C: synthvoice in LAN<br/>(consigliata, non obbligatoria)"]
  FC --> FD["Fase D: produzione su craft-world"]
```

`TEST-PLAN-VOICE.md` elenca le decisioni già prese, un interludio su Rust per chi non lo conosce, e cosa il test **non** copre.
`JANUS-SETUP.md` spiega la corrispondenza tra le due configurazioni (Janus e OpenSim) e i messaggi d'errore più comuni.

## Lavorare con un agente

`AGENTS.md` descrive due cose: gli strumenti MCP per accedere al simulatore in funzione (`mcp-craftsim`) e l'architettura del
progetto con i trabocchetti di build. `CLAUDE.md` tiene lo stato aggiornato (versione, configurazione, controlli aperti).
