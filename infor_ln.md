# Infor LN - Baan 4GL Language Guide

Guida rapida al linguaggio di programmazione Baan 4GL utilizzato in Infor LN (ex Baan ERP).

## Struttura Base del Programma

```baan
|******************************************************************************
|* Nome programma  versione  descrizione
|* Titolo
|* Autore
|* Data
|******************************************************************************

|****************************** declaration section ***************************
declaration:

    #ident "@(#)identificatore versione data autore"

    |* Dichiarazione tabelle
    table    ttnomeDB    |* Commento descrizione

    |* Variabili esterne (form variables)
    extern    domain    tipoDomain    nome.variabile

    |* Variabili locali
        domain    tipoDomain    variabile.locale
            long        contatore
            boolean        flag

    |* Include files
    #include <bic_dam>
    #include "itcmcs2000"

|****************************** program section *******************************
before.program:
    |* Codice eseguito all'avvio

|****************************** group section **********************************
group.1:
init.group:
    |* Inizializzazione gruppo

|****************************** field section **********************************
field.nome.campo:
before.zoom:
    |* Codice prima della lookup
when.field.changes:
    |* Codice quando il campo cambia
check.input:
    |* Validazione input

|****************************** choice section ********************************
choice.nome.scelta:
before.choice:
    |* Codice prima dell'esecuzione
on.choice:
    |* Codice eseguito
after.choice:
    |* Codice dopo l'esecuzione

|****************************** functions section ******************************
functions:

function tipo nome.funzione(parametri)
{
    |* Corpo funzione
}
```

## Tipi di Dati (Domains)

```baan
domain    tcorno        |* Order Number (stringa)
domain    tcdate        |* Data
domain    tcamnt        |* Importo
domain    tcqty         |* Quantità
domain    tcyesno       |* Yes/No (boolean)
domain    tcdsca        |* Descrizione
domain    tcpono        |* Position Number (long)
```

## Dichiarazione Variabili

```baan
|* Variabile esterna (visibile nel form)
extern    domain    tcorno        sales.order

|* Variabile locale
    domain    tcdate        data.inizio
        long        contatore
        boolean        flag.trovato

|* Array
    domain    tcorno        ordini(100)

|* Array based (allocazione dinamica)
    domain    tcorno        ordini.array(1) based
```

## Query Database (SELECT)

### Select Base
```baan
select    tabella.campo1, tabella.campo2
from    tabella
where    tabella.campo = :variabile
selectdo
    |* Elaborazione per ogni record
endselect
```

### Select con Range
```baan
select    tdsls400.*
from    tdsls400
where    tdsls400._index1 inrange {:order.f} and {:order.t}
and    tdsls400.odat between :date.f and :date.t
selectdo
    |* Elaborazione
endselect
```

### Select con Aggregate
```baan
select    sum(campo):totale,
        count(*):numero.righe
from    tabella
where    tabella.chiave = {:valore}
selectdo
endselect
```

### Select con Exists
```baan
and    not exists (    select    tabella2.*
                from    tabella2
                where    tabella2.campo = {tabella1.campo})
```

### Select con Join
```baan
select    tab1.*, tab2.*
from    tab1, tab2
where    tab1._index1 = {:chiave}
and    tab2._index1 = {tab1.campo}
selectdo
endselect
```

### Set Limit
```baan
as set with 1 rows    |* Limita a 1 record
```

## Operazioni Database (DAL - Data Access Layer)

### Inserimento Record
```baan
dal.new.object("nometabella")
dal.set.field("tabella.campo1", valore1)
dal.set.field("tabella.campo2", valore2)
ret = dal.save.object("nometabella")

if ret = 0 then
    commit.transaction()
else
    abort.transaction()
endif
```

### Update Record
```baan
db.retry.point()
select    tabella.*
from    tabella
where    tabella._index1 = {:chiave}
for update
selectdo
    tabella.campo = nuovo.valore
    db.update(tabella, DB.RETRY)
endselect
commit.transaction()
```

## Controlli Condizionali

### If-Then-Else
```baan
if condizione then
    |* codice
else
    |* codice alternativo
endif
```

### On Case (Switch)
```baan
on case variabile
case valore1:
    |* codice
    break
case valore2:
    |* codice
    break
default:
    |* default
    break
endcase
```

## Cicli

### While
```baan
while condizione
    |* codice
    if uscita then
        break
    endif
endwhile
```

### For
```baan
for i = 1 to 10
    |* codice
endfor
```

### Select Loop (già visto sopra)
```baan
selectdo
    |* processa ogni record
endselect
```

## Funzioni

