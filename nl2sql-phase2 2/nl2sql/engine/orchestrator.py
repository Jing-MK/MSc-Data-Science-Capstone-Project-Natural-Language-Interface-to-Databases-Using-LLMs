"""The triage core (report Sections 5.3-5.4).

Given candidate queries for a prediction, the orchestrator:
  1. executes all candidates and clusters them by execution result;
  2. applies the three-way triage (ABSTAIN / AUTO_FIX / ASK);
  3. when asking, chooses which decision point to ask about first by
     expected information gain over the result clusters.

Nothing here diagnoses *why* a query is wrong. The decision to involve the
user rests only on observed execution behaviour, never on a model judging
its own output.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional

from ..types import (
    Action, Candidate, Cluster, ExecResult, Question, QuestionOption,
    TriageOutcome,
)
from .execution import Executor, result_key


class Orchestrator:
    def __init__(self, executor: Executor):
        self.executor = executor
        self._cache: Dict[str, ExecResult] = {}

    # ---- execution + caching -------------------------------------------
    def _execute(self, sql: str) -> ExecResult:
        if sql not in self._cache:
            self._cache[sql] = self.executor.run(sql)
        return self._cache[sql]

    # ---- clustering (report 5.3) ---------------------------------------
    def cluster(self, candidates: List[Candidate]) -> List[Cluster]:
        buckets: Dict[str, Cluster] = {}
        for cand in candidates:
            res = self._execute(cand.sql)
            key = result_key(res)
            if key not in buckets:
                buckets[key] = Cluster(key=key, result=res, candidates=[])
            buckets[key].candidates.append(cand)
        return list(buckets.values())

    @staticmethod
    def _answer_clusters(clusters: List[Cluster]) -> List[Cluster]:
        """Clusters that represent a usable answer (successful execution)."""
        return [c for c in clusters if c.result.ok]

    @staticmethod
    def _pick_default(answer_clusters: List[Cluster]) -> Cluster:
        """A deterministic default choice for the fix-always arm: prefer a
        non-empty, non-baseline cluster; fall back to the largest cluster."""
        non_baseline = [c for c in answer_clusters
                        if not any(cand.axis == "baseline" for cand in c.candidates)
                        and c.result.row_count > 0]
        pool = non_baseline or answer_clusters
        return max(pool, key=lambda c: (c.result.row_count, len(c.candidates)))

    # ---- triage policy (report 5.4) ------------------------------------
    def triage(self, candidates: List[Candidate],
               evidence_pick: Optional[str] = None,
               mode: str = "triage") -> TriageOutcome:
        """mode selects the evaluation arm's policy (report 6.2):
          - "triage"     : the full three-way policy (default);
          - "fix_always" : auto-select on any divergence, never ask;
          - "ask_always" : ask on any divergence, no objective auto-fix.
        """
        clusters = self.cluster(candidates)
        answer_clusters = self._answer_clusters(clusters)

        # Case 1: a single answer cluster -> no genuine alternative -> ABSTAIN.
        if len(answer_clusters) <= 1:
            chosen = answer_clusters[0] if answer_clusters else None
            return TriageOutcome(
                action=Action.ABSTAIN,
                reason="All candidates agree on the result; nothing to change.",
                clusters=clusters, chosen_cluster=chosen,
            )

        # fix_always: never ask; auto-select a cluster on any divergence.
        if mode == "fix_always":
            signal = self._objective_signal(answer_clusters, evidence_pick)
            cluster = signal[0] if signal else self._pick_default(answer_clusters)
            return TriageOutcome(
                action=Action.AUTO_FIX,
                reason="fix-always: auto-selected a cluster without asking.",
                clusters=clusters, chosen_cluster=cluster,
            )

        # ask_always: always ask on divergence (no objective auto-fix).
        if mode == "ask_always":
            axis = self._choose_axis_by_infogain(answer_clusters)
            question = self._build_question(axis, answer_clusters)
            return TriageOutcome(
                action=Action.ASK,
                reason="ask-always: user consulted on every divergence.",
                clusters=clusters, question=question, axis=axis,
            )

        # Case 2: an objective signal singles out one cluster -> AUTO_FIX.
        # An objective signal both detects and fixes the error, so the repair
        # is confident and terminal (report 4.5): we do not then re-open the
        # query to low-value probing on other clauses.
        signal = self._objective_signal(answer_clusters, evidence_pick)
        if signal is not None:
            cluster, why = signal
            out = TriageOutcome(
                action=Action.AUTO_FIX,
                reason=why, clusters=clusters, chosen_cluster=cluster,
            )
            out.terminal = True
            return out

        # Case 3: genuine, intent-dependent divergence -> ASK.
        # The user is shown ALL competing result tables side by side
        # (report 5.5). The info-gain axis only labels which clause the
        # question is primarily about.
        axis = self._choose_axis_by_infogain(answer_clusters)
        question = self._build_question(axis, answer_clusters)
        return TriageOutcome(
            action=Action.ASK,
            reason="Divergence is intent-dependent; the user must decide.",
            clusters=clusters, question=question, axis=axis,
        )

    def _objective_signal(self, answer_clusters: List[Cluster],
                          evidence_pick: Optional[str]):
        """Return (cluster, reason) if a gold-free signal decides, else None.

        An objective signal both detects and fixes the error, so the repair
        is safe without consulting the user (report 4.5).
        """
        # Signal A: exactly one cluster returns a non-empty result -> the
        # empty ones failed to match any value and are wrong.
        nonempty = [c for c in answer_clusters if c.result.row_count > 0]
        if len(nonempty) == 1 and len(answer_clusters) > 1:
            return nonempty[0], ("Only one candidate returns a non-empty "
                                 "result; the empty ones are wrong.")

        # Signal B: a candidate carries an objective repair (e.g. a CAST that
        # fixes truncated integer division) and it changes the result away
        # from a degenerate baseline. Auto-fix to that cluster.
        baseline_cluster = next(
            (c for c in answer_clusters
             if any(cand.axis == "baseline" for cand in c.candidates)), None)
        for c in answer_clusters:
            if c is baseline_cluster:
                continue
            if any(cand.objective for cand in c.candidates):
                return c, ("A deterministic repair (e.g. a cast fixing "
                           "truncated integer division) changes the result.")

        # Signal C: an evidence formula selects a specific candidate SQL.
        if evidence_pick is not None:
            for c in answer_clusters:
                if any(cand.sql.strip() == evidence_pick.strip()
                       for cand in c.candidates):
                    return c, ("The formula stated in the question's evidence "
                               "selects this candidate.")
        return None

    # ---- information gain (report 5.4) ---------------------------------
    def _choose_axis_by_infogain(self, answer_clusters: List[Cluster]) -> str:
        """Pick the decision point whose answer most reduces the number of
        surviving result clusters: the axis that splits candidates into the
        largest number of distinct result clusters.

        The synthetic "baseline" axis is never chosen - it is the current
        query, not a clause the user can decide about.
        """
        axis_to_keys: Dict[str, set] = defaultdict(set)
        for cluster in answer_clusters:
            for cand in cluster.candidates:
                if cand.axis == "baseline":
                    continue
                axis_to_keys[cand.axis].add(cluster.key)
        if not axis_to_keys:
            return "projection"
        # Most distinct diverging clusters first; tie-break by name for determinism.
        return max(sorted(axis_to_keys), key=lambda a: len(axis_to_keys[a]))

    @staticmethod
    def _entropy(counts: List[int]) -> float:
        total = sum(counts)
        if total == 0:
            return 0.0
        h = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                h -= p * math.log2(p)
        return h

    # ---- build the user-facing question (report 5.5) -------------------
    def _build_question(self, axis: str,
                        answer_clusters: List[Cluster]) -> Question:
        """Present competing clusters as answer TABLES, never as SQL.

        The user decides about the data, not the clause, so the prompt is
        answer-focused. The ``axis`` is still carried for logging and for an
        LLM to phrase a richer question when enabled.
        """
        # De-duplicate by result, and order so the most meaningful options
        # come first: the baseline answer, then LLM-proposed clusters, then
        # the rest. Cap the number shown so the user is not flooded.
        MAX_OPTIONS = 4

        def priority(cluster: Cluster) -> int:
            srcs = {c.source for c in cluster.candidates}
            if "baseline" in srcs:
                return 0
            if "llm" in srcs:
                return 1
            return 2

        seen: set = set()
        ordered: List[Cluster] = []
        for cluster in sorted(answer_clusters, key=priority):
            if cluster.key in seen:
                continue
            seen.add(cluster.key)
            ordered.append(cluster)

        options: List[QuestionOption] = []
        for cluster in ordered[:MAX_OPTIONS]:
            rep = cluster.candidates[0]
            label = f"Option {chr(ord('A') + len(options))}"
            options.append(QuestionOption(
                label=label,
                columns=cluster.result.columns,
                rows=cluster.result.rows[:5],
                sql=rep.sql,     # internal only; the UI shows the table
            ))
        prompt = "Which of these answers did you intend?"
        return Question(axis=axis, prompt=prompt, options=options)


def _phrase_question_fallback(axis: str) -> str:
    """Deterministic question text used when no LLM is available."""
    table = {
        "projection": "Which set of columns did you want in the answer?",
        "predicate": "Which filter did you intend?",
        "distinct": "Should duplicate rows be removed?",
        "aggregate": "How should the values be aggregated?",
        "group_by": "At what grouping should the data be summarised?",
        "order": "How should the results be ordered?",
        "join": "Which tables did you mean to combine?",
        "arithmetic": "How should the quantity be computed?",
    }
    return table.get(axis, "Which of these answers did you intend?")
