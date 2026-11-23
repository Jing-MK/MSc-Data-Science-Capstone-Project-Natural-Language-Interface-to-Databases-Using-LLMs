"""Structural agents whose clause has a small, enumerable set of variants
(report 5.2): DISTINCT on/off, COUNT over rows vs distinct values,
alternative grouping/sort keys.

These enumerate deterministically from a fixed set of clause variants and
need no LLM.
"""
from __future__ import annotations

import re
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


class DistinctAgent(Agent):
    axis = "distinct"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []
        has_distinct = re.search(r"\bSELECT\s+DISTINCT\b", sql, re.I)
        if has_distinct:
            toggled = re.sub(r"(\bSELECT\s+)DISTINCT\s+", r"\1", sql, count=1, flags=re.I)
            cands.append(Candidate(sql=toggled, axis=self.axis, source="enum",
                                   note="remove DISTINCT (keep duplicates)"))
        else:
            toggled = re.sub(r"(\bSELECT\s+)", r"\1DISTINCT ", sql, count=1, flags=re.I)
            cands.append(Candidate(sql=toggled, axis=self.axis, source="enum",
                                   note="add DISTINCT (remove duplicates)"))
        return cands


class AggregateAgent(Agent):
    axis = "aggregate"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []
        # Only act on a real COUNT(...) aggregate. Match the aggregate token
        # with a word boundary so "Count" inside a quoted column name like
        # "Free Meal Count (K-12)" is never treated as the function.
        for m in re.finditer(r"(?<![\w\"`])COUNT\s*\(\s*(DISTINCT\s+)?"
                             r'("[^"]+"|`[^`]+`|[\w.]+)\s*\)', sql, re.I):
            inner_distinct, col = m.group(1), m.group(2).strip()
            if inner_distinct:
                alt = sql[:m.start()] + f"COUNT({col})" + sql[m.end():]
                note = "COUNT over all rows instead of distinct values"
            else:
                alt = sql[:m.start()] + f"COUNT(DISTINCT {col})" + sql[m.end():]
                note = "COUNT over distinct values instead of all rows"
            cands.append(Candidate(sql=alt, axis=self.axis, source="enum", note=note))
            break
        return cands


class GroupByAgent(Agent):
    axis = "group_by"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        # Grouping changes are context specific; the deterministic variant we
        # enumerate is dropping an over-eager GROUP BY. Richer alternatives
        # come from the LLM hook for this clause when enabled.
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []
        m = re.search(r"\sGROUP\s+BY\s+.*?(?=\s+(?:ORDER|LIMIT|HAVING)\b|$)", sql, re.I | re.S)
        if m:
            alt = sql[:m.start()] + sql[m.end():]
            cands.append(Candidate(sql=alt.strip(), axis=self.axis, source="enum",
                                   note="remove GROUP BY"))
        return cands


class OrderAgent(Agent):
    axis = "order"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []
        # Flip ASC/DESC on an existing ORDER BY.
        if re.search(r"\bORDER\s+BY\b", sql, re.I):
            if re.search(r"\bDESC\b", sql, re.I):
                alt = re.sub(r"\bDESC\b", "ASC", sql, count=1, flags=re.I)
                note = "sort ascending instead of descending"
            else:
                # add DESC to the order-by target
                alt = re.sub(r"(\bORDER\s+BY\s+[^\s]+)", r"\1 DESC", sql, count=1, flags=re.I)
                note = "sort descending instead of ascending"
            cands.append(Candidate(sql=alt, axis=self.axis, source="enum", note=note))
        return cands
