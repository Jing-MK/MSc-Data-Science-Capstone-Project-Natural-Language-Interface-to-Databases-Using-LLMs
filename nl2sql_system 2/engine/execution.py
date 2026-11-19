"""Execution + order-insensitive result comparison (BIRD EX semantics)."""
import sqlite3


def connect(db_path):
    return sqlite3.connect(db_path)


def execute(conn, sql):
    """Return (columns, rows) on success, or ('ERROR', message) on failure."""
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, rows
    except Exception as e:
        return "ERROR", str(e)


def result_key(cols, rows):
    """Canonical signature of a result as an order-insensitive multiset of rows.
    Two queries are equivalent iff they share this key (ignoring row order)."""
    if cols == "ERROR":
        return ("ERROR",)
    try:
        canon = tuple(sorted(tuple(str(v) for v in r) for r in rows))
    except Exception:
        canon = tuple(tuple(str(v) for v in r) for r in rows)
    return (len(rows), canon)


def is_empty(key):
    return key != ("ERROR",) and key[0] == 0


def is_error(key):
    return key == ("ERROR",)
