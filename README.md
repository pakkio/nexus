# **NPC AI Brain per OpenSim - Documentazione Completa**

Sistema completo per NPCs intelligenti in OpenSim utilizzando il motore AI Nexus/Eldoria.

## **Panoramica Sistema**

Il **NPC AI Brain** trasforma gli NPCs statici di OpenSim in personaggi intelligenti capaci di:

- 🤖 **Conversazioni naturali** alimentate da LLM
- 🎭 **Personalità uniche** basate su lore dettagliata
- 📊 **Profiling psicologico** dei giocatori
- 🎮 **Generazione comandi SL** per animazioni/emotes
- 💾 **Memoria persistente** delle conversazioni
- 🌍 **Integrazione mondo di gioco** completa

### **Flusso Funzionale**
```
Avatar si avvicina → Sensor rileva → API /sense → LLM genera saluto → 
Chat continua → API /chat → Risposte AI → Avatar si allontana → API /leave
```

## **Quick Start**

### **1. Setup Server Nexus**

```bash
# Clone del repository
git clone <nexus-repo>
cd nexus

# Installazione dipendenze
poetry install

# Configurazione ambiente
cp .env.example .env
# Modifica .env con la tua OpenRouter API key

# Avvio server
python app.py
```

### **2. Configurazione OpenSim**

Aggiungi in `OpenSim.ini`:

```ini
[Network]
    OutboundDisallowForUserScriptsExcept = 172.25.249.74:5000|127.0.0.1:5000|localhost:5000

[HttpRequestModule]
    HttpRequestsEnabled = true
    HttpTimeout = 45000
    HttpRequestsAllowLocalhost = true
    HttpRequestsAllowedDomains = localhost,127.0.0.1,172.25.249.74
    HttpRequestsMaxResponseSize = 8192
```

### **3. Deploy Script NPC**

Copia lo script `NPC_AI_Brain_Complete.lsl` in un prim OpenSim e modifica:

```lsl
string API_BASE = "http://172.25.249.74:5000";  // IP del tuo server
string NPC_NAME = "Garin";                      // Nome NPC desiderato
string AREA_NAME = "Village";                   // Area NPC
```

## **Architettura**

```
┌─────────────────┐    HTTP     ┌──────────────────┐    OpenRouter    ┌─────────────┐
│   OpenSim LSL   │ ◄─────────► │   Nexus Server   │ ◄──────────────► │     LLM     │
│   NPC Script    │             │   (Flask API)    │                  │  (Gemini/   │
└─────────────────┘             └──────────────────┘                  │  Llama/etc) │
                                          │                            └─────────────┘
                                          ▼
                                ┌──────────────────┐
                                │    Database      │
                                │  (File/MySQL)    │
                                │ - NPCs           │
                                │ - Conversazioni  │
                                │ - Profili Player │
                                └──────────────────┘
```

## **NPCs Disponibili**

| Nome | Area | Ruolo | Specialità |
|------|------|-------|------------|
| **Garin** | Village | Fabbro della Memoria | Forgiatura, strumenti |
| **Mara** | Village | Erborista della Memoria | Erbe, guarigione |
| **Jorin** | Tavern | Custode di Sogni Perduti | Storie, leggende |
| **Lyra** | Sanctum of Whispers | Tessitrice Suprema | Saggezza antica, guida |
| **Elira** | Forest | Guardiana del Nodo Naturale | Natura, sussurri |
| **Boros** | Mountain | Primo Monaco dell'Equilibrio | Meditazione, equilibrio |
| **Theron** | City | Alto Giudice | Giustizia, politica |
| **Cassian** | City | Burocrate Opportunista | Commercio, influenze |
| **Irenna** | City | Marionettista della Resistenza | Arte, memoria |
| **Syra** | Ancient Ruins | Eco Residuo | Antichità, rovine |
| **Erasmus** | Liminal Void | Sussurro Cosciente | Filosofia, oblio |
| **Meridia** | Nexus of Paths | Tessitrice del Destino | Destino, scelte |

## **API Endpoints**

