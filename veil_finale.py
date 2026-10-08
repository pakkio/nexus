"""The finale: Meridia, the faction gate and the recorded fate of the Veil.

Canonical factions (from the storyboard) and the fate each one stands for:

    Custodi della Memoria     Lyra   -> preserve   (renew the Veil, rebuild the Sacrifice)
    Progressisti              Theron -> dissolve   (let the Veil go, face the Oblivion)
    Viandanti dell'Equilibrio Boros  -> transform  (evolve the Veil into something new)

Meridia "does not appear" until the player has really talked (not merely traded
or used commands) with all three faction leaders. Then the player chooses with
/choose <fate>; the choice is irreversible and stored in plot_flags.
"""
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

MERIDIA_CODE = "NPC.nexusofpaths.meridia"
MERIDIA_AREA = "Nexus of Paths"
LOOM_ITEM = "Il Telaio del Nuovo Inizio"

TURNS_KEY = "_faction_turns"      # {faction: number of dialogue turns with its leader}
FATE_KEY = "_veil_fate"
FATE_AT_KEY = "_veil_fate_at"

FACTIONS: Dict[str, Dict[str, str]] = {
    "memory":  {"leader_code": "NPC.sanctumofwhispers.lyra", "leader": "Lyra",
                "name": "Custodi della Memoria",      "fate": "preserve"},
    "progress": {"leader_code": "NPC.city.theron",           "leader": "Theron",
                "name": "Progressisti",               "fate": "dissolve"},
    "balance": {"leader_code": "NPC.mountain.boros",         "leader": "Boros",
                "name": "Viandanti dell'Equilibrio",  "fate": "transform"},
}

FATES: Dict[str, str] = {
    "preserve": "Rinnovare e preservare il Velo: ricostruire la memoria dei Tessitori e rinnovare il Sacrificio Originale "
                "(la via dei Custodi della Memoria, di Lyra)",
    "dissolve": "Lasciar dissolvere il Velo: liberare Eldoria dalla reliquia del passato e affrontare gli Oblivianti "
                "con la propria forza (la via dei Progressisti, di Theron)",
    "transform": "Trasformare il Velo: farlo evolvere in qualcosa di nuovo che onori il passato senza imprigionare il futuro "
                 "(la via dei Viandanti dell'Equilibrio, di Boros)",
}

_FATE_ALIASES = {
    "preserve": "preserve", "preserva": "preserve", "preservare": "preserve", "renew": "preserve",
    "rinnova": "preserve", "rinnovare": "preserve", "restore": "preserve", "repair": "preserve", "ripara": "preserve",
    "dissolve": "dissolve", "dissolvi": "dissolve", "dissolvere": "dissolve", "release": "dissolve",
    "destroy": "dissolve", "distruggi": "dissolve", "distruggere": "dissolve", "letgo": "dissolve",
    "transform": "transform", "trasforma": "transform", "trasformare": "transform", "evolve": "transform",
    "evolvi": "transform",
}


def turns_required() -> int:
    try:
        return max(1, int(os.environ.get("FACTION_GATE_TURNS", "3")))
    except ValueError:
        return 3


def faction_of_npc(npc_code: Optional[str]) -> Optional[str]:
    for fid, f in FACTIONS.items():
        if f["leader_code"] == npc_code:
            return fid
    return None


def normalize_fate(text: str) -> Optional[str]:
    return _FATE_ALIASES.get((text or "").strip().lower().replace(" ", "").replace("-", ""))


def progress(plot_flags: Optional[dict]) -> Dict[str, int]:
    turns = (plot_flags or {}).get(TURNS_KEY) or {}
    return {fid: int(turns.get(fid, 0)) for fid in FACTIONS}


def gate_status(plot_flags: Optional[dict]) -> Tuple[bool, List[str]]:
    """(open?, leaders still to hear)."""
    need = turns_required()
    prog = progress(plot_flags)
    missing = [FACTIONS[f]["leader"] for f, n in prog.items() if n < need]
    return (not missing), missing


def record_dialogue_turn(plot_flags: dict, npc_code: Optional[str]) -> Optional[str]:
    """Count one real dialogue turn with a faction leader. Returns the faction id if counted."""
    fid = faction_of_npc(npc_code)
    if not fid:
        return None
    turns = plot_flags.setdefault(TURNS_KEY, {})
    turns[fid] = int(turns.get(fid, 0)) + 1
    return fid


def chosen_fate(plot_flags: Optional[dict]) -> Optional[str]:
    return (plot_flags or {}).get(FATE_KEY)


def record_fate(plot_flags: dict, fate: str) -> None:
    plot_flags[FATE_KEY] = fate
    plot_flags[FATE_AT_KEY] = datetime.now().isoformat(timespec="seconds")


def locked_message(missing: List[str], plot_flags: Optional[dict] = None) -> str:
    prog = progress(plot_flags)
    need = turns_required()
    parts = [f"{FACTIONS[f]['leader']} ({FACTIONS[f]['name']}): {min(n, need)}/{need}" for f, n in prog.items()]
    return ("Il Nesso dei Sentieri è vuoto: Meridia non si mostra a chi non ha ascoltato tutte le voci. "
            "Parla davvero con " + ", ".join(missing) + " prima di tornare. Progresso: " + "; ".join(parts) + ".")


def meridia_prompt_lines(plot_flags: Optional[dict]) -> List[str]:
    """Extra, authoritative instructions injected into Meridia's system prompt."""
    fate = chosen_fate(plot_flags)
    lines = [
        "",
        "=" * 60,
        "FINALE - REGOLE DI MERIDIA (hanno la precedenza su tutto il resto)",
        "=" * 60,
        "Le fazioni sono ESATTAMENTE tre, non inventarne altre:",
    ]
    for f in FACTIONS.values():
        lines.append(f"- {f['name']} (guidati da {f['leader']}): {FATES[f['fate']]}")
    lines += [
        "Il Cercatore ha il DIRITTO di scegliere il destino del Velo. Tu non scegli per lui, non lo spingi, "
        "non giudichi: esponi le tre vie con il loro prezzo e lo accompagni nella consapevolezza.",
    ]
    if fate:
        lines += [f"IL CERCATORE HA GIÀ SCELTO: {fate}. La scelta è irrevocabile. Descrivi la conseguenza con rispetto, "
                  "non offrire altre scelte e non riaprire la decisione."]
    else:
        lines += [
            "Quando il Cercatore ti dice chiaramente quale via sceglie, conferma che la scelta non ha ritorno e digli di "
            "pronunciarla con il comando /choose preserve, /choose dissolve oppure /choose transform "
            "(questa è l'unica eccezione al divieto di citare comandi). Non dichiarare mai la scelta compiuta tu stessa.",
        ]
    return lines
