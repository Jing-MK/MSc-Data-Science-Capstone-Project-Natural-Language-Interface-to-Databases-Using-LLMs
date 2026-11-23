"""CorrectionSystem - the top-level framework (report Chapter 5).

Wires the decision-point and semantic agents, the execution-based
orchestrator, and the human-in-the-loop interaction loop into one object
that takes a (question, evidence, predicted SQL, db_id) and returns a
possibly-revised query plus any questions it needed to ask.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from .agents.base import Agent, AgentContext
from .agents.arithmetic import ArithmeticAgent
from .agents.join import JoinAgent
from .agents.predicate import PredicateAgent
from .agents.projection import ProjectionAgent
from .agents.semantic import EvidenceAgent, QuestionEntityAgent
from .agents.simple_clauses import (
    AggregateAgent, DistinctAgent, GroupByAgent, OrderAgent,
)
from .config import Config
from .engine.execution import Executor
from .engine.orchestrator import Orchestrator
from .engine.schema import SchemaReader
from .hitl.interaction import InteractionLoop, InteractionResult, UserAgent
from .llm.client import LLMClient
from .types import Candidate, Constraint


def default_agents() -> List[Agent]:
    """The decision-point agents plus the two semantic agents (report 5.2)."""
    return [
        ProjectionAgent(),        # D2
        PredicateAgent(),         # D6
        JoinAgent(),              # D1
        DistinctAgent(),          # D3
        AggregateAgent(),         # D4
        GroupByAgent(),           # D5
        OrderAgent(),             # D7
        ArithmeticAgent(),        # D8
        EvidenceAgent(),          # semantic (error-type)
        QuestionEntityAgent(),    # semantic (error-type)
    ]


class CorrectionSystem:
    def __init__(self, config: Config, agents: Optional[List[Agent]] = None):
        self.config = config
        self.agents = agents or default_agents()
        self.llm = LLMClient(config.llm)

    def correct(self, db_id: str, question: str, evidence: str,
                predicted_sql: str, user: UserAgent,
                evidence_pick: Optional[str] = None,
                mode: str = "triage") -> InteractionResult:
        db_path = self.config.db_path(db_id)
        executor = Executor(db_path, self.config.framework.busy_timeout_ms)
        reader = SchemaReader(db_path)
        schema = reader.read(db_id)
        orch = Orchestrator(executor)

        def candidate_fn(current_sql: str, resolved_axes: set) -> List[Candidate]:
            # Re-enumerate against the CURRENT query each round, so a resolved
            # choice is carried forward and refines the remaining candidates.
            ctx = AgentContext(
                question=question, evidence=evidence, predicted_sql=current_sql,
                schema=schema, reader=reader, llm=self.llm,
                use_llm=self.config.framework.use_llm_propose,
            )
            out: List[Candidate] = []
            for agent in self.agents:
                if agent.axis in resolved_axes:
                    continue
                try:
                    out.extend(agent.enumerate(ctx))
                except Exception:
                    # An agent that fails to enumerate simply contributes
                    # nothing; it never breaks the run.
                    continue
            return out

        loop = InteractionLoop(orch, max_rounds=self.config.framework.max_rounds)
        return loop.run(
            baseline_sql=predicted_sql, candidate_fn=candidate_fn,
            user=user, evidence_pick=evidence_pick, mode=mode,
        )
