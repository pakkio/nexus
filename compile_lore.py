#!/usr/bin/env python3
"""compile-lore: turn lore.txt into the prompt parts that are derived from it  (`just lore`).

    python compile_lore.py [lore.txt] [--out DIR] [--check] [--no-npcs] [--root DIR]
    ./compile-lore [lore.txt] [--out DIR] [--check] [--no-npcs] [--root DIR]

Writes (into --out, default: next to this script):
  ANTEFATTO.txt                       world summary shown to every regular NPC (loader truncates at 800 chars)
  NPC_PREFIX.<area>.<name>.txt        one per story NPC: role in the story, place, mission chain, stance, limits

Everything comes from lore.txt ([01] world + "Antefatto:" line, [05] factions, [06] places, [07] NPCs,
[08] mission chain, [09] knowledge); nothing is invented here and nothing is tied to one story. The script fails loudly
if lore.txt no longer has the structure it expects. --check writes nothing and exits 1 if the generated files on disk differ from
what lore.txt would produce (with --npcs also if the NPC records differ). Pure automation: lore.txt stays the source.

[07] blocks may carry three optional labels besides Ruolo/Movente/Obiettivo/Tesoro/Trattarlo/Posizione:
  Fazione: <TAG> / <DESTINO>   leader of a faction: <TAG> starts a bullet in [05], <DESTINO> labels its cost
  Servizio: si                 service NPC, not part of the story: no NPC_PREFIX file
  Finale: si                   keeper of the final choice: its prefix lists the cost of every fate

NPC records (name, role, motivation, goal, treasure, playerhint, teleport) are also derived from [07]. They live in the
document store (file or SQLite, honouring NEXUS_STORAGE / NEXUS_SQLITE_PATH, root = --root, default "database"):
  - by default the run WRITES them, after saving the current NPC records to <root>/backups/NPCs-before-compile-lore-*.json;
  - with --no-npcs it only REPORTS which NPC fields would change (--npcs is accepted and means the default).
Only the fields that really differ are written, and only those fields are touched (greetings, emotes, animations, notecards, business cards... are kept). An NPC that
is in lore.txt but not in the store is created.
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANTEFATTO_LIMIT = 780          # session_utils truncates at 800

LABELS = ("Ruolo", "Movente", "Obiettivo", "Tesoro", "Trattarlo", "Trattarla", "Posizione",
          "Fazione", "Servizio", "Finale")


def sections(text: str) -> dict:
    parts = re.split(r"(?m)^\[(\d\d) [A-Z ]+\]$", text)
    out = {parts[i]: parts[i + 1].strip("\n") for i in range(1, len(parts), 2)}
    for need in ("01", "05", "06", "07", "09"):
        if need not in out:
            sys.exit(f"lore.txt: section [{need}] not found")
    return out


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def cap(t: str) -> str:
    return t[:1].upper() + t[1:]


def sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", squash(text)) if s.strip()]


def parse_places(body: str) -> dict:
    places = {}
    for m in re.finditer(r"(?m)^(\w+) \| ([^|\n]+?) \| (\S+) \|[^\n]*\n((?:  [^\n]*\n?)+)", body):
        places[m.group(2).strip()] = {"id": m.group(1), "access": m.group(3), "text": squash(m.group(4))}
    if not places:
        sys.exit("lore.txt [06]: no places parsed (expected 'id | Nome | accesso | chi' blocks)")
    return places


def parse_npcs(body: str) -> dict:
    npcs = {}
    for m in re.finditer(r"(?m)^(NPC\.[\w.]+) \| ([^|\n]+?) \| ([^\n]+)\n((?:  [^\n]*\n?)+)", body):
        code, name, place, block = m.group(1), m.group(2).strip(), m.group(3).strip(), squash(m.group(4))
        fields = {}
        pos = [(lm.start(), lm.end(), lm.group(1)) for lm in re.finditer(r"(%s):" % "|".join(LABELS), block)]
        for i, (s, e, label) in enumerate(pos):
            fields[label] = block[e:(pos[i + 1][0] if i + 1 < len(pos) else len(block))].strip()
        fields["Trattare"] = fields.pop("Trattarlo", None) or fields.pop("Trattarla", "")
        for k in ("Posizione", "Trattare"):
            if fields.get(k):
                fields[k] = re.sub(r"\s*\btp\b.*$", "", fields[k]).strip()
        if "Ruolo" not in fields:
            sys.exit(f"lore.txt [07]: {code} has no 'Ruolo:'")
        npcs[code] = {"name": name, "place": place, **fields}
    if not npcs:
        sys.exit("lore.txt [07]: no NPCs parsed (expected 'NPC.area.nome | Nome | Luogo' blocks)")
    return npcs


def parse_tp(block_text: str) -> str:
    m = re.search(r"\btp\b(.*)$", block_text)
    return ",".join(re.findall(r"\d+", m.group(1))) if m else ""


def npc_records(body: str, npcs: dict) -> dict:
    """code -> the store fields lore.txt defines for that NPC (plus _place, used only when creating one)."""
    tps = {}
    for m in re.finditer(r"(?m)^(NPC\.[\w.]+) \| [^|\n]+? \| [^\n]+\n((?:  [^\n]*\n?)+)", body):
        tps[m.group(1)] = parse_tp(squash(m.group(2)))
    recs = {}
    for code, n in npcs.items():
        r = {"name": n["name"], "role": n["Ruolo"].rstrip(".")}
        if n.get("Movente"):
            r["motivation"] = n["Movente"]
        if n.get("Obiettivo"):
            r["goal"] = n["Obiettivo"]
        if n.get("Tesoro"):
            m = re.match(r"^(.*?) \((.*)\)\.?$", n["Tesoro"])
            r["treasure"] = f"{m.group(1)} - {m.group(2)}" if m else n["Tesoro"]
        if n.get("Trattare"):
            r["playerhint"] = cap(n["Trattare"])
        if tps.get(code):
            r["teleport"] = tps[code]
        recs[code] = r
    return recs


def same_text(a, b) -> bool:
    """Equal for the purpose of NPC records: ignores accents, quote marks, spacing and a trailing full stop, so a digest
    that only dropped an accent or a quote never counts as a change (and never degrades the stored text)."""
    import unicodedata

    def norm(t) -> str:
        t = unicodedata.normalize("NFKD", str(t or ""))
        t = "".join(c for c in t if not unicodedata.combining(c))
        t = re.sub(r"[\u2018\u2019`]", "'", t)
        t = re.sub(r"[\"\u201c\u201d]", "", t)
        return re.sub(r"\s+", " ", t).strip().rstrip(".").strip()
    return norm(a) == norm(b)


def sync_npcs(recs: dict, places: dict, npcs: dict, root: str, apply: bool) -> int:
    """Compare (and with apply=True write) lore's NPC fields against the document store. Returns #changed fields."""
    import json
    import time
    sys.path.insert(0, HERE)
    from doc_store import make_store
    store = make_store(root)
    plan = []                                   # (code, field, old, new)
    for code, rec in recs.items():
        cur = store.get("NPCs", code)
        if cur is None:
            plan.append((code, "(new NPC)", None, rec["name"]))
            continue
        for f, v in rec.items():
            if not same_text(cur.get(f), v):
                plan.append((code, f, cur.get(f), v))
    for code, f, old, new in plan:
        o = "-" if old is None else f"{len(str(old))} chars"
        print(f"  NPC {code}: {f} ({o} -> {len(str(new))} chars)")
    print(f"NPC records: {len(plan)} field(s) differ from lore.txt" + ("" if plan else " - in sync"))
    if apply and plan:
        os.makedirs(os.path.join(root, "backups"), exist_ok=True)
        bak = os.path.join(root, "backups", time.strftime("NPCs-before-compile-lore-%Y%m%d-%H%M%S.json"))
        with open(bak, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v, *_ in store.items("NPCs")}, f, ensure_ascii=False, indent=1)
        print(f"  saved current NPC records to {bak}")
        by_code = {}
        for code, f, _, new in plan:
            by_code.setdefault(code, {})[f] = new
        for code, changed in by_code.items():          # only the fields that really differ; the rest stays as stored
            cur = store.get("NPCs", code)
            if cur is None:
                cur, changed = {"area": npcs[code]["place"]}, recs[code]
            cur.update(changed)
            store.put("NPCs", code, cur)
        print(f"  wrote {len(plan)} field(s) in {len(by_code)} NPC record(s)")
    elif plan:
        print("  (not written: --no-npcs or --check was given)")
    return len(plan)


