"""Core data types shared across the framework.

These mirror the objects described in Chapter 5 of the report:
candidate queries, result clusters, the triage decision, and the
constraints that record a user's answers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Tuple


# A result is a multiset of rows; we key it order-insensitively so that
# two queries returning the same rows in a different order are equal
# (report Section 3.2).
ResultKey = str


class Action(str, Enum):
    ABSTAIN = "abstain"      # one cluster: no genuine alternative -> leave untouched
    AUTO_FIX = "auto_fix"    # objective signal singles out one cluster -> repair
    ASK = "ask"              # intent-dependent divergence -> consult the user


@dataclass
class Candidate:
    """A candidate query produced by an agent along one decision point."""
    sql: str
    axis: str                 # which decision point produced it (e.g. "projection")
    source: str = "enum"      # "baseline" | "enum" | "llm"
    note: str = ""            # human-readable description of the alternative
    objective: bool = False   # carries a gold-free signal that both detects
                              # AND fixes the error (report 4.5), e.g. a CAST
                              # that repairs truncated integer division, or an
                              # empty-result predicate rewrite. The triage may
                              # auto-fix to such a candidate.


@dataclass
class ExecResult:
    """The outcome of executing a candidate against the database."""
    ok: bool
    rows: List[Tuple[Any, ...]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    error: str = ""

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def is_empty(self) -> bool:
        return self.ok and len(self.rows) == 0


@dataclass
class Cluster:
    """A group of candidates that produced the same execution result."""
    key: ResultKey
    result: ExecResult
    candidates: List[Candidate] = field(default_factory=list)

    @property
    def is_nonempty(self) -> bool:
        return self.result.ok and self.result.row_count > 0


@dataclass
class Constraint:
    """A decision recorded from a user's answer (report Section 5.5)."""
    axis: str
    description: str
    chosen_sql: str


@dataclass
class Question:
    """A clarification question presented to the user as answer tables."""
    axis: str
    prompt: str                         # natural-language question
    options: List["QuestionOption"] = field(default_factory=list)


@dataclass
class QuestionOption:
    """One option the user can pick, shown as a result table (not SQL)."""
    label: str
    columns: List[str]
    rows: List[Tuple[Any, ...]]
    sql: str                            # kept internally, NOT shown to the user
    preview_rows: int = 5


@dataclass
class TriageOutcome:
    action: Action
    reason: str
    clusters: List[Cluster] = field(default_factory=list)
    chosen_cluster: Optional[Cluster] = None
    question: Optional[Question] = None
    axis: Optional[str] = None
    terminal: bool = False   # if True, the loop stops after applying this
                             # outcome (a confident objective repair)
