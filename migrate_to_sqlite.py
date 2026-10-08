#!/usr/bin/env python3
"""Import a file-based Nexus database directory into a SQLite database.

    python migrate_to_sqlite.py [--src database] [--dst database/nexus.db] [--force]

Copies every document (NPCs, Locations, Storyboards, player state/profile/inventory,
conversation history and analysis), keeping modification times, then re-reads the
SQLite copy and compares it with the source. Exits non-zero if anything differs.
The source directory is never modified.
"""
import argparse
import os
import sys

from doc_store import KINDS, FileDocStore, SqliteDocStore


def migrate(src: str, dst: str, force: bool = False) -> int:
    if not os.path.isdir(src):
        print(f"source directory not found: {src}")
        return 2
    if os.path.exists(dst):
        if not force:
            print(f"{dst} already exists; use --force to overwrite")
            return 2
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(dst + suffix):
                os.remove(dst + suffix)

    fs, ss = FileDocStore(src), SqliteDocStore(dst)
    total = 0
    for kind in KINDS:
        items = fs.items(kind)
        for key, value, mtime, _size in items:
            ss.put(kind, key, value, mtime=mtime)
        total += len(items)
        print(f"  {kind:22} {len(items):5} documents")

    bad = 0
    for kind in KINDS:
        want = {k: v for k, v, _m, _s in fs.items(kind)}
        got = {k: v for k, v, _m, _s in ss.items(kind)}
        if want != got:
            bad += 1
            print(f"  MISMATCH in {kind}: {sorted(set(want) ^ set(got))[:5]}")
    print(f"{total} documents -> {dst}; verification {'FAILED' if bad else 'ok'}")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="database")
    ap.add_argument("--dst", default=None, help="default: <src>/nexus.db")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    sys.exit(migrate(a.src, a.dst or os.path.join(a.src, "nexus.db"), a.force))
