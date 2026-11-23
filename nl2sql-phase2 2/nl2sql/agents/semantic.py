"""Semantic agents (report 5.2, the two error-type agents combined with the
decision-point agents).

These are named by *error type* rather than by a single SQL clause,
because they capture cross-clause intent:

  * EvidenceAgent rewrites a query's arithmetic / predicate to match a
    formula stated in the question's evidence (e.g. "rate = A / B * 100").
  * QuestionEntityAgent proposes literal values and filters named in the
    question but absent from the query.

They are the "combined" part of the design: error-type reasoning on top of
the clause-grounded structural agents.
"""
from __future__ import annotations

import re
from typing import List

from .base import Agent, AgentContext
from ..types import Candidate


class EvidenceAgent(Agent):
    axis = "arithmetic"   # evidence usually rewrites the arithmetic/formula

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        cands: List[Candidate] = []
        ev = (ctx.evidence or "").strip()
        if not ev:
            return cands
        sql = self._clean(ctx.predicted_sql)

        # If the evidence states a "X = <formula>" and the formula uses
        # columns/operators not present in the prediction, propose the LLM
        # rewrite (the formula space is open-ended).
        if "=" in ev and ctx.use_llm and ctx.llm and ctx.llm.enabled:
            sqls = ctx.llm.propose(
                question=ctx.question, evidence=ctx.evidence,
                schema_summary=self._schema_summary(ctx.schema),
                predicted_sql=sql, axis="arithmetic (match evidence formula)")
            for s in sqls:
                s = self._clean(s)
                if s and s.lower() != sql.lower():
                    cands.append(Candidate(
                        sql=s, axis=self.axis, source="llm",
                        note="rewrite to match the formula in the evidence"))

        # Deterministic signal: evidence multiplies by 100 but the query does
        # not -> propose the *100 variant.
        if re.search(r"\*\s*100\b", ev) and not re.search(r"\*\s*100\b", sql):
            operand = r'("[^"]+"|`[^`]+`|\b[\w.]+\b)'
            m = re.search(operand + r'\s*/\s*' + operand, sql)
            if m:
                num, den = m.group(1).strip(), m.group(2).strip()
                alt = sql[:m.start()] + f"CAST({num} AS REAL) * 100 / {den}" + sql[m.end():]
                cands.append(Candidate(
                    sql=alt, axis=self.axis, source="enum",
                    note="multiply by 100 as the evidence formula requires"))
        return cands


class QuestionEntityAgent(Agent):
    axis = "predicate"   # entities named in the question become filters

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:
        cands: List[Candidate] = []
        if ctx.use_llm and ctx.llm and ctx.llm.enabled:
            sqls = ctx.llm.propose(
                question=ctx.question, evidence=ctx.evidence,
                schema_summary=self._schema_summary(ctx.schema),
                predicted_sql=self._clean(ctx.predicted_sql),
                axis="predicate (add a filter named in the question)")
            for s in sqls:
                s = self._clean(s)
                if s and s.lower() != self._clean(ctx.predicted_sql).lower():
                    cands.append(Candidate(
                        sql=s, axis=self.axis, source="llm",
                        note="add a filter for an entity named in the question"))
        return cands
