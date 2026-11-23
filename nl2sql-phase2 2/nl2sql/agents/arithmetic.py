"""Arithmetic agent (decision point D8).

Proposes casts and formula rewrites, including those implied by the
question's evidence (report 5.2). The recurring BIRD defect is an integer
division that SQLite truncates to zero; inserting a CAST to a real type is
a deterministic repair carrying an objective signal (report 4.5).
"""
from __future__ import annotations

import re
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


class ArithmeticAgent(Agent):
    axis = "arithmetic"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []

        # Division without a cast:  A / B  where neither side is CAST/REAL.
        # Add CAST(... AS REAL) around the numerator of the first bare division.
        # Operands are quoted identifiers or bare words (not spanning quotes).
        operand = r'("[^"]+"|`[^`]+`|\b[\w.]+\b)'
        m = re.search(operand + r'\s*/\s*' + operand, sql)
        if m and "cast" not in sql.lower():
            num, den = m.group(1).strip(), m.group(2).strip()
            alt = sql[:m.start()] + f"CAST({num} AS REAL) / {den}" + sql[m.end():]
            cands.append(Candidate(
                sql=alt, axis=self.axis, source="enum", objective=True,
                note="cast to REAL so integer division is not truncated"))
        return cands
