"""Shared data structures."""
from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class Candidate:
    """A candidate query produced along one decision point."""
    sql: str
    axis: str                  # which decision point / agent produced it
    note: str = ""             # human-readable description of the variant
    cols: Any = None           # execution result columns (filled by orchestrator)
    rows: Any = None           # execution result rows
    key: Any = None            # order-insensitive result signature


@dataclass
class Cluster:
    """A group of candidates sharing the same execution result."""
    key: Any
    members: List[Candidate]

    @property
    def representative(self) -> Candidate:
        return self.members[0]

    @property
    def n_rows(self) -> int:
        return self.key[0] if self.key != ("ERROR",) else -1


@dataclass
class Decision:
    """Output of the triage on one query."""
    action: str                      # ABSTAIN | AUTOFIX | ASK
    axis: str = ""
    clusters: List[Cluster] = field(default_factory=list)
    chosen: Optional[Candidate] = None   # for AUTOFIX: the selected candidate
    reason: str = ""


@dataclass
class Constraint:
    """A user-confirmed decision, carried across rounds and into regeneration."""
    axis: str
    description: str
    sql: str                         # the query embodying the user's choice
