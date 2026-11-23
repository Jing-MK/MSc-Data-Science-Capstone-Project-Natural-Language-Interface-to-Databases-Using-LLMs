"""Human-in-the-loop interaction (report 5.5).

When the framework consults the user it presents the competing result
clusters as TABLES OF ANSWERS, not SQL. Each answer is recorded as a
constraint on the final query. The interaction repeats - resolving one
clause may remove the ambiguity in another - and stops when the candidates
collapse to a single result cluster or the round budget is reached. The
stopping condition is deterministic (cluster collapse), not a model
judging that the query is now correct.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from ..engine.orchestrator import Orchestrator
from ..types import (
    Action, Candidate, Constraint, Question, TriageOutcome,
)


# A UserAgent answers a question by returning the index of the chosen option.
UserAgent = Callable[[Question], int]


class InteractionResult:
    def __init__(self):
        self.final_sql: str = ""
        self.action_trace: List[str] = []
        self.questions_asked: int = 0
        self.constraints: List[Constraint] = []
        self.rounds: int = 0


class InteractionLoop:
    def __init__(self, orchestrator: Orchestrator, max_rounds: int = 4):
        self.orch = orchestrator
        self.max_rounds = max_rounds

    def run(self, baseline_sql: str,
            candidate_fn: Callable[[str, set], List[Candidate]],
            user: UserAgent,
            evidence_pick: Optional[str] = None,
            mode: str = "triage") -> InteractionResult:
        """Drive the triage/interaction loop.

        ``candidate_fn(current_sql, resolved_axes)`` re-enumerates candidates
        against the *current* query (so a resolved choice is carried forward)
        and omits axes already answered, so the same clause is never asked
        twice. The loop stops when the candidates collapse to a single result
        cluster (ABSTAIN) or the round budget is reached (report 5.5).
        """
        result = InteractionResult()
        current_sql = baseline_sql
        constraints: List[Constraint] = []
        resolved_axes: set = set()

        for _ in range(self.max_rounds):
            result.rounds += 1
            # Re-enumerate from the CURRENT query, skipping resolved axes.
            enumerated = candidate_fn(current_sql, resolved_axes)
            candidates = [Candidate(sql=current_sql, axis="baseline",
                                    source="baseline", note="current query")]
            candidates += [c for c in enumerated if c.axis not in resolved_axes]

            outcome = self.orch.triage(candidates, evidence_pick=evidence_pick,
                                       mode=mode)
            result.action_trace.append(outcome.action.value)

            if outcome.action == Action.ABSTAIN:
                if outcome.chosen_cluster:
                    current_sql = outcome.chosen_cluster.candidates[0].sql
                break

            if outcome.action == Action.AUTO_FIX:
                current_sql = outcome.chosen_cluster.candidates[0].sql
                # Record which axis was auto-resolved so we don't revisit it.
                for cand in outcome.chosen_cluster.candidates:
                    if cand.axis != "baseline":
                        resolved_axes.add(cand.axis)
                        break
                if outcome.terminal:
                    break      # a confident objective repair ends the loop
                continue       # otherwise re-probe for any remaining divergence

            # ASK
            q = outcome.question
            result.questions_asked += 1
            choice_idx = user(q)
            choice_idx = max(0, min(choice_idx, len(q.options) - 1))
            chosen = q.options[choice_idx]
            prev_sql = current_sql
            current_sql = chosen.sql
            constraints.append(Constraint(
                axis=outcome.axis or q.axis,
                description=q.prompt, chosen_sql=chosen.sql))
            resolved_axes.add(outcome.axis or q.axis)
            # If the user confirmed the current answer (no change), the clause
            # held no genuine alternative for them; stop re-asking it.
            if chosen.sql.strip() == prev_sql.strip():
                break
            # Loop: resolving this may collapse remaining clusters.

        result.final_sql = current_sql
        result.constraints = constraints
        return result
