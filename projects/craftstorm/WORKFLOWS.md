# craftstorm: flussi di lavoro

[Tutti i progetti](../README.md) · [craftstorm](README.md) · [architettura](ARCHITECTURE.md) · [flussi di lavoro](WORKFLOWS.md)

## Avviare il viewer da browser

```mermaid
flowchart LR
  I["pip install -r web/requirements.txt"] --> R["python3 web/bridge.py"]
  R --> U["apri http://localhost:8088/"]
  R2["alternativa: python3 web/cluster.py<br/>N ponti dietro una porta"] --> U
  R3["alternativa: web/desktop.py<br/>guscio desktop"] --> U
```

Il ponte richiede le dipendenze Python elencate in `web/requirements.txt` (per esempio `imagecodecs`); `bridge.js` è un porting in Node.

## Le parti in C e compilate

Le ricette del `justfile` in `web/`:

| Ricetta | Cosa fa |
|---|---|
| `build-bridge-c` / `clean-bridge-c` | Compila (o pulisce) la versione Cython del ponte |
| `run-compiled` | Esegue il ponte compilato (`bridge_compiled.py`) |
| `test-compiled` | Esegue i test sul ponte compilato |
| `build-fast` / `clean-fast` | Compila (o pulisce) l'estensione C `csfast` dei percorsi caldi |

## Testare

```mermaid
flowchart LR
  T1["npm test<br/>lato browser"] --> OK["entrambi verdi prima di ogni modifica"]
  T2["python3 -m unittest discover -s tests -v<br/>141 test al 2026-10-18"] --> OK
```

## L'elenco delle correzioni previste

`web/HANDOVER_TODO.md` raccoglie i difetti trovati nella revisione del 2026-09-08, in ordine di intervento e senza accorparli:

```mermaid
flowchart TD
  A["1. Correttezza: eventi di WebSocket vecchi,<br/>rientro nella voce, pianificazione dei comandi del ponte"] --> B
  B["2. Rendering: mutazione dei materiali delle texture,<br/>stato della coda delle texture, texture in caricamento"] --> C
  C["3. Cache degli sculpt, contabilità dei gruppi di istanze,<br/>scala dei BVH"] --> D
  D["4. Proprietà degli asset, limiti delle cache,<br/>errori dei worker, profilazione"]
```

Ogni voce ha una condizione di accettazione verificabile da sola; le riproduzioni temporanee vanno trasformate in test di regressione
committati prima di correggere.

## Compilare il viewer Firestorm

Le istruzioni per sistema operativo stanno in `doc/building_windows.md`, `doc/building_macos.md` e `doc/building_linux.md`; per
contribuire, `CONTRIBUTING.md`. Il progetto Firestorm non offre supporto per chi compila da sé.
