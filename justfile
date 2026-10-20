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

# regenerate the lore pages (projects/nexus/VEIL-*.md) from lore.txt; --check to test freshness
docs *args:
    {{py}} build_docs.py "$@"

# regenerate the catalogue of GitHub projects (projects/*/README.md and the hub projects/README.md)
projects *args:
    {{py}} build_projects.py "$@"

# browse a live SQLite db read-only in a web UI on all interfaces (port 8081), in tmux session "sqlite_web" (restarted if running); default is the nexus store, e.g. just db .opencode/opencode.db
db path="database/nexus.db" *args:
    tmux kill-session -t sqlite_web 2>/dev/null || true
    sleep 1
    tmux new-session -d -s sqlite_web -c "$PWD" "exec sqlite_web -r {{path}} --host 0.0.0.0 --port 8081 {{args}}"
    for i in $(seq 1 10); do sleep 1; [ "$(curl -s -m2 -o /dev/null -w '%{http_code}' localhost:8081/)" = 200 ] && echo "sqlite_web up on :8081 ({{path}}, tmux session sqlite_web)" && exit 0; done; echo "sqlite_web did not come up"; exit 1

# stop the sqlite_web server started by just db (kills its tmux session)
db-kill:
    tmux kill-session -t sqlite_web 2>/dev/null && echo "sqlite_web stopped" || echo "sqlite_web not running"
