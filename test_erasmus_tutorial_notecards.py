#!/usr/bin/env python3
"""
Test: Erasmus as First NPC - Tutorial Notecards
Shows the guide notecards Erasmus gives to new players
"""

import sys
sys.path.insert(0, '/root/nexus')

from chat_manager import generate_sl_command_prefix

print("="*80)
print("🎯 TEST: Erasmus Tutorial Notecards (First NPC)")
print("="*80)

erasmus_data = {
    "name": "Erasmus",
    "area": "Liminal Void",
    "lookup": "void_portal",
    "emote": "ethereal_drift",
    "anim": "liminal_floating"
}

# Erasmus's tutorial notecards for new players
tutorials = {
    "Game Rules": """# GUIDA ALLE REGOLE DI ELDORIA

Benvenuto, Cercastorie, nel mondo di Eldoria.
Ecco le regole fondamentali:

## La Ricerca
Tu sei un Cercastorie - uno che cerca il significato e la verità
nel nostro mondo mutevole. Le tue scelte modellano il tuo destino.

## Le Aree
Eldoria è divisa in molte aree. Ogni area ha i suoi NPG (personaggi),
storie, oggetti e sfide. Esplora con cura.

## Gli Oggetti
Raccogli gli oggetti che trovi. Molti NPG vogliono determinati oggetti
in cambio di ricompense, sapienza, e accesso a nuove aree.

## I Crediti
I crediti sono la valuta di Eldoria. Guadagnali completando
compiti per gli NPG. Usali per acquistare oggetti o servizi.

## Le Scelte
Ogni scelta che fai ha conseguenze. Non ci sono scelte "giuste" -
solo scelte che riflettono chi tu sei veramente.""",

    "Commands": """# COMANDI DI ELDORIA

Questi comandi ti aiuteranno a navigare il tuo viaggio:

## Navigazione
/go <area> - Vai in un'area diversa
/areas - Vedi tutte le aree disponibili
/describe <area> - Ottieni descrizione di un'area
/whereami - Vedi la tua posizione attuale

## Interazione
/talk <npc_name> - Parla con un NPG
/who - Vedi gli NPG nell'area attuale
/npcs - Vedi tutti gli NPG conosciuti
/give <item> [to <npc>] - Dai un oggetto a un NPG

## Informazioni
/inventory o /inv - Vedi il tuo inventario
/stats - Vedi le tue statistiche
/profile - Vedi il tuo profilo psicologico
/history - Vedi la cronologia delle conversazioni
/hint - Chiedi consiglio al saggio Guida

## Aiuto
/help - Vedi tutti i comandi
/exit o /quit - Esci dal gioco""",

    "Story Overview": """# LA STORIA DI ELDORIA - ANTEFATTO

## Il Velo dei Tessitori

Molto tempo fa, i Tessitori crearono il Velo - una barriera
per proteggere le memorie di Eldoria dall'Oblio.

## La Crisi Attuale

Oggi il Velo si indebolisce. I Sussurri dell'Oblio guadagnano forza.
Le memorie svaniscono. I Tessitori hanno sacrificato tutto
per mantenerlo, ma il loro potere sta cedendo.

## Le Tre Scelte

Tu, Cercastorie, stai al crocevia di tre strade:

1. PRESERVARE - Rinnovare il Velo, mantenere l'ordine di Eldoria
2. TRASFORMARE - Evolverlo, permettere il cambiamento graduale
3. DISSOLVERE - Accettare l'Oblio, abbracciare la trasformazione

## Il Tuo Ruolo

Le tue scelte determineranno il destino di Eldoria.
Ascolta i diversi punti di vista. Impara da coloro che incontri.
La saggezza viene dall'esperienza.""",

    "Key Targets": """# OBIETTIVI CHIAVE DI ELDORIA

## NPG Principali da Incontrare

LYRA (Sanctum of Whispers)
Tessitrice Suprema - Custode delle memorie e della saggezza.
Insegna sulla preservazione e il significato del Velo.

THERON (Città)
Guerriero e Filosofo - Combatte per la libertà di Eldoria.
Offre perspectiva sulla resistenza all'Oblio.

SYRA (Rovine Antiche)
Archeologa e Tessitura - Custodisce i segreti del passato.
Rivela la vera storia del Velo e dei Tessitori.

BOROS (Montagna)
Saggio e Osservatore - Comprende i cicli naturali.
Offre prospectiva sugli equilibri cosmici.

JORIN (Taverna)
Locandiere e Collezionista - Conserva i sogni e le storie.
Rivela i misteriosi effetti dell'Oblio.

## Aree da Esplorare

- Sanctum of Whispers: Centro di saggezza
- Città: Hub di comunità e resistenza
- Rovine Antiche: Segreti del passato
- Montagna: Prospectiva cosmica
- Taverna: Storie e connessioni
- Foresta: Natura e compassione

## La Tua Missione

1. Incontra i principali NPG
2. Ascolta le loro prospettive
3. Raccogli oggetti e sapienza
4. Comprendi le tre scelte
5. Decidi il destino di Eldoria"""
}

