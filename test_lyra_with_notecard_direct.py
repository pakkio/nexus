#!/usr/bin/env python3
"""
Test: Lyra gives Memory Preservation Scroll - Direct Feature Verification
Shows what the notecard content looks like when included in Lyra's response
"""

import sys
sys.path.insert(0, '/root/nexus')

from chat_manager import generate_sl_command_prefix

print("="*80)
print("🎯 TEST: Lyra Notecard Feature - Direct Verification")
print("="*80)

# Simulate Lyra's data
lyra_data = {
    "name": "Lyra",
    "area": "Sanctum of Whispers",
    "lookup": "telaio_eco",
    "emote": "hand_offer",
    "anim": "movimenti_tessitura"
}

# The Memory Preservation Scroll content
notecard_content = """# PERGAMENA DI PRESERVAZIONE DELLA MEMORIA

## Il Velo e i Tessitori

I Tessitori crearono il Velo per proteggere la memoria dall'Oblio.
Ma il Velo si indebolisce. I Sussurri dell'Oblio guadagnano forza.

## La Crisi Attuale

Ogni giorno il Velo perde filamenti. Le memorie svaniscono.
I Tessitori hanno sacrificato tutto per mantenerlo.
Ora il loro potere sta cedendo.

## Le Tre Scelte

1. PRESERVARE - Rinnovare il Velo, mantenere lo status quo
2. TRASFORMARE - Evolvere il Velo, permettere il cambiamento
3. DISSOLVERE - Accettare l'Oblio, abbracciare la trasformazione

## La Tua Importanza

Tu, Cercatore, sei il catalizzatore.
Le tue scelte determineranno il destino di Eldoria.
Non è solo una questione di potere - è di saggezza.

Impara da coloro che incontri.
Ascolti i Sussurri ma non lasciarti dominare.
Scegli con il cuore, non con la paura."""

print("\nGenerating SL command with Lyra's notecard...\n")

# Generate the SL command WITH notecard
sl_command = generate_sl_command_prefix(
    npc_data=lyra_data,
    include_notecard=True,
    notecard_content=notecard_content
)

print("Full SL Command:")
print("─" * 80)
print(sl_command)
print("─" * 80)

# Parse and display the notecard
if "[notecard=" in sl_command:
    print("\n✅ NOTECARD COMMAND DETECTED IN SL OUTPUT!\n")
    
    start = sl_command.find("[notecard=")
    end = sl_command.find("]", start) + 1
    notecard_cmd = sl_command[start:end]
    
    # Extract details
    eq_pos = notecard_cmd.find("=")
    pipe_pos = notecard_cmd.find("|")
    
    notecard_name = notecard_cmd[eq_pos+1:pipe_pos]
    content_escaped = notecard_cmd[pipe_pos+1:-1]
    
    print(f"📛 Notecard Name: {notecard_name}")
    print(f"📊 Escaped Content Length: {len(content_escaped)} chars")
    print(f"📊 Content Truncated: {len(content_escaped) <= 1000}")
    
    # Unescape for display
    content_unescaped = content_escaped.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    
    print(f"\n📝 Notecard Content (Unescaped):\n")
    print("─" * 80)
    print(content_unescaped)
    print("─" * 80)
    
    print(f"\n✅ WHAT WOULD HAPPEN IN SECOND LIFE:")
    print(f"   1. LSL script receives this command")
    print(f"   2. Parses: [notecard=Pergamena_Preservazione_Memoria|...]")
    print(f"   3. Unescapes the content")
    print(f"   4. Calls osMakeNotecard('Pergamena_Preservazione_Memoria', lines)")
    print(f"   5. Gives to player via llGiveInventory()")
    print(f"   6. Player receives notecard in inventory")
    print(f"   7. Can read anytime - PERSISTENT!")

print("\n" + "="*80)
print("✅ Lyra's Notecard Feature Ready for Integration")
print("="*80)

print("""
Integration Example:
When player brings Cristallo di Memoria Antica to Lyra, the system should:

1. LLM generates Lyra's response with embedded notecard command:
   "Sì... posso sentire le memorie antiche nel cristallo. Hai fatto bene a portarmelo.
   [notecard=Pergamena_Preservazione_Memoria|# PERGAMENA DI PRESERVAZIONE...]"

2. Chat system includes this in the response to player

3. LSL script in Second Life:
   - Detects [notecard=...] in the message
   - Extracts and unescapes the content
   - Creates persistent notecard via osMakeNotecard()
   - Gives to player

4. Player receives "Pergamena_Preservazione_Memoria" notecard
   - Contains full antefatto and story context
   - Persistent - survives session restart
   - Can be read anytime for reference

This provides immersive storytelling through persistent documents!
""")

print("="*80 + "\n")
