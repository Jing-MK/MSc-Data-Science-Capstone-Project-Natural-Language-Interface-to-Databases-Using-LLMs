"""Agent base class.

Each agent owns one decision point and exposes a single capability:
``enumerate`` - propose candidate queries that differ from the prediction
only along that agent's clause. No agent has a ``diagnose`` step: an agent
never needs to know that its clause is wrong, only what else it could be
(report 5.2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from ..engine.schema import Schema, SchemaReader
from ..llm.client import LLMClient
from ..types import Candidate


@dataclass
class AgentContext:
    question: str
    evidence: str
    predicted_sql: str
    schema: Schema
    reader: SchemaReader
    llm: Optional[LLMClient] = None
    use_llm: bool = True


class Agent:
    #: decision point name, e.g. "projection"
    axis: str = "base"

    def enumerate(self, ctx: AgentContext) -> List[Candidate]:  # pragma: no cover
        raise NotImplementedError

    # ---- shared helpers -------------------------------------------------
    @staticmethod
    def _clean(sql: str) -> str:
        return sql.split("----- bird -----")[0].strip().rstrip(";")

    @staticmethod
    def _schema_summary(schema: Schema, max_cols: int = 60) -> str:
        lines = []
        for t in schema.tables:
            cols = ", ".join(c.name for c in schema.columns.get(t, [])[:max_cols])
            lines.append(f"{t}({cols})")
        return "\n".join(lines)

    def _llm_candidates(self, ctx: AgentContext) -> List[Candidate]:
        """Open-ended clauses may be assisted by the LLM (report 5.2/5.6)."""
        if not (ctx.use_llm and ctx.llm and ctx.llm.enabled):
            return []
        sqls = ctx.llm.propose(
            question=ctx.question, evidence=ctx.evidence,
            schema_summary=self._schema_summary(ctx.schema),
            predicted_sql=self._clean(ctx.predicted_sql), axis=self.axis,
        )
        out = []
        for s in sqls:
            s = self._clean(s)
            if s and s.lower() != self._clean(ctx.predicted_sql).lower():
                out.append(Candidate(sql=s, axis=self.axis, source="llm",
                                     note=f"LLM-proposed {self.axis} alternative"))
        return out
