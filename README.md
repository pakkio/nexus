# 🌟 Nexus Framework
### *Il Futuro delle Avventure Testuali è Qui*

---

## 🎭 Introduzione

**Nexus** non è l'ennesimo motore per avventure testuali. È una **rivoluzione narrativa** che porta l'intelligenza artificiale nel cuore della storytelling interattiva. Immagina un mondo dove i personaggi non solo rispondono alle tue azioni, ma ti *ricordano*, ti *studiano*, e si *adattano* al tuo stile di gioco.

Attualmente implementa **"The Shattered Veil"**, un'epica avventura ambientata nel misterioso mondo di **Eldoria**, dove una barriera mistica che protegge la realtà si sta sgretolando sotto i tuoi occhi.

---

## ✨ Caratteristiche che Cambiano le Regole del Gioco

### 🧠 **NPCs con Memoria Persistente**
Non più dialoghi robotici: i personaggi ricordano ogni conversazione, ogni scelta, ogni momento condiviso. La narrazione diventa un **tessuto vivente** di relazioni autentiche.

### 🎯 **Profilo Psicologico Dinamico**
Il sistema *ti osserva mentre giochi*, costruendo un profilo psicologico che influenza come il mondo reagisce a te. Sei diplomatico? Aggressivo? Curioso? Gli NPCs se ne accorgeranno.

### 🎨 **Adattamento Intelligente**
Ogni personaggio modifica il proprio comportamento in base a chi sei e a come ti comporti. Un'esperienza **davvero personalizzata**.

### 💻 **Interfaccia Elegante**
Sistema di comandi intuitivo con **formattazione ANSI** che trasforma il terminale in una finestra su mondi fantastici.

### 🗃️ **Database Flessibile**
Supporto completo per **MySQL** con fallback intelligente su file JSON. La tua avventura è sempre al sicuro.

### 🤖 **Integrazione LLM Avanzata**
Wrapper sofisticato per **OpenRouter** che supporta i migliori modelli linguistici disponibili. Gestione separata dei modelli per dialoghi NPCs e analisi psicologica del giocatore.

### 🔮 **Sistema di Consulenza Integrato**
Il comando `/hint` ti connette con **Lyra**, un'oracolo digitale che mantiene cache intelligente dei consigli basati sul contesto di gioco.

### 🎒 **Economia di Gioco Completa**
Sistema di inventario e crediti che aggiunge profondità strategica alle tue scelte.

### ⚡ **Sistema di Reset Intelligente**
Script di reset integrato per ripulire stati di gioco, database e profili giocatore quando necessario.

---

## 🏗️ Architettura del Sistema

Il framework è costruito con una **architettura modulare** che respira eleganza e flessibilità:

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ main.py         │──────│ main_core.py    │──────│ command_processor│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│ db_manager.py   │◄─────│ session_utils   │◄─────│ chat_manager    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│player_profile_  │◄─────│ hint_manager    │◄─────│ llm_wrapper     │
│ manager         │      │                 │      │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 🧩 **Componenti Chiave**

- **`main.py`** - *Il portale d'ingresso*: gestisce argomenti avanzati inclusi modelli separati per dialoghi e analisi profilo
- **`main_core.py`** - *Il cuore pulsante*: coordina il loop principale con aggiornamenti del profilo giocatore tramite LLM
- **`command_processor.py`** - *L'interprete*: gestisce 15+ comandi specializzati con tracking azioni per profilo psicologico
- **`session_utils.py`** - *Il regista*: orchestra conversazioni con integrazione insights psicologici nel system prompt degli NPCs
- **`chat_manager.py`** - *Il ponte*: interfaccia streaming con statistiche dettagliate (token, tempi, performance)
- **`player_profile_manager.py`** - *Lo psicologo*: analisi LLM-based con extraction JSON robusta per profili comportamentali
- **`db_manager.py`** - *La memoria*: supporto MySQL completo + fallback JSON con schema player profiles avanzato
- **`llm_wrapper.py`** - *Il traduttore*: client OpenRouter con gestione errori, logging e supporto streaming SSE
- **`terminal_formatter.py`** - *L'artista*: formattazione ANSI avanzata con supporto Markdown-like (bold, italic, colori)
- **`hint_manager.py`** - *Il consigliere*: sistema di cache intelligente per consigli contestuali di Lyra
- **`load.py`** - *Il costruttore*: parser per NPCs e storyboard con supporto encoding UTF-8

