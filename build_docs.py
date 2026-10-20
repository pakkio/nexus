#!/usr/bin/env python3
"""build-docs: genera il lato lore della rete di documentazione da lore.txt  (`just docs`).

    python build_docs.py [lore.txt] [--out DIR] [--check]

Scrive VEIL-WORLD.md, VEIL-PLACES.md, VEIL-NPCS.md, VEIL-FACTIONS.md e VEIL-MISSIONS.md in --out (default: projects/nexus/, la
cartella di Nexus nella rete di documentazione). Le pagine contengono prosa copiata da lore.txt e grafi Mermaid calcolati
dalla sua struttura (chi vive dove, chi scambia con chi, le fazioni, l'NPC della scelta finale): non possono quindi
discostarsi dal canone e non si modificano a mano. Le pagine del motore e della pipeline (ENGINE*.md, PIPELINE*.md, VEIL.md)
sono scritte a mano e rimandano a queste. --check non scrive nulla ed esce con 1 se una pagina su disco differisce da quella
che lore.txt produrrebbe. Indipendente dalla storia: legge la stessa struttura di compile_lore.py.
"""
import argparse
import json
import os
import re
import sys

import compile_lore as cl

HERE = os.path.dirname(os.path.abspath(__file__))
UP = "../../"            # la radice del repository, vista da projects/nexus/
NAV = (
    "[Tutti i progetti](../README.md) · [Nexus](README.md) · Motore: [panoramica](ENGINE.md), "
    "[flusso delle richieste](ENGINE-REQUEST-FLOW.md), [comandi](ENGINE-COMMANDS.md), [prompt](ENGINE-PROMPT.md), "
    "[meccaniche](ENGINE-MECHANICS.md), [storage e configurazione](ENGINE-STORAGE-CONFIG.md) · Pipeline: "
    "[panoramica](PIPELINE.md), [digest](PIPELINE-DIGEST.md), [derivazione](PIPELINE-DERIVE.md) · Lore: "
    "[il Velo](VEIL.md), [mondo](VEIL-WORLD.md), [luoghi](VEIL-PLACES.md), [NPC](VEIL-NPCS.md), [fazioni](VEIL-FACTIONS.md), "
    "[missioni](VEIL-MISSIONS.md)"
)
GENERATED = "> Generato da `lore.txt` con `build_docs.py` (`just docs`). Non modificare a mano: modifica il lore e rigenera."


def mid(s: str) -> str:
    """Id di nodo Mermaid."""
    return "n_" + re.sub(r"\W", "_", s)


def q(s: str) -> str:
    """Testo sicuro dentro un'etichetta Mermaid tra virgolette."""
    return re.sub(r"\s+", " ", s.replace('"', "'")).strip()


def slug(heading: str) -> str:
    """Ancora di intestazione in stile GitHub."""
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


# Front matter so quick switchers (Obsidian Ctrl+O, GitHub-style viewers) find the lore pages by the story's name,
# not only by file name: every page answers to "Velo" and "Veil", each also to its own topic.
STORY_ALIASES = ["Velo", "Il Velo", "Veil", "Lore del Velo"]
TOPIC_ALIASES = {
    "Lore: il mondo": ["Velo - il mondo", "Veil world"],
    "Lore: i luoghi": ["Velo - luoghi", "Veil places"],
    "Lore: gli NPC": ["Velo - NPC", "Veil NPCs"],
    "Lore: fazioni e finale": ["Velo - fazioni e finale", "Veil factions"],
    "Lore: la catena di missioni": ["Velo - missioni", "Veil missions"],
}


def front(extra: list) -> str:
    names = ", ".join(f'"{a}"' for a in STORY_ALIASES + extra)
    return f"---\naliases: [{names}]\ntags: [veil, velo, lore]\n---\n\n"


def page(title: str, intro: str, body: str) -> str:
    return front(TOPIC_ALIASES.get(title, [])) + f"# {title}\n\n{NAV}\n\n{GENERATED}\n\n{intro}\n\n{body.rstrip()}\n"


def squash_para(t: str) -> str:
    return re.sub(r"\n(?!\n)", " ", t).strip()


def faction_name(s05: str, tag: str) -> str:
    b = cl.bullet(s05, tag)
    return b.split(",")[0].strip() if b else tag