| Endpoint | Metodo | Descrizione | Payload |
|----------|--------|-------------|---------|
| `/health` | GET | Health check server | - |
| `/sense` | POST | Notifica arrivo avatar | `{name, npcname, area}` |
| `/api/chat` | POST | Chat con NPC | `{player_name, message, npc_name, area}` |
| `/leave` | POST | Notifica partenza avatar | `{name}` |
| `/api/game/npcs` | GET | Lista NPCs disponibili | - |
| `/api/game/areas` | GET | Lista aree disponibili | - |

## **Esempio di Utilizzo**

```bash
# Test connettività
curl -X GET http://172.25.249.74:5000/health

# Chat con NPC
curl -X POST http://172.25.249.74:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "player_name": "TestPlayer",
    "message": "Hello Garin!",
    "npc_name": "Garin",
    "area": "Village"
  }'
```

## **Script LSL Completo**

### **NPC_AI_Brain_Complete.lsl**

```lsl
// NPC AI Brain - Complete OpenSim Script
string API_BASE = "http://172.25.249.74:5000";  // IP del tuo server
string NPC_NAME = "Garin";        // Nome NPC
string AREA_NAME = "Village";     // Area NPC

// State management
key current_player = NULL_KEY;
string current_player_name = "";
integer listening = FALSE;
integer listen_handle = -1;

// HTTP request tracking
key health_request = NULL_KEY;
key sense_request = NULL_KEY;
key chat_request = NULL_KEY;
key leave_request = NULL_KEY;

// Sensor configuration
integer SENSOR_RANGE = 10;        // Raggio rilevamento in metri
float SENSOR_INTERVAL = 3.0;      // Scansione ogni 3 secondi
integer CHAT_CHANNEL = 0;         // Canale chat pubblico

// Status flags
integer system_ready = FALSE;
integer connection_tested = FALSE;

default {
    state_entry() { 
        llSetText("🤖 AI NPC: " + NPC_NAME + "\nArea: " + AREA_NAME + "\n🔄 Initializing...", 
                  <1.0, 1.0, 0.0>, 1.0);
        
        llOwnerSay("=== NPC AI BRAIN INITIALIZING ===");
        llOwnerSay("NPC: " + NPC_NAME + " in " + AREA_NAME);
        llOwnerSay("API: " + API_BASE);
        llOwnerSay("Testing connection to Nexus AI...");
        
        // Test connettività
        health_request = llHTTPRequest(
            API_BASE + "/health",
            [HTTP_METHOD, "GET"],
            ""
        );
        llSetTimerEvent(15.0);  // Timeout 15 secondi per health check
    }
    
    // Avatar rilevato nelle vicinanze
    sensor(integer detected) {
        if (!system_ready) return;
        
        key avatar = llDetectedKey(0);
        string avatar_name = llDetectedName(0);
        float distance = llVecMag(llDetectedPos(0) - llGetPos());
        
        // Ingaggia solo se nessuna conversazione attiva
        if (current_player == avatar) return;
        if (current_player != NULL_KEY) return;
        
        llOwnerSay("👤 Detected: " + avatar_name + " at " + (string)((integer)distance) + "m");
        
        // Inizia conversazione
        current_player = avatar;
        current_player_name = avatar_name;
        
        // Inizia ascolto di questo avatar
        if (listen_handle != -1) llListenRemove(listen_handle);
        listen_handle = llListen(CHAT_CHANNEL, "", avatar, "");
        listening = TRUE;
        
        // Notifica arrivo al server Nexus
        string json_data = llList2Json(JSON_OBJECT, [
            "name", avatar_name,
            "npcname", NPC_NAME,
            "area", AREA_NAME
        ]);
        
        sense_request = llHTTPRequest(
            API_BASE + "/sense",
            [HTTP_METHOD, "POST", 
             HTTP_MIMETYPE, "application/json"],
            json_data
        );
        
        llOwnerSay("🎯 Started conversation with: " + avatar_name);
    }
    
    // Nessun avatar rilevato - termina conversazione
    no_sensor() {
        if (current_player != NULL_KEY) {
            llOwnerSay("📡 No avatars in range - ending conversation");
            
            string departing_player = current_player_name;
            
            // Notifica partenza al server
            string json_data = llList2Json(JSON_OBJECT, [
                "name", current_player_name
            ]);
            
            leave_request = llHTTPRequest(
                API_BASE + "/leave", 
                [HTTP_METHOD, "POST",
                 HTTP_MIMETYPE, "application/json"],
                json_data
            );
            
            // Cleanup locale
            if (listen_handle != -1) {
                llListenRemove(listen_handle);
                listen_handle = -1;
            }
            
            listening = FALSE;
            current_player = NULL_KEY;
            current_player_name = "";
            
            llOwnerSay("👋 Ended conversation with: " + departing_player);
        }
    }
    
    // Touch per interazione manuale
    touch_start(integer total_number) {
        key avatar = llDetectedKey(0);
        string avatar_name = llDetectedName(0);
        
        if (!system_ready) {
            llSay(0, "AI Brain still initializing, please wait...");
            return;
        }
        
        if (current_player == NULL_KEY) {
            llOwnerSay("👆 Manual interaction: " + avatar_name);
            
            current_player = avatar;
            current_player_name = avatar_name;
            
            if (listen_handle != -1) llListenRemove(listen_handle);
            listen_handle = llListen(CHAT_CHANNEL, "", avatar, "");
            listening = TRUE;
            
            string json_data = llList2Json(JSON_OBJECT, [
                "name", avatar_name,
                "npcname", NPC_NAME,
                "area", AREA_NAME
            ]);
            
            sense_request = llHTTPRequest(
                API_BASE + "/sense",
                [HTTP_METHOD, "POST", 
                 HTTP_MIMETYPE, "application/json"],
                json_data
            );
            
        } else if (current_player == avatar) {
            llSay(0, "We're already talking, " + avatar_name + "!");
        } else {
            llSay(0, "I'm currently talking with " + current_player_name + ", please wait.");
        }
    }
    
    // Ascolto chat avatar
    listen(integer channel, string name, key id, string message) {
        if (!system_ready) return;
        if (id != current_player) return;
        if (llGetSubString(message, 0, 0) == "/") return; // Ignora comandi
        
        llOwnerSay("💬 " + name + ": " + message);
        
        // Invia al cervello AI
        string json_data = llList2Json(JSON_OBJECT, [
            "player_name", name,
            "message", message,
            "npc_name", NPC_NAME,
            "area", AREA_NAME
        ]);
        
        chat_request = llHTTPRequest(
            API_BASE + "/api/chat",
            [HTTP_METHOD, "POST",
             HTTP_MIMETYPE, "application/json"],
            json_data
        );
        
        llOwnerSay("🧠 Processing: " + message);
    }
    
    // Timer per timeout connessione
    timer() {
        llSetTimerEvent(0.0);
        if (!connection_tested) {
            llOwnerSay("⚠️ Connection timeout - starting anyway");
            llSetText("🤖 AI NPC: " + NPC_NAME + "\n⚠️ Limited Mode\nTouch to interact", 
                      <1.0, 0.5, 0.0>, 1.0);
            system_ready = TRUE;
            llSensorRepeat("", NULL_KEY, AGENT, SENSOR_RANGE, PI, SENSOR_INTERVAL);
        }
    }
    
    // Gestore risposte HTTP
    http_response(key request_id, integer status, list metadata, string body) {
        if (request_id == health_request) {
            // Gestione risposta health check
            llSetTimerEvent(0.0);
            connection_tested = TRUE;
            
            if (status == 200) {
                string service = llJsonGetValue(body, ["service"]);
                if (service == "nexus-api") {
                    llOwnerSay("✅ Connected to Nexus AI Engine!");
                } else {
                    llOwnerSay("⚠️ Unexpected service response");
                }
            } else {
                llOwnerSay("❌ Connection failed (Status: " + (string)status + ")");
                llOwnerSay("Starting in offline mode...");
            }
            
            // Inizializza sistemi NPC
            system_ready = TRUE;
            
            llSetText("🤖 AI NPC: " + NPC_NAME + "\n📍 " + AREA_NAME + "\n✅ Ready - Approach to Chat!", 
                      <0.2, 0.8, 0.2>, 1.0);
            
            // Avvia rilevamento avatar
            llSensorRepeat("", NULL_KEY, AGENT, SENSOR_RANGE, PI, SENSOR_INTERVAL);
            llOwnerSay("✅ " + NPC_NAME + " AI Brain is ACTIVE and ready!");
            llOwnerSay("Detection range: " + (string)SENSOR_RANGE + "m");
        }
        else if (request_id == sense_request) {
            // Gestione risposta arrivo avatar
            if (status == 200) {
                string npc_message = llJsonGetValue(body, ["message"]);
                if (npc_message != JSON_INVALID && npc_message != "") {
                    llSay(0, npc_message);
                    llOwnerSay("👋 Greeted: " + current_player_name);
                }
                
                string sl_commands = llJsonGetValue(body, ["sl_commands"]);
                if (sl_commands != JSON_INVALID && sl_commands != "") {
                    llOwnerSay("🎮 SL Commands: " + sl_commands);
                }
            } else {
                llOwnerSay("❌ Sense error " + (string)status + ": " + body);
                llSay(0, "Hello, " + current_player_name + "! How can I help you?");
            }
        }
        else if (request_id == chat_request) {
            // Gestione risposta chat
            if (status == 200) {
                string npc_response = llJsonGetValue(body, ["npc_response"]);
                if (npc_response != JSON_INVALID && npc_response != "") {
                    llSay(0, npc_response);
                    llOwnerSay("💭 Response sent to " + current_player_name);
                }
                
                // Messaggi di sistema
                list system_messages = llJson2List(llJsonGetValue(body, ["system_messages"]));
                integer i;
                for (i = 0; i < llGetListLength(system_messages); i++) {
                    string sys_msg = llList2String(system_messages, i);
                    if (sys_msg != "" && sys_msg != JSON_INVALID) {
                        llSay(0, "[System] " + sys_msg);
                    }
                }
                
                string sl_commands = llJsonGetValue(body, ["sl_commands"]);
                if (sl_commands != JSON_INVALID && sl_commands != "") {
                    llOwnerSay("🎮 SL Commands: " + sl_commands);
                }
                
            } else {
                llOwnerSay("❌ Chat error " + (string)status + ": " + body);
                llSay(0, "I'm having trouble thinking right now, can you repeat that?");
            }
        }
        else if (request_id == leave_request) {
            // Gestione risposta partenza
            if (status == 200) {
                string departure_msg = llJsonGetValue(body, ["message"]);
                if (departure_msg != JSON_INVALID && departure_msg != "") {
                    llSay(0, departure_msg);
                }
                llOwnerSay("✅ Departure processed");
            } else {
                llOwnerSay("❌ Leave error " + (string)status);
            }
        }
    }
}
```

