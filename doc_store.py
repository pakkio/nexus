"""Document stores behind DbManager's non-MySQL ("mockup") mode.

Two interchangeable backends with the same API:

* FileDocStore   -- the original JSON-files-in-a-directory layout (default).
* SqliteDocStore -- one SQLite file (WAL), same documents, atomic writes.

Documents are grouped by *kind* and addressed by *key*:

    NPCs, Locations, Storyboards     key = "NPC.forest.elira" (file name sans .json)
    PlayerState, PlayerProfiles      key = player id
    Inventory                        key = player id
    ConversationAnalysis             key = player id (value is plain text)
    ConversationHistory              key = "<player id>/<npc code>"

Select the backend with NEXUS_STORAGE=file|sqlite (NEXUS_SQLITE_PATH sets the
database file, default "<mockup_dir>/nexus.db").
"""
import json
import os
import shutil
import sqlite3
import threading
import time
from typing import Any, Iterator, List, Optional, Tuple

KINDS = ("NPCs", "Locations", "Storyboards", "PlayerState", "PlayerProfiles",
         "Inventory", "ConversationAnalysis", "ConversationHistory")

# Item = (key, value, mtime, size_in_bytes)
Item = Tuple[str, Any, float, int]


def _check_key(key: str, nested: bool = False) -> str:
    if not key or not isinstance(key, str):
        raise ValueError("empty document key")
    parts = key.split("/") if nested else [key]
    for p in parts:
        if not p or p in (".", "..") or "\\" in p or "\x00" in p or (not nested and "/" in p):
            raise ValueError(f"unsafe document key: {key!r}")
    return key