---

## 🚀 Setup Rapido

### **Requisiti Minimi**
- **Python 3.8+** (il linguaggio degli dei)
- **Chiave API OpenRouter** (il passaporto per l'IA)
- **MySQL** *(opzionale, ma consigliato per l'esperienza completa)*

### **Installazione con Poetry** *(Raccomandato)*

```bash
# Clona il futuro
git clone https://github.com/pakkio/nexus.git
cd nexus

# Preparati alla magia
pip install poetry
poetry install
poetry shell
```

**Perché Poetry?** Perché la vita è troppo breve per gestire dipendenze manualmente:
- ✅ **Ambienti virtuali automatici**
- ✅ **Risoluzione intelligente dei conflitti**
- ✅ **Versioni bloccate e riproducibili**
- ✅ **Pubblicazione su PyPI semplificata**

### **Installazione Tradizionale**

```bash
# Per i puristi
git clone https://github.com/pakkio/nexus.git
cd nexus
pip install -r requirements.txt
```

### **Configurazione Ambientale**

Crea il file `.env` nella directory principale con le tue credenziali:

```env
OPENROUTER_API_KEY=your_actual_openrouter_api_key_here
OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
PROFILE_ANALYSIS_MODEL=google/gemma-2-2b-it:free
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=nexus_db
```

**⚠️ IMPORTANTE:** L'`OPENROUER_API_KEY` deve essere una chiave API valida ottenuta da [OpenRouter](https://openrouter.ai). Senza questa chiave, il sistema non potrà effettuare chiamate LLM.

---

## 🎮 Lanciare la Tua Avventura

### **Avvio Immediato**
```bash
# Con Poetry
poetry shell
python main.py --mockup --player TestSeeker --area "Sanctum of Whispers"

# Modalità database completa
python main.py --db --player TestSeeker --area "Sanctum of Whispers"

# Con modelli premium
python main.py --mockup --model anthropic/claude-3-opus:beta --profile-analysis-model google/gemma-2-2b-it:free
```

### **Opzioni di Configurazione Avanzate**

- **`--mockup`** / **`--db`** - Scegli tra file JSON o database MySQL
- **`--model`** - Specifica il modello LLM per i dialoghi
- **`--profile-analysis-model`** - Modello per l'analisi psicologica
- **`--no-stream`** - Disabilita lo streaming delle risposte
- **`--show-stats`** - Mostra statistiche dettagliate sulle chiamate LLM

---

## 🕹️ Comandi di Gioco

Una volta nel mondo di Eldoria, usa questi comandi per plasmarlo:

### **🗺️ Navigazione**
- `/go <area>` - Viaggia verso nuove terre
- `/areas` - Scopri tutti i luoghi disponibili
- `/whereami` - Dove ti trovi ora?

### **👥 Interazione Sociale**
- `/talk <npc>` - Inizia una conversazione
- `/who` - Chi c'è qui con te?
- `/npcs` - Lista tutti i personaggi disponibili

### **🎒 Gestione Risorse**
- `/inventory` - Controlla i tuoi oggetti
- `/give <item>` - Dona un oggetto
- `/give <numero> Credits` - Trasferisci denaro

### **🔮 Saggezza e Aiuto**
- `/hint` - Consulta l'oracolo Lyra
- `/endhint` - Termina la consultazione

### **📊 Informazioni e Debug**
- `/profile` - Il tuo profilo psicologico
- `/profile_for_npc` - Come ti vedono gli NPCs
- `/stats` - Statistiche di gioco
- `/session_stats` - Dati della sessione corrente
- `/history` - Cronologia delle tue azioni

### **⚙️ Gestione Sistema**
- `/clear` - Pulisci lo schermo
- `/exit` - Termina l'avventura
- `/stats` - Statistiche complete delle chiamate LLM (token, tempi, modelli)
- `/session_stats` - Statistiche della sessione corrente
- `/history` - Cronologia completa delle tue azioni

### **🔧 Strumenti di Sviluppo**
- `python load.py --mockup --storyboard <file>` - Carica nuovi contenuti
- Script di reset per database e profili giocatore
- Modalità debug con logging avanzato

---

## 🎬 Esempio di Sessione

```
You > ciao, chi sei?

Lyra > Sono Lyra, Custode della Conoscenza Velata e ultima discendente 
       di un antico ordine di Guardiani del Velo. Il mio compito è 
       preservare la conoscenza ancestrale e guidare coloro che possono 
       aiutare a fermare il collasso del Velo.

You > cosa devo fare?

Lyra > Devi trovare prove della corruzione del Velo. Cerca nei luoghi 
       critici: la Foresta, dove Elira potrebbe aiutarti a ottenere un 
       campione della piaga, o le Montagne, dove il vecchio Boros 
       conserva testimonianze di una precedente rottura del Velo.

You > /go forest

Moving to: Forest...

Elira > The trees weep for what you've burned... o per ciò che il Velo 
        spezzato sta distruggendo.

You > /profile

[Profilo Psicologico Dettagliato]
- Curiosità: 7/10 (Aumentata dalle domande frequenti)
- Cautela: 5/10 (Approccio equilibrato ai pericoli)
- Empatia: 6/10 (Interesse per la sofferenza di Elira)
```

---

## 🛠️ Creazione di Contenuti

### **📜 Definire Nuove Storie**

I file storyboard definiscono l'ambientazione generale:

```
Name: The Shattered Veil
Description:
For centuries, the world of Eldoria has been protected by the Veil, 
a barrier of mystical energy separating the material realm from the 
chaotic magic beyond. Now the Veil is fraying, and strange anomalies 
ripple across the land.

Themes:
- Forgotten truths
- Leaking magic  
- Fractured dreams
```

### **👤 Progettare NPCs Memorabili**

Il sistema supporta NPCs complessi con motivazioni strutturate:

```
Name: Lyra
Area: Sanctum of Whispers
Role: Custode della Conoscenza Velata
Motivation: Preservare la conoscenza ancestrale
Goal: Confermare la gravità della rottura del Velo
Needed Object: Prove della Rottura
Treasure: La "Mappa delle Ombre Crescenti"
Veil Connection: Discendente diretta dei primi Guardiani

Dialogue Hooks:
- "Benvenuto/a, Cercatore. Sento l'eco dei tuoi passi nel destino."
- "Il tessuto della realtà si sta logorando davanti ai nostri occhi."
```

**NPCs Disponibili nel Mondo di Eldoria:**
- **Lyra** (Sanctum) - La guida saggia, custode dei segreti del Velo
- **Elira** (Forest) - Guardiana della natura, soffre con la sua foresta corrotta
- **Boros** (Mountain) - Guerriero in pensione, testimone di antiche catastrofi
- **Jorin** (Tavern) - Oste collezionista di sussurri e sogni infranti
- **Garin** (Village) - Fabbro erede di una tradizione della Guerra del Velo
- **Syra** (Ancient Ruins) - Spirito guardiano legato ai Sigilli ancestrali
- **Theron** (City) - Alto Giudice corrotto, antagonista principale

### **⚡ Caricamento Contenuti**

```bash
# Carica nuovi NPCs e storie
python load.py --mockup --storyboard Storyboard.TheShatteredVeil.txt

# Reset completo del sistema (carica tutti i dati di default)
./reset_game

# Avvio rapido dopo reset
python main.py --mockup --player TestSeeker --area "Sanctum of Whispers"

# Debug e test con statistiche
python main.py --mockup --show-stats --model anthropic/claude-3-opus:beta
```

**Script `reset_game`:** Combina pulizia database + ricaricamento dati + inizializzazione sistema. Perfetto per reset rapidi durante sviluppo.

---

## 🤝 Contribuire al Progetto

Il **Nexus Framework** cresce grazie alla community. Ecco come unirti all'avventura:

### **🔧 Processo di Contribuzione**

1. **Fork** del repository
2. **Crea** un branch per la tua feature (`git checkout -b feature/amazing-feature`)
3. **Committa** le modifiche (`git commit -m 'Add some amazing feature'`)
4. **Push** al branch (`git push origin feature/amazing-feature`)
5. **Apri** una Pull Request

### **🎯 Aree di Interesse**

- **🧠 Miglioramenti AI** - Logica di analisi del profilo più sofisticata
- **🎮 Nuovi Sistemi** - Crafting, combattimento, magia
- **⚡ Ottimizzazioni** - Prompt LLM più efficienti
- **📚 Contenuti** - Nuove storie e personaggi indimenticabili
- **🎨 UX/UI** - Interfaccia sempre più elegante e intuitiva

---

## 🚨 Troubleshooting

### **Errore 401: "No auth credentials found"**

**Problema:** Il sistema non trova le credenziali OpenRouter API.

**Soluzioni:**
```bash
# 1. Verifica che il file .env esista
ls -la .env

# 2. Controlla il contenuto del file .env
cat .env

# 3. Assicurati che la chiave API sia valida
# Visita https://openrouter.ai/settings/keys per ottenere/verificare la tua chiave

# 4. Riavvia il framework dopo aver modificato .env
python main.py --mockup --player TestSeeker --area "Sanctum of Whispers"
```

### **NPCs non rispondono / Chiamate LLM falliscono**

**Cause comuni:**
- API key OpenRouter scaduta o non valida
- Crediti insufficienti su OpenRouter
- Modello LLM non disponibile

**Debug:**
```bash
# Testa con modelli gratuiti confermati
python main.py --mockup --model google/gemma-2-9b-it:free --profile-analysis-model google/gemma-2-2b-it:free --show-stats
```

### **Database MySQL non funziona**

**Usa la modalità mockup per test rapidi:**
```bash
# Modalità file-based (no MySQL richiesto)
python main.py --mockup --player TestSeeker

# Reset completo del sistema
./reset_game
```

### **Errori di import/dipendenze**

**Con Poetry:**
```bash
poetry install --sync
poetry shell
```

**Con pip:**
```bash
pip install -r requirements.txt --upgrade
```

### **Performance Lenta**

**Ottimizzazioni:**
- Usa modelli più piccoli per profile analysis: `google/gemma-2-2b-it:free`
- Disabilita streaming se non necessario: `--no-stream`
- Monitora l'uso con: `--show-stats`

---

## 🏆 Conclusione

**Nexus Framework** rappresenta l'evoluzione naturale della narrativa interattiva. Non stiamo solo creando giochi - stiamo **forgiando mondi vivi** dove ogni scelta conta, ogni personaggio respira, e ogni storia si adatta a chi la vive.

Il sistema di *profiling psicologico* basato su LLM trasforma ogni sessione in un'esperienza unica, mentre la *memoria persistente* degli NPCs crea narrazioni che crescono organicamente con il tempo. La flessibilità architetturale permette di estendere facilmente il framework con nuovi sistemi di gioco.

**Nexus** è più di un motore - è una **piattaforma per l'immaginazione**.

---

## 📚 Riferimenti

- [Documentazione Claude](https://docs.anthropic.com/) - Guida completa all'API Claude
- [OpenRouter API](https://openrouter.ai/docs) - Documentazione per l'accesso ai modelli LLM
- [MySQL Connector Python](https://github.com/mysql/mysql-connector-python) - Connettore ufficiale MySQL
- [Python-dotenv](https://pypi.org/project/python-dotenv/) - Gestione elegante delle variabili d'ambiente
- [Poetry Documentation](https://python-poetry.org/docs/) - Gestione dipendenze moderna
- [ANSI Color Codes](https://en.wikipedia.org/wiki/ANSI_escape_code) - Formattazione terminale avanzata
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) - Streaming protocol per LLM responses

---

*Nexus Framework - Dove l'Intelligenza Artificiale Incontra l'Immaginazione*

**Licenza:** MIT | **Linguaggio:** Python 3.8+ | **Stato:** Attivo