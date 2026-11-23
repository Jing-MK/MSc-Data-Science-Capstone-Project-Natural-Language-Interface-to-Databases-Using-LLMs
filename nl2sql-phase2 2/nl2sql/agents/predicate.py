"""Predicate agent (decision point D6).

Proposes alternative filters: a different but related filter column, the
addition of a condition named in the question, the removal of a condition,
and alternative literal values drawn from the column's actual stored
domain (report 5.2). Like projection, this clause is open-ended, so its
enumeration may be assisted by the LLM.
"""
from __future__ import annotations

import re
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


class PredicateAgent(Agent):
    axis = "predicate"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []

        where = re.search(r"\bWHERE\b(.*?)(?=\s+(?:GROUP|ORDER|LIMIT|HAVING)\b|$)",
                          sql, re.I | re.S)
        if where:
            # Alternative literal values from the column's stored domain, for
            # equality predicates:  "col" = 'value'
            for m in re.finditer(r'(["`]?[\w ]+["`]?)\s*=\s*\'([^\']*)\'',
                                 where.group(1)):
                col_raw, literal = m.group(1), m.group(2)
                col = col_raw.strip().strip('"`').strip()
                table = self._find_table_for_col(ctx, col)
                if table:
                    domain = ctx.reader.column_domain(table, col, limit=50)
                    lit = literal.strip()
                    close = [v for v in domain
                             if v and v.strip()                      # skip empty
                             and v.lower() != literal.lower()
                             and lit                                 # skip empty literal
                             and (lit.lower() in v.lower()           # zero-padding etc.
                                  or v.lower() in lit.lower())]
                    # Prefer candidates that CONTAIN the original literal
                    # (e.g. '40' -> '0040'); these are the likely intended value.
                    close.sort(key=lambda v: (lit.lower() not in v.lower(), len(v)))
                    for v in close[:2]:
                        alt = sql.replace(f"'{literal}'", f"'{v}'", 1)
                        cands.append(Candidate(
                            sql=alt, axis=self.axis, source="enum",
                            note=f"filter value '{v}' instead of '{literal}'"))

        cands.extend(self._llm_candidates(ctx))
        return cands

    @staticmethod
    def _find_table_for_col(ctx: AgentContext, col: str):
        for t, cols in ctx.schema.columns.items():
            if any(c.name.lower() == col.lower() for c in cols):
                return t
        return None