def parse_chain(body: str, npcs: dict) -> list:
    """Trade lines of [08]: '  Nome -> Oggetto   per N crediti | in cambio di X'. Empty list if the story has none."""
    by_last = {n["name"].split()[-1]: c for c, n in npcs.items()}
    steps = []
    for m in re.finditer(r"(?m)^\s{2}(\w+)\s+->\s+(.+?)\s{2,}(per \d+ crediti|in cambio di .+?)\s*(?:\(.*)?$", body or ""):
        if m.group(1) not in by_last:
            sys.exit(f"lore.txt [08]: trade line names '{m.group(1)}', who is not an NPC in [07]")
        steps.append({"code": by_last[m.group(1)], "gives": m.group(2).strip(), "cost": m.group(3).strip()})
    return steps


def _norm_item(t: str) -> str:
    """Item name for matching: case-insensitive, 'in cambio di ' (the format keyword) removed. No language handling:
    the digest (LLM) must write the required item exactly as the giver's item is written."""
    t = t.strip().lower()
    return t[len("in cambio di "):].strip() if t.startswith("in cambio di ") else t


def off_chain(chain: list) -> set:
    """Codes that sell something but are linked to nobody else's trade (not in the mission chain)."""
    gives = {_norm_item(s["gives"]): s["code"] for s in chain}
    linked = set()
    for s in chain:
        if s["cost"].startswith("in cambio di"):
            need = _norm_item(s["cost"])
            if need not in gives:
                sys.exit(f"lore.txt [08]: '{s['cost']}' (asked by {s['code']}) matches no item given by another NPC "
                         f"({sorted(gives)}); write the item name exactly as the giver's, without articles")
            linked |= {s["code"], gives[need]}
    return {s["code"] for s in chain} - linked


