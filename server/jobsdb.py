"""ConFlow 服务端 · 任务列表持久化（SQLite：server-data/jobs.db）。

任务仍常驻内存（app.JOBS），每次变更即落盘；服务重启时全量回载。
"""
from __future__ import annotations

import json
import sqlite3

from . import store

DB_PATH = store.DATA_DIR / "jobs.db"


_DB_INITED = False


def _conn() -> sqlite3.Connection:
    global _DB_INITED
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    if not _DB_INITED:            # 老库惰性自愈：缺表自动补
        try:
            init()
            _DB_INITED = True
        except Exception:
            pass
    return conn


def init() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS jobs ("
                  "id TEXT PRIMARY KEY, t0 REAL NOT NULL, data TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS subs ("
                  "id TEXT PRIMARY KEY, url TEXT NOT NULL, name TEXT DEFAULT '',"
                  "doc_type TEXT DEFAULT 'auto', interval_hours INTEGER DEFAULT 24,"
                  "max_new INTEGER DEFAULT 5, last_check REAL DEFAULT 0,"
                  "enabled INTEGER DEFAULT 1, created TEXT DEFAULT '',"
                  "language TEXT DEFAULT 'zh', script INTEGER DEFAULT 0,"
                  "storyboard INTEGER DEFAULT 0)")
        for col, ddl in (("language", "TEXT DEFAULT 'zh'"),
                         ("script", "INTEGER DEFAULT 0"),
                         ("storyboard", "INTEGER DEFAULT 0")):
            try:                      # 老库迁移
                c.execute(f"ALTER TABLE subs ADD COLUMN {col} {ddl}")
            except Exception:
                pass


def save(job: dict) -> None:
    try:
        with _conn() as c:
            c.execute("INSERT OR REPLACE INTO jobs (id, t0, data) VALUES (?, ?, ?)",
                      (job["id"], float(job.get("t0") or 0.0),
                       json.dumps(job, ensure_ascii=False)))
    except Exception:
        pass  # 持久化失败不阻塞任务（内存态仍是权威）


def delete(jid: str) -> None:
    try:
        with _conn() as c:
            c.execute("DELETE FROM jobs WHERE id = ?", (jid,))
    except Exception:
        pass


def all() -> list[dict]:
    """按创建时间回载全部任务；库不存在时返回空。"""
    if not DB_PATH.exists():
        return []
    try:
        with _conn() as c:
            rows = c.execute("SELECT data FROM jobs ORDER BY t0").fetchall()
        return [json.loads(r[0]) for r in rows]
    except Exception:
        return []


# ------------------------------------------------------------- 订阅 subs ----

_SUB_COLS = ("id", "url", "name", "doc_type", "interval_hours",
             "max_new", "last_check", "enabled", "created",
             "language", "script", "storyboard")


def sub_add(sub: dict) -> None:
    with _conn() as c:
        c.execute(f"INSERT OR REPLACE INTO subs VALUES ({','.join('?' * len(_SUB_COLS))})",
                  tuple(sub.get(k) for k in _SUB_COLS))


def sub_all() -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        with _conn() as c:
            rows = c.execute(f"SELECT {','.join(_SUB_COLS)} FROM subs").fetchall()
        return [dict(zip(_SUB_COLS, r)) for r in rows]
    except Exception:
        return []


def sub_get(sid: str) -> dict | None:
    for s in sub_all():
        if s["id"] == sid:
            return s
    return None


def sub_update(sid: str, **fields) -> None:
    keys = [k for k in fields if k in _SUB_COLS]
    if not keys:
        return
    with _conn() as c:
        c.execute(f"UPDATE subs SET {','.join(k + '=?' for k in keys)} WHERE id=?",
                  [fields[k] for k in keys] + [sid])


def sub_delete(sid: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM subs WHERE id = ?", (sid,))
