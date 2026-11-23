"""Evaluation metrics (report 6.1).

  N_fix   : queries wrong before correction and correct after.
  N_break : queries correct before and wrong after.
  N_net   : N_fix - N_break.
  questions / query : total questions asked, divided by the evaluated set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalResult:
    arm: str
    n_cases: int = 0
    n_fix: int = 0
    n_break: int = 0
    questions: int = 0
    per_case: List[dict] = field(default_factory=list)

    @property
    def n_net(self) -> int:
        return self.n_fix - self.n_break

    @property
    def questions_per_query(self) -> float:
        return self.questions / self.n_cases if self.n_cases else 0.0

    def row(self) -> dict:
        return {
            "arm": self.arm,
            "N_fix": self.n_fix,
            "N_break": self.n_break,
            "N_net": self.n_net,
            "questions": self.questions,
            "Q_per_query": round(self.questions_per_query, 2),
        }