def antefatto(world: str) -> str:
    m = re.search(r"(?m)^Antefatto[^:\n]*:[ \t]*(\S[^\n]*)$", world)
    if not m:
        sys.exit("lore.txt [01]: no line 'Antefatto (per i prompt, max 780 caratteri): <testo>'")
    text = squash(m.group(1))
    if len(text) > ANTEFATTO_LIMIT:
        sys.exit(f"Antefatto line in [01] is {len(text)} chars (limit {ANTEFATTO_LIMIT}); shorten it")
    return text + "\n"


def bullet(body: str, tag: str) -> str:
    m = re.search(r"(?ms)^ - %s[^\n]*\n(?:   [^\n]*\n?)*" % re.escape(tag), body)
    return squash(m.group(0)).lstrip("- ").strip() if m else ""


def incompat(factions: str) -> str:
    m = re.search(r"(?ms)^Incompatibilita[^\n]*\n(?:[^\n]+\n?)+", factions)
    return squash(m.group(0)) if m else ""


def faction_of(npc: dict):
    m = re.match(r"^(\S+)\s*/\s*(\S+)", npc.get("Fazione", ""))
    return (m.group(1), m.group(2)) if m else None


def prefix(code: str, npc: dict, places: dict, chain: list, S: dict, npcs: dict, rivals: set) -> str:
    L = []
    L.append(f"IL TUO RUOLO NELLA STORIA\nSei {npc['name']}, {npc['Ruolo'].rstrip('.')}. Il tuo luogo: {npc['place']}.")
    if npc.get("Movente"):
        L.append(f"Il tuo movente: {npc['Movente']}")
    if npc.get("Obiettivo"):
        L.append(f"Il tuo obiettivo: {npc['Obiettivo']}")
    if npc.get("Tesoro"):
        L.append(f"Cio che custodisci (non lo dai in cambio di una frase): {npc['Tesoro']}")
    if npc.get("Trattare"):
        L.append(f"COME SEI E COME TRATTI IL CERCATORE\n{cap(npc['Trattare'])}")
    if npc["place"] in places:
        L.append(f"IL TUO LUOGO ({npc['place']}, accesso {places[npc['place']]['access']})\n{places[npc['place']]['text']}")

    off = off_chain(chain)
    in_chain = [s for s in chain if s["code"] not in off]
    mine = next((s for s in chain if s["code"] == code), None)
    idx = next((i for i, s in enumerate(in_chain) if s["code"] == code), None)
    if mine and code in off:
        L.append(f"I TUOI SCAMBI\nTu dai: {mine['gives']}, {mine['cost']}. Non fai parte della catena delle missioni. "
                 "L'oggetto passa solo dopo il pagamento.")
    elif idx is not None:
        s = in_chain[idx]
        lines = [f"Tu dai: {s['gives']}, {s['cost']}."]
        if idx > 0:
            p = in_chain[idx - 1]
            lines.append(f"Prima di te nella catena: {npcs[p['code']]['name']} ({npcs[p['code']]['place']}), che da {p['gives']}.")
        if idx + 1 < len(in_chain):
            n = in_chain[idx + 1]
            lines.append(f"Dopo di te: {npcs[n['code']]['name']} ({npcs[n['code']]['place']}), che da {n['gives']} {n['cost']}.")
        elif S.get("08"):
            tail = re.search(r"(?m)^\s*Nota:\s*(.+)$", S["08"])
            if tail:
                lines.append(tail.group(1).strip())
        lines.append("Se il Cercatore chiede dove andare, dillo con il nome del luogo, mai con un comando. "
                     "L'oggetto passa solo dopo consegna o pagamento.")
        L.append("LA CATENA DEGLI SCAMBI\n" + "\n".join(lines))

    fac = faction_of(npc)
    if fac:
        tag, fate = fac
        L.append("LA TUA FAZIONE E IL SUO PREZZO\n" + bullet(S["05"], tag) + "\nCosto irreversibile della tua via: "
                 + bullet(S["05"], fate))
    if "Finale" in npc:
        fates = re.findall(r"(?m)^ - ([A-Z]{4,}):", S["05"])
        L.append("I COSTI DELLE VIE (non scegli tu, non spingi, non giudichi)\n"
                 + "\n".join(bullet(S["05"], f) for f in fates))
    if code in rivals:
        L.append("CIO CHE NON SI CONCILIA\n" + incompat(S["05"]))
    if npc.get("Posizione"):
        L.append(f"LA TUA POSIZIONE\n{cap(npc['Posizione'])}")

    # shared knowledge rules; an example naming a rivalry "(A contro B)" is kept only for the NPCs it names
    last = npc["name"].split()[-1]
    know = []
    for t in sentences(" ".join(S["09"].split("\n")[:5])):
        ex = re.search(r"\((\w+)\s+contro\b[^)]*\)", t)      # "(Accusatore contro Accusato)": keep for the accuser only
        if ex and ex.group(1) != last:
            continue
        know.append(t)
    L.append("COSA SAI E COSA NO\n" + " ".join(know))
    return "\n\n".join(L) + "\n"


