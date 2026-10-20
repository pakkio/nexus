# jev-pakkio: flussi di lavoro

[Tutti i progetti](../README.md) · [jev-pakkio](README.md) · [architettura](ARCHITECTURE.md) · [flussi di lavoro](WORKFLOWS.md)

## Installare e servire

```mermaid
flowchart LR
  U["uv sync"] --> H["uv run hf auth login"]
  H --> D["uv run hf download google/gemma-3-4b-it<br/>--local-dir models/gemma-3-4b-it"]
  D --> SV["uv run jev_pakkio serve<br/>--backend torch --device auto --port 8000"]
  SV --> C["uv run jev_pakkio check<br/>i punteggi in batch coincidono con la ricodifica ingenua"]
  SV --> SCR["jev_pakkio score --context ... --option ..."]
```

Serve Python 3.12+ e `uv`; la licenza di Gemma va accettata su Hugging Face prima del download. Su macOS (`make setup`) il comando
sceglie MLX; altrove PyTorch. Per NVIDIA si installa prima la build di PyTorch adatta e poi si usa `uv run --no-sync` perché `uv`
non la sostituisca.

## Usare il server

Con il server acceso (`make serve`):

| Cosa | Come |
|---|---|
| Stato | `make health` → `GET /health` |
| Punteggio di opzioni | `POST /score` con contesto e opzioni (`make request` ne mostra un esempio) |
| Domande System One | `POST /v1/systemone`: scelta, punteggio e sì/no insieme (`make systemone`) |
| Demo Doom | `make doom` (richiede il server acceso): il modello sceglie ogni azione |
| Da un agente | `jev_pakkio mcp` espone `classify`, `rate`, `noul`, `jev`, `train_lora`, `status` |

## Addestrare e misurare

```mermaid
flowchart TD
  subgraph head["Testa di attenzione (richiede MLX)"]
    F["jev_pakkio features<br/>feature congelate in runs/feats"] --> T["jev_pakkio train<br/>addestra la testa"]
    T --> E["jev_pakkio eval-head<br/>top-k, ECE, controllo con contesto mescolato"]
  end
  subgraph lora["LoRA"]
    L["jev_pakkio lora"] --> LE["jev_pakkio lora-eval"]
    LE --> LQ["jev_pakkio lora-quantize"]
  end
  subgraph zero["Senza addestramento"]
    Z["jev_pakkio eval<br/>accuratezza top-k zero-shot su JSONL"]
    B["make bench<br/>latenza: in cache e in batch contro ingenuo"]
  end
```

I dati sintetici si generano con gli script `gen_*.py`; `compare_jev.py` mette `jev_pakkio` accanto al Jev ospitato di TypeSafe sulle
stesse righe, e `bench_mixed.py` fa girare 100 domande miste (40 di scelta, 30 sì/no, 30 di punteggio) su tutti i motori.

## Memoria agentica (Jev-Mem)

```mermaid
flowchart LR
  W["jev_pakkio mem add<br/>scrive un'osservazione"] --> ST[("store")]
  Q["jev_pakkio mem query<br/>recupera le prove per una domanda"] --> ST
  CTRL["il controller decide<br/>cosa scrivere e cosa leggere"] --> W
  CTRL --> Q
  CTRL -.->|"System One su un server in esecuzione"| SV["jev_pakkio serve"]
```
