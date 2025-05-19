# Nexus: LLM-Powered Text Adventure Framework

![Nexus Framework Banner](https://img.shields.io/badge/Nexus-Interactive%20Fiction%20Engine-blue)

**Nexus** è un framework avanzato per la creazione di avventure testuali potenziate da modelli linguistici di grandi dimensioni (LLM). Pensato per sviluppatori di narrativa interattiva che vogliono creare mondi dinamici con personaggi non giocanti dotati di memoria, apprendimento e profondità psicologica.

Il sistema attualmente implementa "The Shattered Veil", un'avventura ambientata nel mondo di Eldoria, dove una barriera mistica che protegge il mondo si sta disgregando.

## Indice

- [Caratteristiche Principali](#caratteristiche-principali)
- [Architettura](#architettura)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Esecuzione Rapida](#esecuzione-rapida)
- [Utilizzo](#utilizzo)
- [Creazione di NPC e Storie](#creazione-di-npc-e-storie)
- [Come Contribuire](#come-contribuire)

## Caratteristiche Principali

- **NPCs con Memoria Persistente**: I personaggi ricordano le conversazioni e le interazioni precedenti, permettendo una narrazione continuativa e coerente.
- **Profilo Psicologico del Giocatore**: Il sistema analizza il comportamento del giocatore attraverso LLM per costruire un profilo psicologico che influenza le reazioni degli NPC.
- **Adattamento degli NPC**: Gli NPC adattano le loro risposte in base al profilo del giocatore per interazioni più personalizzate.
- **Interfaccia a Linea di Comando**: Sistema di comandi intuitivo con formattazione ANSI per una migliore leggibilità.
- **Database Flessibile**: Supporto per database MySQL reale con fallback a sistema basato su file JSON.
- **Integrazione LLM**: Wrapper per OpenRouter che supporta diversi modelli linguistici.
- **Modalità di Consulenza**: Sistema `/hint` che permette ai giocatori di consultare un NPC saggio (Lyra) per ricevere consigli strategici.
- **Sistema di Inventario e Crediti**: Gestione degli oggetti e dell'economia di gioco.

## Architettura

Il framework è composto da moduli interconnessi che gestiscono diversi aspetti del gioco:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│     main.py     │──────│   main_core.py  │──────│ command_processor│
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                         │
         │                        │                         │
┌────────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
│   db_manager.py │◄─────│  session_utils  │◄─────│  chat_manager   │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                         │
         │                        │                         │
┌────────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
│player_profile_  │◄─────│  hint_manager   │◄─────│   llm_wrapper   │
│    manager      │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

- `main.py`: Punto di ingresso dell'applicazione che gestisce argomenti da linea di comando e inizializzazione.
- `main_core.py`: Loop di interazione principale che coordina le sessioni di gioco.
- `command_processor.py`: Elabora i comandi dell'utente e aggiorna lo stato di gioco.
- `session_utils.py`: Gestisce le conversazioni e il cambio di contesto tra NPC.
- `chat_manager.py`: Interfaccia con LLM per gestire conversazioni dinamiche.
- `player_profile_manager.py`: Analizza il comportamento del giocatore e aggiorna il suo profilo psicologico.
- `db_manager.py`: Gestisce la persistenza dei dati su database MySQL o file system.
- `llm_wrapper.py`: Interfaccia con OpenRouter per l'accesso a modelli linguistici di grandi dimensioni.
- `terminal_formatter.py`: Formattazione e stili ANSI per l'output terminale.
- `hint_manager.py`: Gestisce il sistema di consulenza con Lyra.

## Requisiti

- Python 3.8+
- Chiave API per OpenRouter
- MySQL (opzionale, supportata modalità file-based)


1. Clona il repository:

   ```bash
   git clone https://github.com/pakkio/nexus.git
   cd nexus
   ```

2. Installa le dipendenze con Poetry:

   ```bash
   # Se non hai già Poetry installato
   pip install poetry
   
   # Installa tutte le dipendenze del progetto
   poetry install
   
   # Attiva l'ambiente virtuale creato da Poetry
   poetry shell
   ```

3. Crea un file .env nella directory principale con le seguenti variabili:

   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
   PROFILE_ANALYSIS_MODEL=google/gemma-2-2b-it:free

   # Solo se usi un database MySQL
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=nexus_db
   `

## Vantaggi dell'Uso di Poetry

Poetry offre diversi benefici rispetto all'approccio con `requirements.txt`:

- **Gestione automatica degli ambienti virtuali**: crea e gestisce un ambiente virtuale dedicato al progetto
- **Risoluzione delle dipendenze**: risolve automaticamente i conflitti tra le dipendenze
- **Blocco delle versioni**: mantiene il file `poetry.lock` che assicura che tutti gli sviluppatori usino esattamente le stesse versioni delle dipendenze
- **Pubblicazione semplificata**: facilita il processo di build e pubblicazione del pacchetto su PyPI

## Esecuzione del Progetto con Poetry

Per eseguire il progetto dopo l'installazione con Poetry:

```bash
# Assicurati di essere nell'ambiente virtuale di Poetry
poetry shell

# Poi esegui il progetto come indicato ad esempio
python main.py --mockup --player TestSeeker --area "Sanctum of Whispers"
```

## Installazione

1. Clona il repository:
   ```bash
   git clone https://github.com/yourusername/nexus-framework.git
   cd nexus-framework
   ```

2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

3. Crea un file `.env` nella directory principale con le seguenti variabili:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
   PROFILE_ANALYSIS_MODEL=google/gemma-2-2b-it:free
   
   # Solo se usi un database MySQL
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=nexus_db
   ```

## Configurazione

Il framework è altamente configurabile attraverso argomenti a linea di comando e file di configurazione:

- **Modalità Database**: Scegli tra database MySQL reale o sistema basato su file con il flag `--mockup`.
- **Modelli LLM**: Configura modelli diversi per il dialogo degli NPC e l'analisi del profilo con `--model` e `--profile-analysis-model`.
- **Streaming**: Abilita o disabilita lo streaming della risposta con `--no-stream`.
- **Statistiche**: Mostra statistiche sulle chiamate LLM con `--show-stats`.

## Esecuzione Rapida

Per avviare rapidamente il framework con impostazioni predefinite:

```bash
# Modalità database file-based (raccomandato per iniziare)
python main.py --mockup --player TestSeeker --area "Sanctum of Whispers"

# Con database MySQL (se configurato)
python main.py --db --player TestSeeker --area "Sanctum of Whispers"

# Con modelli personalizzati
python main.py --mockup --model anthropic/claude-3-opus:beta --profile-analysis-model google/gemma-2-2b-it:free
```

## Utilizzo

Una volta avviato, interagisci con il mondo usando comandi testuali. Ecco i principali:

- **Navigazione**: `/go <area>`, `/areas`, `/whereami`
- **Interazione**: `/talk <npc>`, `/who`, `/npcs`
- **Oggetti e Denaro**: `/inventory`, `/give <item>`, `/give <numero> Credits`
- **Aiuto e Consulenza**: `/hint`, `/endhint`
- **Profilo**: `/profile`, `/profile_for_npc`
- **Statistiche e Debug**: `/stats`, `/session_stats`, `/history`
- **Gestione**: `/clear`, `/exit`

Esempio di sessione:

```
You > ciao, chi sei?

Lyra > Sono Lyra, Custode della Conoscenza Velata e ultima discendente di un antico 
ordine di Guardiani del Velo. Il mio compito è preservare la conoscenza ancestrale 
e guidare coloro che possono aiutare a fermare il collasso del Velo.

You > cosa devo fare?

Lyra > Devi trovare prove della corruzione del Velo. Cerca nei luoghi critici: 
la Foresta, dove Elira potrebbe aiutarti a ottenere un campione della piaga, 
o le Montagne, dove il vecchio Boros conserva testimonianze di una precedente 
rottura del Velo.

You > /go forest

Moving to: Forest...

Elira > The trees weep for what you've burned... o per ciò che il Velo spezzato 
sta distruggendo.
```

## Creazione di NPC e Storie

Il framework utilizza file di testo semplici per definire NPC e storyboard:

### File Storyboard (es. `Storyboard.TheShatteredVeil.txt`)

```
Name: The Shattered Veil
Description:
For centuries, the world of Eldoria has been protected by the Veil, a barrier of
mystical energy separating the material realm from the chaotic magic beyond. Now
the Veil is fraying, and strange anomalies ripple across the land. Each NPC holds
a clue, a key, or a curse connected to this unraveling.

Themes:
- Forgotten truths
- Leaking magic
- Fractured dreams
```

### File NPC (es. `NPC.sanctumofwhispers.lyra.txt`)

```
Name: Lyra
Area: Sanctum of Whispers
Role: Custode della Conoscenza Velata
Motivation: Preservare la conoscenza ancestrale, impedire il collasso del Velo
Goal: Confermare la gravità della rottura del Velo attraverso prove tangibili.
Needed Object: Prove della Rottura
Treasure: La "Mappa delle Ombre Crescenti"
Veil Connection: Discendente diretta dei primi Guardiani del Velo.
PlayerHint: Lyra è la tua guida principale e la fonte di conoscenza sulla crisi del Velo.
Dialogue Hooks:
- "Benvenuto/a, Cercatore/Cercatrice. Sento l'eco dei tuoi passi nel grande disegno del destino."
- "Non sono semplici dicerie o incubi isolati. Il tessuto della realtà si sta logorando."
```

Per caricare nuovi NPC e storie:

```bash
python load.py --mockup --storyboard Storyboard.TheShatteredVeil.txt
```

## Come Contribuire

Apprezziamo contributi e miglioramenti al framework. Ecco come partecipare:

1. Fai un fork del repository
2. Crea un branch per la tua funzionalità (`git checkout -b feature/amazing-feature`)
3. Committa le tue modifiche (`git commit -m 'Add some amazing feature'`)
4. Pusha al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

Aree particolarmente interessanti per contributi:
- Miglioramenti alla logica di analisi del profilo
- Nuovi sistemi di gioco (crafting, combattimento, etc.)
- Ottimizzazioni per i prompt LLM
- Nuove storie e NPCs
- Interfaccia utente migliorata

---

*Nexus Framework è un progetto open source per avventure testuali potenziate da IA.*

Riferimenti:
1. https://github.com/anthropic/claude-documentation - Documentazione Claude
2. https://openrouter.ai/docs - Documentazione OpenRouter API
3. https://github.com/mysql/mysql-connector-python - Connettore MySQL per Python
4. https://pypi.org/project/python-dotenv/ - Gestione variabili d'ambiente