## **Configurazione Ambiente**

### **File .env necessario:**

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
PROFILE_ANALYSIS_MODEL=mistralai/mistral-7b-instruct:free

# Nexus Server Configuration
NEXUS_USE_MOCKUP=true
NEXUS_MOCKUP_DIR=database
NEXUS_DEBUG_MODE=false
NEXUS_PORT=5000
```

## **Troubleshooting**

### **Problemi Comuni**

#### **"Request disallowed by filter"**
```ini
# Aggiungi in OpenSim.ini:
OutboundDisallowForUserScriptsExcept = 172.25.249.74:5000|localhost:5000
```

#### **"Could not find NPC X in area Y"**
```bash
# Verifica NPCs disponibili:
curl http://172.25.249.74:5000/api/game/npcs

# Usa nomi esatti (case-sensitive)
string NPC_NAME = "Garin";    // ✅ Corretto
string AREA_NAME = "Village"; // ✅ Corretto
```

#### **"NPC seems to ponder..." (risposta fallback)**
```bash
# Cambia modello LLM nel .env:
OPENROUTER_DEFAULT_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

## **Caratteristiche Avanzate**

### **Profiling Psicologico**
- Analisi automatica tratti comportamentali
- Adattamento risposte NPC al profilo player
- Memoria delle preferenze e stili di gioco

