"""Database access: schema introspection and guarded, read-only execution."""
import os
import sqlite3

import pandas as pd

import guard
import seed

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")
MAX_ROWS = 500


def ensure_db() -> None:
    if not os.path.exists(DB_PATH):
        seed.build(DB_PATH)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.set_authorizer(guard.read_only_authorizer)
    return con


def schema_text() -> str:
    """Describe every table as 'name(col type, ...)' plus its foreign keys."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    lines = []
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        cols = [f"{c[1]} {c[2]}{' PK' if c[5] else ''}" for c in con.execute(f"PRAGMA table_info({table})")]
        line = f"{table}({', '.join(cols)})"
        fks = [f"{f[3]} -> {f[2]}.{f[4]}" for f in con.execute(f"PRAGMA foreign_key_list({table})")]
        if fks:
            line += "  FK: " + "; ".join(fks)
        lines.append(line)
    con.close()
    return "\n".join(lines)


def run(sql: str) -> pd.DataFrame:
    """Validate, then execute. Raises guard.UnsafeSQL or sqlite3.Error."""
    safe = guard.check(sql)
    con = _connect()
    try:
        cur = con.execute(safe)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(MAX_ROWS)
        return pd.DataFrame(rows, columns=cols)
    finally:
        con.close()