def build(lore_path: str) -> dict:
    text = open(lore_path, encoding="utf-8").read()
    S = sections(text)
    places, npcs = parse_places(S["06"]), parse_npcs(S["07"])
    chain = parse_chain(S.get("08", ""), npcs)
    inc = incompat(S["05"])
    rivals = {c for c, n in npcs.items() if faction_of(n) or re.search(r"\b%s\b" % re.escape(n["name"].split()[-1]), inc)}
    out = {"ANTEFATTO.txt": antefatto(S["01"])}
    for code, npc in npcs.items():
        if "Servizio" in npc:
            continue
        area = code.split(".")[1]
        name = npc["name"].lower().replace(" ", "")
        out[f"NPC_PREFIX.{area}.{name}.txt"] = prefix(code, npc, places, chain, S, npcs, rivals)
    out["__npcs__"] = (npc_records(S["07"], npcs), places, npcs)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lore", nargs="?", default=os.path.join(HERE, "lore.txt"))
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--npcs", action="store_true", help="write the NPC records into the store (this is the default)")
    ap.add_argument("--no-npcs", action="store_true", help="only report NPC record differences, write nothing to the store")
    ap.add_argument("--root", default=os.path.join(HERE, "database"), help="document store root (default: ./database)")
    a = ap.parse_args()
    files = build(a.lore)
    npc_recs, place_names, npc_blocks = files.pop("__npcs__")
    stale = 0
    for fn, content in sorted(files.items()):
        path = os.path.join(a.out, fn)
        same = os.path.exists(path) and open(path, encoding="utf-8").read() == content
        if a.check:
            stale += not same
            print(("ok     " if same else "STALE  ") + fn)
        elif not same:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"wrote {fn} ({len(content)} chars)")
    # NPC_PREFIX.* is owned by this script: a prefix no NPC maps to any more (renamed or removed NPC) is an orphan
    orphans = sorted(os.path.basename(f) for f in glob.glob(os.path.join(a.out, "NPC_PREFIX.*.txt"))
                     if os.path.basename(f) not in files)
    for fn in orphans:
        if a.check:
            stale += 1
            print("STALE  " + fn + "  (orphan: no NPC in lore.txt maps to it)")
        else:
            os.remove(os.path.join(a.out, fn))
            print(f"removed orphan {fn}")
    write_npcs = not a.no_npcs and not a.check
    drift = sync_npcs(npc_recs, place_names, npc_blocks, a.root, apply=write_npcs)
    if a.check:
        # NPC text drift is normal for a digest, so --check fails on stale generated files only (add --npcs to include it)
        sys.exit(1 if (stale or (drift and a.npcs)) else 0)