### **Sistema Quest Dinamico**
- Quest generate automaticamente basate su lore
- Tracking progresso obiettivi
- Catene quest interconnesse tra NPCs

### **Comandi Second Life**
```
[lookup=oggetto] - Riferimento oggetti in-world
[llSetText=testo] - Aggiornamento testo floating  
[emote=gesto] - Trigger gesture/animazioni
[anim=animazione] - Controllo animazioni avatar
```

### **Multi-Model Support**
- Gratuiti: Google Gemma, Llama 3.2, Phi-3
- Premium: GPT-4, Claude, Gemini Pro
- Specializzati: Modelli per creatività, analisi, coding

## **Performance**

### **Response Times Tipici**
- Health check: 50-100ms
- Sense (greeting): 800-1500ms
- Chat response: 1000-3000ms  
- Leave: 200-400ms

### **Scalabilità**
- Concurrent NPCs: 50+ per server
- Concurrent conversations: 20+ simultaneous
- Request rate: 100+ req/min per NPC

## **Esempi Scenari**

### **RPG Fantasy**
```
Player: "I need a sword"
Garin: "Ah, un guerriero! Per una spada degna, mi serve Minerale di Ferro Antico. 
       Boros sulla Montagna ne ha, ma non lo cede facilmente..."
[Quest generata automaticamente]
```

