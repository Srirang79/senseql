"""SQL safety gate. Only a single read-only SELECT (or WITH ... SELECT) gets through."""
import re
import sqlite3

BLOCKED = {
    "insert", "update", "delete", "drop", "alter", "create", "replace", "truncate",
    "attach", "detach", "pragma", "vacuum", "reindex", "analyze", "begin", "commit",
    "rollback", "savepoint", "release",
}


class UnsafeSQL(ValueError):
    pass


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def _outside_strings(sql: str) -> str:
    """Remove quoted literals and identifiers so keyword checks only see real SQL."""
    return re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|`[^`]*`|\[[^\]]*\]", " ", sql)


def check(sql: str) -> str:
    """Return the cleaned query or raise UnsafeSQL with a reason a user can read."""
    if not sql or not sql.strip():
        raise UnsafeSQL("The model returned no SQL.")
    cleaned = _strip_comments(sql).strip().rstrip(";").strip()
    bare = _outside_strings(cleaned)
    if ";" in bare:
        raise UnsafeSQL("Only one statement is allowed.")
    first = bare.split(None, 1)[0].lower() if bare.split() else ""
    if first not in ("select", "with"):
        raise UnsafeSQL(f"Only SELECT queries are allowed (got '{first.upper() or 'nothing'}').")
    words = set(re.findall(r"[a-z_]+", bare.lower()))
    hit = sorted(words & BLOCKED)
    if hit:
        raise UnsafeSQL(f"Blocked keyword: {hit[0].upper()}.")
    if not sqlite3.complete_statement(cleaned + ";"):
        raise UnsafeSQL("The SQL looks incomplete (unbalanced quotes or brackets).")
    return cleaned


def read_only_authorizer(action, arg1, arg2, db_name, source):
    """Second layer: SQLite itself refuses anything that is not a read."""
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
