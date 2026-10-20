#!/usr/bin/env python3
"""build-projects: catalogo dei progetti GitHub, una cartella ciascuno  (`just projects`).

    python build_projects.py [--out projects] [--owner pakkio] [--offline] [--check]

Legge dall'API di GitHub i repository pubblici del proprietario (nome, linguaggio, date, argomenti, descrizione) e le prime righe
del README di ciascuno, poi scrive:
  projects/README.md           il nodo centrale: un grafo di tutti i progetti e una tabella
  projects/<nome>/README.md    una pagina di catalogo per ogni progetto privo di documentazione scritta a mano
e conserva ciò che ha letto in projects/catalogue.json, così --offline e --check funzionano senza rete.

I progetti documentati a mano (DEEP qui sotto: nexus, craftsim, craftstorm, jev-pakkio) mantengono le loro cartelle e pagine; il
nodo centrale rimanda a loro. Nulla di qui si modifica a mano. I repository privati non sono visibili all'API; i due privati che
esistono in locale (craftsim, craftstorm) sono elencati dalla tabella DEEP.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATED = "> Voce di catalogo generata dai metadati di GitHub con `build_projects.py` (`just projects`). Non si modifica a mano."

# Documentati a mano, in profondità. nome -> (descrizione in una riga, pubblico?, pagine)
DEEP = {
    "nexus": ("Motore di RPG testuale basato su IA: NPC guidati da un LLM nel mondo di Eldoria, usabile da terminale, HTTP, MCP o OpenSim", True,
              [("Ingresso", "README.md"), ("Motore", "ENGINE.md"), ("Pipeline", "PIPELINE.md"), ("Lore", "VEIL-WORLD.md")]),
    "craftsim": ("Fork di OpenSimulator su .NET 10: motore di script ZEngine, percorsi di servizio asincroni, moduli aggiuntivi, voce, strumenti operativi", False,
                 [("Ingresso", "README.md"), ("Architettura", "ARCHITECTURE.md"), ("Flussi di lavoro", "WORKFLOWS.md")]),
    "craftstorm": ("Fork del viewer Firestorm più un viewer da browser che si collega alla griglia via LLUDP", False,
                   [("Ingresso", "README.md"), ("Architettura", "ARCHITECTURE.md"), ("Flussi di lavoro", "WORKFLOWS.md")]),
    "jev-pakkio": ("Punteggio locale delle opzioni in un solo passaggio con Gemma 3 4B: CLI, server HTTP, strumenti MCP, motori System One, Jev-Mem", True,
                   [("Ingresso", "README.md"), ("Architettura", "ARCHITECTURE.md"), ("Flussi di lavoro", "WORKFLOWS.md")]),
}
# Relazioni tra i progetti documentati a mano: (da, a, etichetta, tratteggiata?)
RELATIONS = [
    ("craftstorm", "craftsim", "il ponte per il browser accede alla griglia", False),
    ("nexus", "craftsim", "gli script degli NPC girano in una regione OpenSim", True),
    ("nexus", "jev-pakkio", "stesso formato di domande System One", True),
]


def mid(s: str) -> str:
    return "n_" + re.sub(r"\W", "_", s)


def q(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace('"', "'")).strip()


def get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "nexus-build-projects", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def readme_excerpt(owner: str, name: str) -> str:
    try:
        raw = get(f"https://raw.githubusercontent.com/{owner}/{name}/HEAD/README.md", timeout=15)
    except Exception:
        return ""
    raw = re.sub(r"(?s)<!--.*?-->", "", raw)
    raw = re.sub(r"(?s)```.*?```", "", raw)
    raw = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw)                  # immagini e badge
    raw = re.sub(r"<[^>]+>", "", raw)                                 # tag html
    raw = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw)               # link -> il loro testo
    lines = [re.sub(r"\s+", " ", l).strip(" #>*_`-") for l in raw.splitlines()]
    lines = [l for l in lines if len(l) > 3 and not l.startswith("|") and not re.match(r"^[-=]+$", l)]
    out = " ".join(lines[:4])
    return (out[:420].rsplit(" ", 1)[0] + "…") if len(out) > 420 else out


def fetch(owner: str) -> list:
    repos = json.loads(get(f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated"))
    if isinstance(repos, dict):
        sys.exit(f"API di GitHub: {repos.get('message', repos)}")
    keep = [{"name": r["name"], "language": r["language"], "fork": r["fork"], "archived": r["archived"],
             "description": r["description"], "created": r["created_at"][:10], "pushed": r["pushed_at"][:10],
             "topics": r.get("topics", []), "size": r["size"], "license": (r.get("license") or {}).get("spdx_id"),
             "homepage": r.get("homepage"), "url": r["html_url"]} for r in repos]
    with cf.ThreadPoolExecutor(8) as ex:
        for r, ex_text in zip(keep, ex.map(lambda r: readme_excerpt(owner, r["name"]), keep)):
            r["excerpt"] = ex_text
    return sorted(keep, key=lambda r: r["name"].lower())


def stem(name: str) -> str:
    return re.split(r"[-_]", name, 1)[0].lower().rstrip("0123456789")


def family(name: str, names: list) -> list:
    s = stem(name)
    return sorted(n for n in names if n != name and len(s) >= 3 and stem(n) == s)


def project_page(r: dict, names: list) -> str:
    kind = "fork" if r["fork"] else "originale"
    if r["archived"]:
        kind += ", archiviato"
    fam = family(r["name"], names)
    rows = [("Repository", f"[{r['url'].split('github.com/')[1]}]({r['url']})"), ("Linguaggio", r["language"] or "—"), ("Tipo", kind),
            ("Creato", r["created"]), ("Ultimo push", r["pushed"])]
    if r["topics"]:
        rows.append(("Argomenti", ", ".join(r["topics"])))
    if r["license"] and r["license"] != "NOASSERTION":
        rows.append(("Licenza", r["license"]))
    if r["homepage"]:
        rows.append(("Sito", r["homepage"]))
    rows.append(("Dimensione", f"{r['size']} KB"))
    g = ["```mermaid", "graph LR", '  HUB["Tutti i progetti"]']
    lang = r["language"] or "nessun linguaggio"
    g.append(f'  HUB --> {mid("lang")}["{q(lang)}"]')
    g.append(f'  {mid("lang")} --> {mid("self")}(["{q(r["name"])}"])')
    for f in fam[:8]:
        g.append(f'  {mid("fam")}["stessa famiglia: {q(re.split(r"[-_]", r["name"], 1)[0])}-*"] --- {mid(f)}(["{q(f)}"])')
    if fam:
        g.append(f'  {mid("fam")} --- {mid("self")}')
    g.append("```")
    body = [f"# {r['name']}", "", "[Tutti i progetti](../README.md)", "", GENERATED, ""]
    body += ["| | |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows] + [""]
    if r["description"]:
        body += [r["description"], ""]
    if r["excerpt"]:
        body += ["## Dal suo README", "", f"> {r['excerpt']}", ""]
    body += ["## Dove si colloca", ""] + g + [""]
    if fam:
        body += ["Stessa famiglia (prefisso del nome in comune): " + ", ".join(f"[{f}](../{f}/README.md)" for f in fam), ""]
    return "\n".join(body)


def hub(repos: list) -> str:
    by_lang = {}
    for r in repos:
        if r["name"] not in DEEP:
            by_lang.setdefault(r["language"] or "nessun linguaggio", []).append(r)
    g = ["```mermaid", "graph LR", '  subgraph deep["Documentati in profondità"]']
    for n in DEEP:
        g.append(f'    {mid(n)}[["{n}"]]')
    g.append("  end")
    for a, b, label, dotted in RELATIONS:
        g.append(f'  {mid(a)} {"-.->" if dotted else "-->"}|"{q(label)}"| {mid(b)}')
    for lang, rs in sorted(by_lang.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        g.append(f'  subgraph {mid("sg" + lang)}["{q(lang)} ({len(rs)})"]')
        for r in rs:
            g.append(f'    {mid(r["name"])}(["{q(r["name"])}"])')
        g.append("  end")
    g.append("```")
    rows = ["| Progetto | Linguaggio | Ultimo push | Descrizione |", "|---|---|---|---|"]
    for n, (desc, pub, pages) in DEEP.items():
        r = next((x for x in repos if x["name"] == n), None)
        links = " · ".join(f"[{t}]({n}/{p})" for t, p in pages)
        rows.append(f"| **[{n}]({n}/README.md)** ★ | {(r or {}).get('language') or '—'} | {(r or {}).get('pushed') or 'privato'} | {desc} — {links} |")
    for r in repos:
        if r["name"] in DEEP:
            continue
        rows.append(f"| [{r['name']}]({r['name']}/README.md) | {r['language'] or '—'} | {r['pushed']} | {q(r['description'] or r['excerpt'])[:110]} |")
    return "\n".join([
        "# Progetti", "",
        "La mappa del lavoro su [github.com/pakkio](https://github.com/pakkio). Quattro progetti sono documentati in profondità, "
        "ciascuno come una piccola rete di pagine Markdown con grafi (★); ogni altro repository ha una pagina di catalogo generata da GitHub.", "",
        GENERATED.replace("Voce di catalogo generata", "Questo nodo è generato"), "",
        "## La mappa", "", *g, "",
        "Le linee tratteggiate sono relazioni più deboli (un formato condiviso, un posto dove girare); quelle piene sono dipendenze dirette.", "",
        "## Documentati in profondità", "",
        "- **[nexus](nexus/README.md)** — documentato da due lati: [motore e pipeline](nexus/ENGINE.md) e [lore](nexus/VEIL-WORLD.md)",
        "- **[craftsim](craftsim/README.md)** — il fork di OpenSimulator ([architettura](craftsim/ARCHITECTURE.md), [flussi di lavoro](craftsim/WORKFLOWS.md))",
        "- **[craftstorm](craftstorm/README.md)** — viewer e ponte per il browser ([architettura](craftstorm/ARCHITECTURE.md), [flussi di lavoro](craftstorm/WORKFLOWS.md))",
        "- **[jev-pakkio](jev-pakkio/README.md)** — punteggio locale delle opzioni ([architettura](jev-pakkio/ARCHITECTURE.md), [flussi di lavoro](jev-pakkio/WORKFLOWS.md))", "",
        "## Tutti i progetti", "", *rows, ""])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "projects"))
    ap.add_argument("--owner", default="pakkio")
    ap.add_argument("--offline", action="store_true", help="usa projects/catalogue.json invece della rete")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cache = os.path.join(a.out, "catalogue.json")
    if a.offline or a.check:
        repos = json.load(open(cache, encoding="utf-8"))
    else:
        repos = fetch(a.owner)
        os.makedirs(a.out, exist_ok=True)
        json.dump(repos, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    names = [r["name"] for r in repos]
    pages = {"README.md": hub(repos)}
    for r in repos:
        if r["name"] not in DEEP:
            pages[f"{r['name']}/README.md"] = project_page(r, names)
    stale = 0
    for rel, content in sorted(pages.items()):
        path = os.path.join(a.out, rel)
        same = os.path.exists(path) and open(path, encoding="utf-8").read() == content
        if a.check:
            stale += not same
            if not same:
                print("STALE  " + rel)
        elif not same:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(content)
    print(f"{len(repos)} repository; {len(pages)} pagine" + (f"; {stale} non aggiornate" if a.check else " scritte"))
    if a.check:
        sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
