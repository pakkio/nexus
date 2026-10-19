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

# lore.txt -> ANTEFATTO.txt + NPC_PREFIX.*.txt; add --npcs to write NPC records, --check to test freshness
lore *args:
    {{py}} compile_lore.py "$@"