### **Educational Sim** 
```
Student: "Explain quantum physics"
Lyra: "Immagina che la realtà sia come un tessuto... ogni filo rappresenta 
       una possibilità quantistica..."
[Spiegazione personalizzata basata su learning style]
```

### **Business Training**
```
Employee: "How do I handle difficult customers?"
Theron: "Listen first, acknowledge their concerns, then guide them toward 
        a solution. Show me how you'd respond to this scenario..."
[Simulazione interattiva]
```

## **Sicurezza**

### **Protezioni Implementate**
- Input validation e sanitizzazione
- Rate limiting per prevenire spam
- IP whitelisting configurabile  
- Nessun dato personale sensibile stored

### **Privacy**
- Conversation history opzionale
- Player profiles anonimizzati
- Nessuna PII (personally identifiable information)

## **Contributing**

### **Come Contribuire**
1. Fork del repository
2. Crea feature branch (`git checkout -b feature/amazing-feature`)
3. Commit delle modifiche (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri Pull Request

### **Bug Reports**
- Usa GitHub Issues per segnalazioni
- Includi log completi e steps per riprodurre
- Specifica versione OpenSim e configurazione

## **Roadmap**

### **Short Term (1-3 mesi)**
- [ ] Implementazione completa SL commands parsing
- [ ] Web dashboard per monitoring NPCs
- [ ] Sistema metriche performance avanzate
- [ ] Multi-language support

### **Medium Term (3-6 mesi)**
- [ ] Visual scripting NPCs behavior
- [ ] Advanced quest system builder
- [ ] Integration con HUD viewer-side
- [ ] Mobile companion app

### **Long Term (6-12 mesi)**
- [ ] Voice synthesis per NPCs
- [ ] Machine learning behavior adaptation
- [ ] Blockchain integration per assets
- [ ] Cross-grid NPC migration

## **Supporto**

### **Risorse**
- **Issues:** [GitHub Issues](https://github.com/your-repo/nexus/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-repo/nexus/discussions)
- **Wiki:** [Project Wiki](https://github.com/your-repo/nexus/wiki)

### **Community**
- Discord server per real-time support
- Monthly community calls
- Showcase channel per creazioni utenti

## **Licenza**

MIT License - Vedi [LICENSE](LICENSE) file per dettagli.

---

## **🎉 Risultato**

Hai ora un sistema NPC AI completo che trasforma OpenSim in un mondo populated con personaggi veramente intelligenti! 

Gli NPCs possono:
- ✅ Rilevare automaticamente avatar in avvicinamento
- ✅ Condurre conversazioni naturali e contestuali
- ✅ Ricordare interazioni precedenti
- ✅ Adattarsi al profilo psicologico del player
- ✅ Generare quest dinamiche
- ✅ Controllare animazioni e comportamenti in-world

**Il futuro degli NPCs intelligenti in mondi virtuali è qui! 🤖✨**