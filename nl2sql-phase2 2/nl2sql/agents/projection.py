"""Projection agent (decision point D2).

Proposes alternative column sets drawn from schema columns that are
semantically or lexically close to those projected - for instance a code
column and its paired label column, or near-synonymous names (report 5.2).

Projection faces an open-ended space of alternatives, so its enumeration
may be assisted by the LLM (the ``llm_propose`` hook). This agent also
handles the common BIRD case where a column is projected from the wrong
table alias (e.g. "School Name" on frpm vs "School" on schools).
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class ProjectionAgent(Agent):
    axis = "projection"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        sql = self._clean(ctx.predicted_sql)
        cands: List[Candidate] = []

        sel = re.search(r"SELECT\s+(DISTINCT\s+)?(.*?)\s+FROM", sql, re.I | re.S)
        if sel:
            projected = sel.group(2)
            # Only treat a column as a projection choice if it is NOT nested
            # inside a function call or arithmetic expression (those operands
            # belong to the aggregate/arithmetic agents, not projection).
            if re.search(r"[()/*+]", projected):
                proj_cols = []
            else:
                tokens = re.findall(
                    r'"([^"]+)"|`([^`]+)`|\b([A-Za-z_][A-Za-z0-9_ ]*)\b',
                    projected)
                proj_cols = [next(t for t in tok if t) for tok in tokens]

            all_cols = ctx.schema.column_names()
            proj_set = {p.lower() for p in proj_cols}
            for pc in proj_cols:
                # Propose a lexically close column that is NOT already in the
                # projection (swapping a column for one already selected is
                # reordering noise, not a real alternative), and only the
                # single best match, to avoid flooding the triage.
                close = sorted(
                    (c for c in set(all_cols)
                     if c.lower() != pc.lower()
                     and c.lower() not in proj_set
                     and _similar(c, pc) >= 0.72),
                    key=lambda c: -_similar(c, pc),
                )[:1]
                for c in close:
                    alt = _replace_col(sql, pc, c)
                    if alt and alt.lower() != sql.lower():
                        cands.append(Candidate(
                            sql=alt, axis=self.axis, source="enum",
                            note=f'project "{c}" instead of "{pc}"'))

        # LLM-proposed alternatives for the open-ended projection space.
        cands.extend(self._llm_candidates(ctx))
        return _dedup(cands)


def _replace_col(sql: str, old: str, new: str) -> str:
    # Replace the quoted/bare occurrence of a column name, longest-first,
    # whole-token, to avoid substring hits (e.g. "School" inside "School Name").
    for q in ('"', "`"):
        pat = re.escape(q + old + q)
        if re.search(pat, sql):
            return re.sub(pat, q + new + q, sql, count=1)
    # bare token, word-boundary
    pat = r"(?<![\w])" + re.escape(old) + r"(?![\w])"
    if re.search(pat, sql):
        return re.sub(pat, new, sql, count=1)
    return ""


def _dedup(cands: List[Candidate]) -> List[Candidate]:
    seen = set()
    out = []
    for c in cands:
        k = c.sql.strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out