class FileDocStore:
    """JSON files under a root directory (the pre-existing on-disk layout)."""
    backend = "file"

    # kind -> (relative path template, text?)
    _LAYOUT = {
        "NPCs": ("NPCs/{key}.json", False),
        "Locations": ("Locations/{key}.json", False),
        "Storyboards": ("Storyboards/{key}.json", False),
        "PlayerState": ("PlayerState/{key}.json", False),
        "PlayerProfiles": ("PlayerProfiles/{key}.json", False),
        "Inventory": ("{key}_inventory.json", False),
        "ConversationAnalysis": ("ConversationAnalysis/{key}_analysis.txt", True),
        "ConversationHistory": ("ConversationHistory/{key}.json", False),
    }

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)
        for sub in ("NPCs", "Locations", "Storyboards", "PlayerState",
                    "PlayerProfiles", "ConversationHistory"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)

    def _path(self, kind: str, key: str) -> str:
        tmpl, _ = self._LAYOUT[kind]
        _check_key(key, nested=(kind == "ConversationHistory"))
        return os.path.join(self.root, tmpl.format(key=key))

    def _read(self, kind: str, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return f.read() if self._LAYOUT[kind][1] else json.load(f)

    def get(self, kind: str, key: str) -> Optional[Any]:
        path = self._path(kind, key)
        if not os.path.exists(path):
            return None
        try:
            return self._read(kind, path)
        except Exception:
            return None

    def put(self, kind: str, key: str, value: Any, mtime: Optional[float] = None) -> None:
        path = self._path(kind, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            if self._LAYOUT[kind][1]:
                f.write(value)
            else:
                json.dump(value, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        if mtime is not None:
            os.utime(path, (mtime, mtime))

    def delete(self, kind: str, key: str) -> None:
        path = self._path(kind, key)
        if os.path.exists(path):
            os.remove(path)

    def meta(self, kind: str, key: str) -> Optional[Tuple[float, int]]:
        path = self._path(kind, key)
        if not os.path.exists(path):
            return None
        return os.path.getmtime(path), os.path.getsize(path)

    def _files(self, kind: str, prefix: str) -> Iterator[Tuple[str, str]]:
        """Yield (key, path) for every document of a kind under an optional prefix."""
        text = self._LAYOUT[kind][1]
        suffix = ".txt" if text else ".json"
        if kind == "Inventory":
            base, pre, post = self.root, "", "_inventory.json"
        elif kind == "ConversationAnalysis":
            base, pre, post = os.path.join(self.root, "ConversationAnalysis"), "", "_analysis.txt"
        elif kind == "ConversationHistory":
            player = prefix.rstrip("/")
            base = os.path.join(self.root, "ConversationHistory", player) if player else \
                os.path.join(self.root, "ConversationHistory")
            if not os.path.isdir(base):
                return
            if player:
                for fn in sorted(os.listdir(base)):
                    if fn.endswith(".json"):
                        yield f"{player}/{fn[:-5]}", os.path.join(base, fn)
            else:
                for pl in sorted(os.listdir(base)):
                    pdir = os.path.join(base, pl)
                    if os.path.isdir(pdir):
                        for fn in sorted(os.listdir(pdir)):
                            if fn.endswith(".json"):
                                yield f"{pl}/{fn[:-5]}", os.path.join(pdir, fn)
            return
        else:
            base, pre, post = os.path.join(self.root, kind), "", suffix
        if not os.path.isdir(base):
            return
        for fn in sorted(os.listdir(base)):
            if fn.endswith(post) and fn.startswith(pre):
                key = fn[len(pre):-len(post)]
                if key and key.startswith(prefix):
                    yield key, os.path.join(base, fn)

    def items(self, kind: str, prefix: str = "") -> List[Item]:
        out: List[Item] = []
        for key, path in self._files(kind, prefix):
            try:
                out.append((key, self._read(kind, path), os.path.getmtime(path), os.path.getsize(path)))
            except Exception:
                continue
        return out

    def delete_kind(self, kind: str, prefix: str = "") -> int:
        n = 0
        for key, path in list(self._files(kind, prefix)):
            os.remove(path)
            n += 1
        if kind == "ConversationHistory" and not prefix:
            shutil.rmtree(os.path.join(self.root, "ConversationHistory"), ignore_errors=True)
            os.makedirs(os.path.join(self.root, "ConversationHistory"), exist_ok=True)
        return n


class SqliteDocStore:
    """All documents in one SQLite database (WAL mode, one short connection per call)."""
    backend = "sqlite"

    def __init__(self, path: str):
        self.path = path
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""CREATE TABLE IF NOT EXISTS docs (
                           kind  TEXT NOT NULL,
                           key   TEXT NOT NULL,
                           body  TEXT NOT NULL,
                           mtime REAL NOT NULL,
                           PRIMARY KEY (kind, key)) WITHOUT ROWID""")

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=15)
        c.execute("PRAGMA busy_timeout=15000")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    @staticmethod
    def _check_kind(kind: str) -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown document kind: {kind!r}")

    def get(self, kind: str, key: str) -> Optional[Any]:
        self._check_kind(kind)
        _check_key(key, nested=(kind == "ConversationHistory"))
        c = self._conn()
        try:
            row = c.execute("SELECT body FROM docs WHERE kind=? AND key=?", (kind, key)).fetchone()
        finally:
            c.close()
        return json.loads(row[0]) if row else None

    def put(self, kind: str, key: str, value: Any, mtime: Optional[float] = None) -> None:
        self._check_kind(kind)
        _check_key(key, nested=(kind == "ConversationHistory"))
        body = json.dumps(value, ensure_ascii=False)
        c = self._conn()
        try:
            with c:
                c.execute("INSERT INTO docs(kind,key,body,mtime) VALUES(?,?,?,?) "
                          "ON CONFLICT(kind,key) DO UPDATE SET body=excluded.body, mtime=excluded.mtime",
                          (kind, key, body, time.time() if mtime is None else mtime))
        finally:
            c.close()

    def delete(self, kind: str, key: str) -> None:
        self._check_kind(kind)
        c = self._conn()
        try:
            with c:
                c.execute("DELETE FROM docs WHERE kind=? AND key=?", (kind, key))
        finally:
            c.close()

    def meta(self, kind: str, key: str) -> Optional[Tuple[float, int]]:
        self._check_kind(kind)
        c = self._conn()
        try:
            row = c.execute("SELECT mtime, LENGTH(CAST(body AS BLOB)) FROM docs WHERE kind=? AND key=?",
                            (kind, key)).fetchone()
        finally:
            c.close()
        return (row[0], row[1]) if row else None

    def items(self, kind: str, prefix: str = "") -> List[Item]:
        self._check_kind(kind)
        if kind == "ConversationHistory" and prefix and not prefix.endswith("/"):
            prefix += "/"
        c = self._conn()
        try:
            rows = c.execute("SELECT key, body, mtime, LENGTH(CAST(body AS BLOB)) FROM docs "
                             "WHERE kind=? AND substr(key, 1, ?) = ? ORDER BY key",
                             (kind, len(prefix), prefix)).fetchall()
        finally:
            c.close()
        return [(k, json.loads(b), m, s) for k, b, m, s in rows]

    def delete_kind(self, kind: str, prefix: str = "") -> int:
        self._check_kind(kind)
        if kind == "ConversationHistory" and prefix and not prefix.endswith("/"):
            prefix += "/"
        c = self._conn()
        try:
            with c:
                cur = c.execute("DELETE FROM docs WHERE kind=? AND substr(key, 1, ?) = ?",
                                (kind, len(prefix), prefix))
                return cur.rowcount
        finally:
            c.close()


def make_store(root: str, backend: Optional[str] = None, sqlite_path: Optional[str] = None):
    """Build the configured store. backend: 'file' (default) or 'sqlite'."""
    backend = (backend or os.environ.get("NEXUS_STORAGE", "file")).strip().lower()
    if backend == "sqlite":
        return SqliteDocStore(sqlite_path or os.environ.get("NEXUS_SQLITE_PATH")
                              or os.path.join(root, "nexus.db"))
    if backend in ("file", "files", "json"):
        return FileDocStore(root)
    raise ValueError(f"unknown NEXUS_STORAGE backend: {backend!r}")