print("\nGenerating Erasmus's Tutorial Notecards...\n")

for title, content in tutorials.items():
    print("─" * 80)
    print(f"📋 {title}")
    print("─" * 80)
    
    # Create notecard name
    notecard_name = title.replace(" ", "_").replace(":", "")
    
    # Generate SL command
    sl_command = generate_sl_command_prefix(
        npc_data=erasmus_data,
        include_notecard=True,
        notecard_content=content
    )
    
    # Parse the command
    if "[notecard=" in sl_command:
        start = sl_command.find("[notecard=")
        end = sl_command.find("]", start) + 1
        notecard_cmd = sl_command[start:end]
        
        eq_pos = notecard_cmd.find("=")
        pipe_pos = notecard_cmd.find("|")
        
        name = notecard_cmd[eq_pos+1:pipe_pos]
        content_escaped = notecard_cmd[pipe_pos+1:-1]
        
        print(f"✅ Notecard Name: {name}")
        print(f"✅ Content Length: {len(content_escaped)} chars (escaped)")
        print(f"✅ Within Limit: {len(content_escaped) <= 1000}")
        
        # Show content preview
        content_unescaped = content_escaped.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        preview = content_unescaped[:200] if len(content_unescaped) > 200 else content_unescaped
        print(f"\nPreview:\n{preview}...")
    
    print()

print("="*80)
print("✅ Erasmus's Tutorial System")
print("="*80)

print("""
NEW ROLE FOR ERASMUS:

As the first NPC encountered, Erasmus now serves dual purposes:

1. PHILOSOPHICAL GUIDE (existing)
   - Offers perspective on Oblivion
   - Explains cosmic transformation
   - Respects player choice

2. TUTORIAL GUIDE (new!)
   - Gives Game Rules notecard
   - Provides Commands reference
   - Explains Story Overview
   - Lists Key NPG Targets

PLAYER EXPERIENCE:

First Meeting with Erasmus:
1. Player: "Hello Erasmus..."
2. Erasmus: [Gives philosophical greeting]
   [notecard=Guida_Regole|# GUIDA ALLE REGOLE...]
   [notecard=Comandi|# COMANDI DI ELDORIA...]
   [notecard=Antefatto_Breve|# LA STORIA DI ELDORIA...]
   [notecard=Obiettivi_Chiave|# OBIETTIVI CHIAVE...]

3. Player receives 4 tutorial notecards in inventory
4. Can reference anytime during gameplay
5. Helps new players understand game mechanics
6. Maintains immersion through mystical framing

CHARACTER INTEGRATION:

Erasmus's role as "bridge consciousness" naturally extends
to being a guide/mentor. His philosophical nature makes him
the perfect character to:
- Welcome new players
- Explain the world and rules
- Point toward key NPCs
- Maintain mystical atmosphere while being helpful

This is perfect character consistency!
""")

print("="*80 + "\n")
