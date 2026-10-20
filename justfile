# nexus lore pipeline:  free text --(LLM)--> lore.txt --(script)--> prompt parts + NPC records
set shell := ["bash", "-cu"]
set positional-arguments

py := ".venv/bin/python"

# list the recipes
default:
    @just --list

# free text -> lore.txt via an LLM (backs up the old lore.txt). just compile story.txt [more.txt] [--model M] [--title T]
compile *files:
    {{py}} digest_lore.py "$@"

# lore.txt -> ANTEFATTO.txt + NPC_PREFIX.*.txt + NPC records (backed up first); --no-npcs to skip records, --check to test freshness
lore *args:
    {{py}} compile_lore.py "$@"

# browse a live SQLite db read-only in a web UI on all interfaces (port 8081); default is the nexus store, e.g. just sqlite_web .opencode/opencode.db
sqlite_web db="database/nexus.db" *args:
    sqlite_web -r {{db}} --host 0.0.0.0 --port 8081 "${@:2}"