def data_files() -> tuple:
    def load(f):
        try:
            return json.load(open(os.path.join(HERE, f), encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return load("NPC_BUSINESS_CARDS.json"), load("NPC_EXTRAS.json")


def build(lore_path: str) -> dict:
    text = open(lore_path, encoding="utf-8").read()
    S = cl.sections(text)
    places, npcs = cl.parse_places(S["06"]), cl.parse_npcs(S["07"])
    chain = cl.parse_chain(S.get("08", ""), npcs)
    off = cl.off_chain(chain)
    in_chain = [s for s in chain if s["code"] not in off]
    cards, extras = data_files()
    by_place = {}
    for code, n in npcs.items():
        by_place.setdefault(n["place"], []).append(code)
    prefix_of = lambda c: f"NPC_PREFIX.{c.split('.')[1]}.{npcs[c]['name'].lower().replace(' ', '')}.txt"
    first = lambda c: npcs[c]["name"].split()[-1]
    out = {}

    # ---- VEIL-WORLD.md: il mondo ------------------------------------------------------------------------------------
    world = S["01"]
    ante = re.search(r"(?m)^Antefatto[^:\n]*:[ \t]*(\S[^\n]*)$", world)
    prose = re.sub(r"(?m)^Antefatto[^:\n]*:.*\n?", "", world).strip()
    body = ("## In breve\n\n" + (f"> {ante.group(1).strip()}\n\n" if ante else "")
            + "## Il mondo\n\n" + prose + "\n\n## Termini\n\n```text\n" + S.get("02", "").strip() + "\n```\n\n"
            + "## Cosa sa un NPC\n\n```text\n" + S["09"].strip() + "\n```\n\n"
            + "## Dove andare ora\n\n"
            "- [Luoghi](VEIL-PLACES.md) — la mappa e chi ci vive\n- [NPC](VEIL-NPCS.md) — tutti, con luogo e ruolo\n"
            "- [Fazioni e finale](VEIL-FACTIONS.md)\n- [La catena di missioni](VEIL-MISSIONS.md)\n"
            "- Come questo testo arriva ai personaggi: [assemblaggio del prompt](ENGINE-PROMPT.md) · "
            "come viene prodotto: [la pipeline del lore](PIPELINE.md)\n")
    out["VEIL-WORLD.md"] = page("Lore: il mondo", "Il canone, così come è stato distillato nelle sezioni [01], [02] e [09] di `lore.txt`.", body)

    # ---- VEIL-PLACES.md ---------------------------------------------------------------------------------------
    g = ["```mermaid", "graph LR"]
    for pname, p in places.items():
        g.append(f'  {mid(pname)}["{q(pname)}<br/>{q(p["access"])}"]')
    for pname, codes in by_place.items():
        if pname in places:
            for c in codes:
                g.append(f'  {mid(pname)} --- {mid(c)}(["{q(npcs[c]["name"])}"])')
    g.append("```")
    rows = ["| Luogo | Id | Accesso | Residenti |", "|---|---|---|---|"]
    for pname, p in places.items():
        res = ", ".join(f"[{npcs[c]['name']}](VEIL-NPCS.md#{slug(npcs[c]['name'])})" for c in by_place.get(pname, [])) or "—"
        rows.append(f"| [{pname}](#{slug(pname)}) | `{p['id']}` | {p['access']} | {res} |")
    sec = "\n\n".join(f"## {pname}\n\nAccesso: `{p['access']}` · id `{p['id']}`\n\n{p['text']}" for pname, p in places.items())
    out["VEIL-PLACES.md"] = page("Lore: i luoghi", "Tutti i luoghi del canone (`lore.txt` [06]) e gli NPC che vi abitano.",
                                 "\n".join(g) + "\n\n" + "\n".join(rows) + "\n\n" + sec)

    # ---- VEIL-NPCS.md -----------------------------------------------------------------------------------------
    s05 = S["05"]
    g = ["```mermaid", "graph LR"]
    for pname, codes in by_place.items():
        g.append(f'  subgraph {mid("sg" + pname)}["{q(pname)}"]')
        for c in codes:
            g.append(f'    {mid(c)}(["{q(npcs[c]["name"])}"])')
        g.append("  end")
    tags = {}
    for c, n in npcs.items():
        f = cl.faction_of(n)
        if f:
            tags.setdefault(f[0], []).append(c)
    for tag, codes in tags.items():
        g.append(f'  {mid("f" + tag)}{{{{"{q(faction_name(s05, tag))}"}}}}')
        for c in codes:
            g.append(f'  {mid(c)} ==>|guida| {mid("f" + tag)}')
    g.append("```")
    rows = ["| NPC | Luogo | Ruolo | Fazione | Catena |", "|---|---|---|---|---|"]
    for c, n in npcs.items():
        f = cl.faction_of(n)
        step = next((i for i, x in enumerate(in_chain, 1) if x["code"] == c), None)
        rows.append(f"| [{n['name']}](#{slug(n['name'])}) | [{n['place']}](VEIL-PLACES.md#{slug(n['place'])}) | {n['Ruolo'].rstrip('.')} | "
                    f"{faction_name(s05, f[0]) if f else '—'} | "
                    f"{'fuori catena' if c in off else (f'passo {step}' if step else '—')} |")
    parts = []
    for c, n in npcs.items():
        L = [f"## {n['name']}", f"*{n['Ruolo'].rstrip('.')}* · [{n['place']}](VEIL-PLACES.md#{slug(n['place'])}) · `{c}`", ""]
        for label, key in (("Movente", "Movente"), ("Obiettivo", "Obiettivo"), ("Custodisce", "Tesoro"),
                           ("Come trattarlo", "Trattare"), ("Posizione", "Posizione")):
            if n.get(key):
                L.append(f"- **{label}:** {n[key]}")
        f = cl.faction_of(n)
        if f:
            L.append(f"- **Fazione:** {faction_name(s05, f[0])} — via *{f[1]}* ([fazioni](VEIL-FACTIONS.md))")
        if "Finale" in n:
            L.append("- **Scelta finale:** questo NPC la custodisce ([fazioni e finale](VEIL-FACTIONS.md#la-scelta-finale))")
        idx = next((i for i, s in enumerate(in_chain) if s["code"] == c), None)
        if c in off:
            mine = next(s for s in chain if s["code"] == c)
            L.append(f"- **Scambio:** dà {mine['gives']}, {mine['cost']} — fuori catena ([missioni](VEIL-MISSIONS.md))")
        elif idx is not None:
            s = in_chain[idx]
            L.append(f"- **Scambio:** dà {s['gives']}, {s['cost']} ([missioni](VEIL-MISSIONS.md))")
            if idx > 0:
                p = in_chain[idx - 1]["code"]
                L.append(f"- **Prima:** [{npcs[p]['name']}](#{slug(npcs[p]['name'])})")
            if idx + 1 < len(in_chain):
                nx = in_chain[idx + 1]["code"]
                L.append(f"- **Dopo:** [{npcs[nx]['name']}](#{slug(npcs[nx]['name'])})")
        derived = [f"[`{prefix_of(c)}`]({UP}{prefix_of(c)})"]
        if c in cards:
            derived.append("biglietto da visita (`NPC_BUSINESS_CARDS.json`)")
        if extras.get(c, {}).get("notecard_feature"):
            derived.append("notecard (`NPC_EXTRAS.json`)")
        if extras.get(c, {}).get("teleport"):
            derived.append(f"teletrasporto `{extras[c]['teleport']}`")
        L.append("- **Derivati:** " + ", ".join(derived) + " — vedi [assemblaggio del prompt](ENGINE-PROMPT.md)")
        parts.append("\n".join(L))
    out["VEIL-NPCS.md"] = page("Lore: gli NPC", "Tutti i personaggi (`lore.txt` [07]) con luogo, fazione e posizione nella catena di missioni.",
                               "\n".join(g) + "\n\n" + "\n".join(rows) + "\n\n" + "\n\n".join(parts))

    # ---- VEIL-FACTIONS.md -------------------------------------------------------------------------------------
    g = ["```mermaid", "graph TD"]
    for tag, codes in tags.items():
        for c in codes:
            f = cl.faction_of(npcs[c])
            g.append(f'  {mid("f" + tag)}["{q(faction_name(s05, tag))}"] -->|"guidata da {q(first(c))}"| {mid(c)}(["{q(npcs[c]["name"])}"])')
            g.append(f'  {mid("f" + tag)} ==>|"rappresenta"| {mid("fate" + f[1])}{{{{"{q(f[1])}"}}}}')
    gate = [(c, n) for c, n in npcs.items() if "Finale" in n]
    if gate:
        c, n = gate[0]
        leaders = ", ".join(first(x) for codes in tags.values() for x in codes)
        g += [f'  L(["Il giocatore parla con {q(leaders)}"]) -->|"abbastanza turni di dialogo"| {mid(c)}(["{q(n["name"])} compare"])',
              f'  {mid(c)} --> CH["/choose &lt;destino&gt;"]', '  CH --> IR(["Irreversibile: registrata nei flag del giocatore"])']
    g.append("```")
    fin = re.search(r"(?ms)^FINALE:.*", s05)
    body = ("\n".join(g) + "\n\n## Fazioni e costi\n\n```text\n" + s05.strip() + "\n```\n\n## La scelta finale\n\n"
            + (squash_para(fin.group(0)) if fin else "Questa storia non definisce una scelta finale.")
            + "\n\nLato motore: il cancello e il destino registrato stanno in `veil_finale.py` — vedi [meccaniche](ENGINE-MECHANICS.md#la-scelta-finale).\n")
    out["VEIL-FACTIONS.md"] = page("Lore: fazioni e finale", "Chi guida cosa, quanto costa ogni via e come si arriva al finale "
                                   "(`lore.txt` [05]).", body)

    # ---- VEIL-MISSIONS.md -------------------------------------------------------------------------------------
    gives_of = {cl._norm_item(s["gives"]): s["code"] for s in chain}
    g = ["```mermaid", "graph LR"]
    for s in chain:
        g.append(f'  {mid(s["code"])}["{q(npcs[s["code"]]["name"])}<br/>dà {q(s["gives"])}"]')
    for s in chain:
        if s["cost"].startswith("in cambio di"):
            giver = gives_of[cl._norm_item(s["cost"])]
            item = next(x["gives"] for x in chain if x["code"] == giver)
            g.append(f'  {mid(giver)} -->|"{q(item)}"| {mid(s["code"])}')
        else:
            g.append(f'  {mid("pay" + s["code"])}(["{q(s["cost"])}"]) --> {mid(s["code"])}')
    g.append("```")
    rows = ["| # | NPC | Dà | Costo | Nella catena |", "|---|---|---|---|---|"]
    for i, s in enumerate(chain, 1):
        rows.append(f"| {i} | [{npcs[s['code']]['name']}](VEIL-NPCS.md#{slug(npcs[s['code']]['name'])}) | {s['gives']} | {s['cost']} | "
                    f"{'no' if s['code'] in off else 'sì'} |")
    s08 = S.get("08", "")
    rules = re.search(r"(?ms)^Regole:.*", s08)
    note = re.search(r"(?m)^\s*Nota:\s*(.+)$", s08)
    body = ("\n".join(g) + "\n\n" + "\n".join(rows) + "\n\n" + (f"Nota: {note.group(1).strip()}\n\n" if note else "")
            + "## Regole\n\n" + (squash_para(rules.group(0)) if rules else "Nessuna regola di scambio definita.")
            + "\n\nLato motore: il server accetta solo questi scambi (`quest_trades.py`) — vedi [meccaniche](ENGINE-MECHANICS.md#scambi).\n")
    out["VEIL-MISSIONS.md"] = page("Lore: la catena di missioni", "Chi dà cosa, in cambio di cosa (`lore.txt` [08]).", body)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lore", nargs="?", default=os.path.join(HERE, "lore.txt"))
    ap.add_argument("--out", default=os.path.join(HERE, "projects", "nexus"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    pages = build(a.lore)
    os.makedirs(a.out, exist_ok=True)
    stale = 0
    for fn, content in sorted(pages.items()):
        path = os.path.join(a.out, fn)
        same = os.path.exists(path) and open(path, encoding="utf-8").read() == content
        if a.check:
            stale += not same
            print(("ok     " if same else "STALE  ") + fn)
        elif not same:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"scritto {fn} ({len(content)} caratteri)")
    if a.check:
        sys.exit(1 if stale else 0)