### Definizione
```baan
function tipo nome.funzione(
        domain    tcorno    i.parametro.input,
    ref    domain    tcamnt    io.parametro.inout)
{
        long        variabile.locale

    |* Corpo funzione
    return(valore)
}
```

### Passaggio Parametri
- **Per valore**: `domain tipo variabile`
- **Per riferimento**: `ref domain tipo variabile`
- **Input**: prefisso `i.`
- **Output**: prefisso `o.`
- **Input/Output**: prefisso `io.`

## Gestione Stringhe

```baan
trim$(stringa)                |* Rimuove spazi
string$(numero)               |* Converte numero in stringa
str$(numero)                  |* Converte numero in stringa
isspace(stringa)              |* True se vuota/spazi
stringa1 & stringa2           |* Concatenazione
```

## Gestione Date

```baan
utc.num()                     |* Data/ora corrente (UTC timestamp)
date.to.utc(yy, mm, dd, hh, mi, se)    |* Crea timestamp
utc.to.date(timestamp, yy, mm, dd, hh, mi, se)    |* Estrae componenti
utc.add(data, anni, mesi, giorni, ore, min, sec, risultato)    |* Aggiunge tempo
```

## Gestione Report (BRP)

```baan
|* Apertura report
report.id = brp.open("nome.report", "", 1)

|* Preparazione e stampa
brp.ready(report.id)
brp.field(report.id, "campo.report", valore)
brp.line(report.id, tipo.linea)

|* Chiusura
brp.close(report.id)
```

## Messaggi Utente

```baan
mess("codice.messaggio", tipo)
|* tipo: 0 = info, 1 = warning, 2 = error

mess("Testo libero", 0)

set.input.error("codice.messaggio")    |* Errore input campo
```

## Display e Refresh Campi

```baan
display("nome.campo")                  |* Aggiorna display campo
display("nome.campo", "valore")        |* Imposta e mostra

set.fmin(campo.f, domainof(campo.f))   |* Imposta minimo range
set.fmax(campo.t, domainof(campo.t))   |* Imposta massimo range
```

## Utility Functions

```baan
inc(variabile)                |* Incrementa di 1
return(valore)                |* Return da funzione
commit.transaction()          |* Commit modifiche DB
abort.transaction()           |* Rollback modifiche DB
db.retry.point()              |* Punto retry per lock
```

## Operatori

```baan
=   <>   >   <   >=   <=      |* Confronto
and   or   not                |* Logici
+   -   *   /                 |* Aritmetici
&                             |* Concatenazione stringhe
```

## Convenzioni Naming

### Tabelle
- Prefisso package: `td` (Procurement), `tc` (Common), `ti` (Inventory)
- Modulo: `pur` (Purchase), `sls` (Sales), `com` (Common)
- Numero: `200`, `400`, ecc.
- Esempio: `ttdpur200` = Purchase Requisitions

### Campi
- `_index1`, `_index2`: Indici tabella
- `.f`, `.t`: From/To per range
- `.desc`: Descrizione

### Variabili
- Punti (`.`) al posto di underscore
- Nomi descrittivi: `order.date.f`, `customer.total.amount`

## Form Types

- **Type 1**: Browse (lista record)
- **Type 2**: Single Record
- **Type 4**: Report/Batch Processing (più comune per report)
- **Type 5**: Zoom/Lookup

## Best Practices

1. **Commenti**: Usare `|*` per commenti su linea
2. **Indentazione**: Usare tab per blocchi codice
3. **Gestione Errori**: Sempre controllare return code delle funzioni DAL
4. **Transazioni**: Commit/abort dopo operazioni DB
5. **Performance**: Usare indici (`_index1`) nelle query
6. **Validazione**: Validare input nei campi con `check.input`
7. **Zoom**: Configurare `before.zoom` per pre-filtrare lookup
8. **Display**: Aggiornare campi dipendenti con `display()`

## Esempi Comuni

### Validazione Range Date
```baan
field.date.t:
check.input:
    if date.f > date.t and date.t <> 0 then
        set.input.error("tdpur0001")
        |* To date may not be before from date.
        return
    endif
```

### Propagazione From -> To
```baan
field.order.f:
when.field.changes:
    order.t = order.f
    display("order.t")
```

### Calcolo Totali in Loop
```baan
total = 0
select    tdsls401.*
from    tdsls401
where    tdsls401._index1 = {:order.number}
selectdo
    total = total + (tdsls401.pric * tdsls401.qoor)
endselect
```

### Gestione Flag Boolean
```baan
if flag = tcyesno.yes then
    |* Esegui azione
endif
```
