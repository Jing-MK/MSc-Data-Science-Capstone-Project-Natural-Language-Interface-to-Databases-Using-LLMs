"""Lightweight schema introspection used by the enumeration agents."""
from .execution import execute


def get_tables(conn):
    cols, rows = execute(conn, "SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in rows] if cols != "ERROR" else []


def get_columns(conn, table):
    """Return list of column names for a table (handles spaces via quoting)."""
    cols, rows = execute(conn, f'PRAGMA table_info("{table}")')
    return [r[1] for r in rows] if cols != "ERROR" else []


def get_foreign_keys(conn, table):
    """Return list of (from_col, ref_table, ref_col)."""
    cols, rows = execute(conn, f'PRAGMA foreign_key_list("{table}")')
    if cols == "ERROR":
        return []
    return [(r[3], r[2], r[4]) for r in rows]


def column_domain(conn, table, column, limit=50):
    """Distinct stored values of a column (for value-level enumeration)."""
    cols, rows = execute(
        conn, f'SELECT DISTINCT "{column}" FROM "{table}" '
              f'WHERE "{column}" IS NOT NULL LIMIT {limit}')
    return [r[0] for r in rows] if cols != "ERROR" else []


def all_columns(conn):
    """Map column_name(lower) -> list of (table, actual_name)."""
    out = {}
    for t in get_tables(conn):
        for c in get_columns(conn, t):
            out.setdefault(c.lower(), []).append((t, c))
    return out
