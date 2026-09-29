"""ConFlow 服务端 · 任务列表持久化（SQLite：server-data/jobs.db）。

任务仍常驻内存（app.JOBS），每次变更即落盘；服务重启时全量回载。
"""
from __future__ import annotations

import json
import sqlite3

from . import store

DB_PATH = store.DATA_DIR / "jobs.db"


def _conn() -> sqlite3.Connection:
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=5)


def init() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS jobs ("
                  "id TEXT PRIMARY KEY, t0 REAL NOT NULL, data TEXT NOT NULL)")


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
