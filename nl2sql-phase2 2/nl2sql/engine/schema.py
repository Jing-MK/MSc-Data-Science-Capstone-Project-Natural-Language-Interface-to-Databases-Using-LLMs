"""Lightweight schema reader for a BIRD SQLite database.

Agents use this to enumerate candidates grounded in the real schema:
the projection agent needs the column list, the join agent needs the
foreign-key graph, the predicate agent needs a column's stored domain.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Column:
    table: str
    name: str
    type: str


@dataclass
class ForeignKey:
    from_table: str
    from_col: str
    to_table: str
    to_col: str


@dataclass
class Schema:
    db_id: str
    tables: List[str] = field(default_factory=list)
    columns: Dict[str, List[Column]] = field(default_factory=dict)   # table -> columns
    foreign_keys: List[ForeignKey] = field(default_factory=list)

    def all_columns(self) -> List[Column]:
        out: List[Column] = []
        for cols in self.columns.values():
            out.extend(cols)
        return out

    def column_names(self) -> List[str]:
        return [c.name for c in self.all_columns()]


class SchemaReader:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def read(self, db_id: str = "") -> Schema:
        conn = sqlite3.connect(self.db_path)
        conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
        schema = Schema(db_id=db_id)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
            tables = [r[0] for r in cur.fetchall()]
            schema.tables = tables
            for t in tables:
                cols: List[Column] = []
                for row in conn.execute(f'PRAGMA table_info("{t}")'):
                    # row: (cid, name, type, notnull, dflt, pk)
                    cols.append(Column(table=t, name=row[1], type=row[2] or ""))
                schema.columns[t] = cols
                for row in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
                    # row: (id, seq, table, from, to, on_update, on_delete, match)
                    schema.foreign_keys.append(
                        ForeignKey(from_table=t, from_col=row[3],
                                   to_table=row[2], to_col=row[4])
                    )
        finally:
            conn.close()
        return schema

    def column_domain(self, table: str, column: str, limit: int = 20) -> List[str]:
        """Sample the distinct stored values of a column (for predicate
        literal enumeration)."""
        conn = sqlite3.connect(self.db_path)
        conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
        try:
            q = f'SELECT DISTINCT "{column}" FROM "{table}" ' \
                f'WHERE "{column}" IS NOT NULL LIMIT {limit}'
            return [str(r[0]) for r in conn.execute(q).fetchall()]
        except Exception:
            return []
        finally:
            conn.close()
