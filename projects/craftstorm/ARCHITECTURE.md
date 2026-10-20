# craftstorm: architettura

[Tutti i progetti](../README.md) · [craftstorm](README.md) · [architettura](ARCHITECTURE.md) · [flussi di lavoro](WORKFLOWS.md)

Due metà: il viewer Firestorm, ereditato, e `web/`, il viewer da browser con il suo ponte. Quasi tutto il lavoro recente è in `web/`.

## Il viewer da browser

```mermaid
graph TD
  subgraph browser["Browser"]
    APP["app.js<br/>rendering con three.js"]
    COL["collision.js<br/>giocatore contro prim"]
    LL["llsd.js<br/>parser LLSD"]
    J2["openjpeg.js<br/>JPEG2000 in RGBA, WASM"]
    HC["httpClient.js"]
    BC["runtime/bridge_client.js"]
  end
  subgraph bridge["Ponte (una sola implementazione per volta)"]
    BP["bridge.py<br/>Python, solo libreria standard"]
    BJ["bridge.js<br/>porting in Node"]
    BCY["bridge_compiled.py<br/>versione compilata con Cython"]
    CF["csfast<br/>estensione C per i percorsi caldi"]
    J2L["j2k_lenient.py<br/>decodifica JPEG2000 tollerante via OpenJPEG"]
    CL["cluster.py<br/>N ponti dietro una sola porta"]
  end
  subgraph grid["Griglia craftsim"]
    LG["login XML-RPC"]
    UDP["circuito UDP LLUDP"]
    CAPS["capability CAPS<br/>GetTexture via HTTP"]
  end
  APP --- COL
  APP --- LL
  APP --- J2
  BC <-->|"WebSocket, JSON"| BP
  BP --> LG
  BP <--> UDP
  BP --> CAPS
  BP --- CF
  BP --- J2L
  CL --> BP
  DS["desktop.py<br/>guscio desktop"] --> BP
```

## Perché esiste il ponte

- Il protocollo reale (movimento, chat, aggiornamenti degli oggetti, tocco, sedersi) è UDP (LLUDP), e un browser non può usarlo.
- Il ponte fa il login tramite il servizio XML-RPC della griglia, apre il circuito UDP con il simulatore usando il formato dei
  messaggi del viewer (`message_template.msg`), e offre al browser un protocollo JSON su un server WebSocket scritto a mano.
- Le texture arrivano dalla capability `GetTexture` (negoziata dal seed CAPS ottenuto al login) e vanno decodificate da JPEG2000,
  perché il browser non sa farlo. La decodifica passa da `imagecodecs` (OpenJPEG), non da Pillow: le texture dei corpi di questa
  griglia sono flussi J2K grezzi con una quinta componente (una maschera ausiliaria) che Pillow rifiuta.

## Prestazioni: la scalabilità del ponte

Un ponte Python è un solo processo, quindi la parte di `web/` più curata è la scalabilità.

```mermaid
flowchart LR
  BRO["molti browser"] --> FR["fronte con affinità di sessione<br/>nginx.cluster.conf.sample"]
  FR --> S1["scaglione bridge.py 1"]
  FR --> S2["scaglione 2"]
  FR --> SN["scaglione N"]
  S1 --> POOL["decodifica in un pool di processi"]
  S2 --> POOL
  SN --> POOL
  S1 --> CACHE[("cache degli asset condivisa<br/>con richieste coalescenti")]
  S2 --> CACHE
  SN --> CACHE
  CACHE --> GZ["mesh compresse una volta sola"]
```

Dalla cronologia dei commit: scaglioni dietro un fronte con affinità, decodifica in un pool di processi, cache degli asset condivisa
con coalescenza delle richieste, mesh compresse una volta sola e condivise tra richieste concorrenti, `orjson`, un'estensione C
(`csfast`) per i percorsi caldi, un lettore persistente sul socket del simulatore e arrotondamenti esatti veloci.

## Il viewer Firestorm

`indra/` contiene il codice del viewer (C++), `scripts/` e `autobuild.xml` gli strumenti di build, `doc/` le istruzioni per
Windows, macOS e Linux. È la base ufficiale di Firestorm; il lavoro specifico di craftstorm è in `web/`.
