"""SQL execution against a BIRD SQLite database.

Implements the order-insensitive result comparison of report Section 3.2:
two results are equal if they contain the same multiset of rows,
irrespective of row order.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from ..types import ExecResult, ResultKey


def _strip_suffix(sql: str) -> str:
    """Predictions in the BIRD prediction file carry a trailing
    '\\t----- bird -----\\t<db_id>' marker; remove it."""
    return sql.split("----- bird -----")[0].strip().rstrip(";")


class Executor:
    """Executes queries against one database file, with a busy timeout."""

    def __init__(self, db_path: str, busy_timeout_ms: int = 5000):
        self.db_path = db_path
        self.busy_timeout_ms = busy_timeout_ms

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=self.busy_timeout_ms / 1000.0)
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        # BIRD column names contain spaces/parentheses; text_factory keeps them safe.
        conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
        return conn

    def run(self, sql: str) -> ExecResult:
        sql = _strip_suffix(sql)
        if not sql:
            return ExecResult(ok=False, error="empty query")
        conn = None
        try:
            conn = self._connect()
            cur = conn.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return ExecResult(ok=True, rows=rows, columns=cols)
        except Exception as e:  # noqa: BLE001 - we want any SQL error as a string
            return ExecResult(ok=False, error=f"{type(e).__name__}: {e}")
        finally:
            if conn is not None:
                conn.close()


def result_key(res: ExecResult) -> ResultKey:
    """Order-insensitive key for a result's row multiset.

    Failed executions are keyed by their error so that all crashing
    candidates cluster together and apart from any successful one.
    """
    if not res.ok:
        return f"__error__:{res.error}"
    # Sort rows so that order does not matter; stringify cells for a stable key.
    normalized = sorted(tuple(str(c) for c in row) for row in res.rows)
    return repr(normalized)


def results_equal(a: ExecResult, b: ExecResult) -> bool:
    """True if two results are equal under the order-insensitive comparison."""
    if not a.ok or not b.ok:
        return False
    return result_key(a) == result_key(b)
