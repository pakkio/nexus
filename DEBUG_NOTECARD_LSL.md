# DEBUG: Notecard Troncato in Second Life

## Situazione
- **Server Python**: Invia notecard COMPLETO (501 caratteri con `]` finale) ✓
- **Second Life**: Notecard appare troncato quando visualizzato

## Notecard Inviato dal Server
```
notecard=Segreti_della_Foresta|# SAGGEZZA DI ELIRA\nGuardiana del Nodo Primordiale\n\nCHI SONO:\nSono Elira, unita alla Foresta Sacra.\nIl mio spirito si intreccia con ogni albero.\n\nLA MIA MISSIONE:\nProteggere il Nodo dove i Tessitori si sacrificarono.\nValutare chi e' degno di accedere alla conoscenza antica.\n\nCOSA CERCO:\nCompassione sincera per la natura.\nCapacita' di ascoltare senza dominare.\n\nCOME SUPERARE LA PROVA:\n1. Porta una Pozione di Guarigione da Mara\n2. Oppure convincimi con parole di compassione sincera]
```

## Possibili Cause Lato LSL

### 1. Funzione `unescape_notecard_content()` (touch.lsl righe 563-607)
Questa funzione converte `\\n` (backslash + n) in newline reali.

**Problema potenziale**:
- Il server invia `\n` come DUE caratteri: `\` + `n`
- LSL dovrebbe convertirli in un solo carattere newline
- Se la conversione fallisce, il notecard sarà tutto su una riga

### 2. Funzione `osMakeNotecard()` (touch.lsl riga 553)
```lsl
list notecard_lines = llParseString2List(content, ["\n"], []);
osMakeNotecard(notecard_name, notecard_lines);
```

**Problema potenziale**:
- `llParseString2List()` divide il contenuto per `\n` (newline REALE)
- Se `unescape_notecard_content()` non ha convertito `\\n` → `\n`, la lista avrà 1 sola riga lunghissima
- OpenSim potrebbe troncare righe troppo lunghe nel notecard

### 3. Limite Heap/Stack LSL
- LSL ha limite di memoria heap (~64KB in SL, variabile in OpenSim)
- Contenuto lungo + parsing potrebbe saturare l'heap
- Risultato: script crash o troncamento silenzioso

## Soluzioni da Testare

### Opzione A: Debug LSL Console
Aggiungi `llOwnerSay()` in `process_notecard()` per vedere:
```lsl
llOwnerSay("Notecard name: " + notecard_name);
llOwnerSay("Escaped content length: " + (string)llStringLength(escaped_content));
llOwnerSay("Unescaped content length: " + (string)llStringLength(content));
llOwnerSay("Number of lines: " + (string)llGetListLength(notecard_lines));
llOwnerSay("First line: " + llList2String(notecard_lines, 0));
```

### Opzione B: Ridurre Contenuto Notecard
Se il problema è la lunghezza, abbrevia il contenuto nel file `NPC.forest.elira.txt`:
```
# SAGGEZZA DI ELIRA

Sono unita alla Foresta Sacra.

MISSIONE: Proteggere il Nodo Primordiale.

PROVA: Porta Pozione di Guarigione da Mara
O dimostra compassione sincera.
```

### Opzione C: Cambiare Formato Escape
Invece di `\n`, usare `~` come separatore e convertirlo in LSL:
```lsl
content = llDumpList2String(llParseString2List(content, ["~"], []), "\n");
```

Modificare app.py per usare `~` invece di `\n` nel notecard.

## Prossimo Step
**Lorenza**: Puoi verificare nella console di Second Life (chat) se vedi messaggi di debug quando tocchi Elira e chiedi notecard?

Oppure posso modificare il contenuto del notecard di Elira per renderlo più breve e testare se funziona.
