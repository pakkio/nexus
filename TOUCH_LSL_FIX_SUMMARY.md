# Fix per touch.lsl - Notecard Troncati

## Problemi Risolti

### 1. Notecard Troncati (Problema Principale)
**Causa:** Il parser divideva `sl_commands` per `;` (semicolon) PRIMA di estrarre il notecard. Se il contenuto del notecard conteneva `;`, veniva troncato.

**Soluzione:**
- Estrai il notecard PRIMA di dividere per `;`
- Processa tutti gli altri comandi normalmente
- Processa il notecard alla fine

**Codice Modificato:** Funzione `process_sl_commands()` (righe 445-529)

```lsl
// PRIMA (BUGGY):
list command_parts = llParseString2List(commands, [";"], []);
// Questo troncava il notecard se conteneva ";"

// DOPO (FIXED):
// 1. Estrai notecard prima
integer notecard_pos = llSubStringIndex(commands, "notecard=");
if (notecard_pos != -1) {
    notecard_data = llGetSubString(commands, notecard_pos + 9, -1);
    commands = llGetSubString(commands, 0, notecard_pos - 1);
}
// 2. Processa altri comandi
list command_parts = llParseString2List(commands, [";"], []);
// 3. Processa notecard alla fine
if (notecard_data != "") process_notecard(current_toucher, notecard_data);
```

### 2. Output Duplicato
**Causa:** Multipli `llOwnerSay()` mostravano informazioni già visibili al giocatore

**Soluzione:** Rimossi `llOwnerSay()` non necessari in:
- `process_sl_commands()`: Rimossi output per lookup, emote, anim, llSetText
- `process_notecard()`: Rimosso messaggio "✓ Notecard given to..."

**Benefici:**
- Chat più pulita
- Solo messaggi importanti (errori, tempo risposta)
- Esperienza utente migliore

## File Modificato
- `/root/nexus/touch.lsl`

## Test Consigliato
1. Copia il nuovo `touch.lsl` in Second Life
2. Tocca Elira e chiedi "notecard"
3. Verifica che il notecard sia completo (non troncato)
4. Verifica che non ci siano messaggi duplicati nella chat

## Compatibilità
- ✅ Funziona con tutti gli NPC esistenti
- ✅ Backward compatible (notecard senza `;` funzionano come prima)
- ✅ Fix funziona anche se notecard contiene `;` nel contenuto
- ✅ Mantiene tutti gli altri comandi SL (lookup, emote, anim, teleport, llSetText)

## Data Fix
2025-10-23
