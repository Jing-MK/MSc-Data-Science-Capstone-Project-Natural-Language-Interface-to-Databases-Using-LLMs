"""Assemble the full multi-agent + HITL correction system."""
from engine.execution import connect
from engine.context import Context
from hitl.interaction import correct

from agents.projection import ProjectionAgent
from agents.predicate import PredicateAgent
from agents.join import JoinAgent
from agents.simple_clauses import DistinctAgent, AggregateAgent, OrderAgent
from agents.arithmetic import ArithmeticAgent
from agents.evidence import EvidenceAgent
from agents.question_entity import QuestionEntityAgent
from agents.percentage import PercentageAgent
from agents.groupby import GroupByAgent
from agents.rank import RankAgent
from agents.empty_result import EmptyResultAgent


def default_agents():
    """One agent per SQL decision point + semantic agents.

    Original agents (D1-D8):
    - ProjectionAgent (D2): Column selection
    - PredicateAgent (D6): WHERE conditions
    - JoinAgent (D1): Table joins
    - DistinctAgent (D3): DISTINCT keyword
    - AggregateAgent (D4): Aggregation functions
    - OrderAgent (D7): ORDER BY, LIMIT
    - ArithmeticAgent (D8): Arithmetic expressions

    Semantic agents:
    - EvidenceAgent: Check if SQL implements evidence hints (formulas, columns, conditions)
    - QuestionEntityAgent: Check if WHERE values match question entities

    Targeted fix agents (based on BIRD error analysis):
    - PercentageAgent: Fix * 100 / * 100.0 issues
    - GroupByAgent: Remove unnecessary GROUP BY clauses
    - RankAgent: Add RANK() window function when question mentions "rank"
    - EmptyResultAgent: Fix queries that return 0 rows (JOIN issues, case mismatch, etc.)
    """
    return [
        # Execution-grounded agents first (highest priority - use actual results)
        EmptyResultAgent(),      # Fix empty results (JOIN, WHERE issues)

        # Semantic agents (use question/evidence context)
        EvidenceAgent(),         # Check evidence alignment & precomputed columns
        QuestionEntityAgent(),   # Check question entity matching

        # Targeted fix agents (specific error patterns)
        PercentageAgent(),       # Fix * 100 issues
        GroupByAgent(),          # Remove unnecessary GROUP BY
        RankAgent(),             # Add RANK() for ranking questions

        # Original structural agents
        ProjectionAgent(),       # D2
        PredicateAgent(),        # D6
        JoinAgent(),             # D1
        DistinctAgent(),         # D3
        AggregateAgent(),        # D4
        OrderAgent(),            # D7
        ArithmeticAgent(),       # D8
    ]


class CorrectionSystem:
    def __init__(self, db_path, llm_propose=None):
        self.conn = connect(db_path)
        self.agents = default_agents()
        self.llm_propose = llm_propose

    def run(self, question, predicted_sql, evidence="", user=None,
            max_rounds=4, log=None):
        ctx = Context(self.conn, llm_propose=self.llm_propose, evidence=evidence, question=question)
        return correct(self.conn, predicted_sql, self.agents, ctx,
                       user=user, max_rounds=max_rounds, log=log)
