"""Join agent (decision point D1).

Proposes alternative table sets and join paths over the schema's
foreign-key graph (report 5.2). The common BIRD case is a prediction that
reads a column from a single table when the gold query joins a second
table that also holds a same-named column (the "school type from T1 or
T2?" ambiguity). This agent enumerates adding a foreign-key-reachable
table.
"""
from __future__ import annotations

import re
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


class JoinAgent(Agent):
    axis = "join"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []

        # Tables currently referenced in FROM/JOIN.
        used = set(t.lower() for t in re.findall(
            r'\b(?:FROM|JOIN)\s+["`]?(\w+)["`]?', sql, re.I))
        if not used:
            return cands

        # Candidate tables reachable by a single foreign key from a used table.
        reachable = []
        for fk in ctx.schema.foreign_keys:
            if fk.from_table.lower() in used and fk.to_table.lower() not in used:
                reachable.append((fk.from_table, fk.from_col, fk.to_table, fk.to_col))
            elif fk.to_table.lower() in used and fk.from_table.lower() not in used:
                reachable.append((fk.to_table, fk.to_col, fk.from_table, fk.from_col))

        # Enumerate adding one reachable table as an INNER JOIN. We expose the
        # alternative as a note; the actual rewrite for complex joins is left
        # to the regeneration step (report 5.5). Here we add a simple join
        # that the executor can run when the structure permits.
        for (ut, uc, nt, nc) in reachable[:3]:
            # Only produce a runnable rewrite for the simple single-FROM case.
            m = re.search(r'\bFROM\s+["`]?(\w+)["`]?(\s+AS\s+\w+)?', sql, re.I)
            if m and m.group(1).lower() == ut.lower():
                join_clause = f' INNER JOIN "{nt}" ON "{ut}"."{uc}" = "{nt}"."{nc}"'
                alt = sql[:m.end()] + join_clause + sql[m.end():]
                cands.append(Candidate(
                    sql=alt, axis=self.axis, source="enum",
                    note=f"also join table {nt} (reachable via foreign key)"))
        return cands
