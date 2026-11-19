"""Evaluation metrics for correction: N_fix / N_break / N_net + human effort.

Definitions (following SQLENS for N_fix/N_break and Sphinteract for effort):
  N_fix    : queries wrong before correction, correct after
  N_break  : queries correct before correction, wrong after   (the corruption cost)
  N_net    : N_fix - N_break
  questions: total user questions asked (0 for fully automatic arms)
  EX_before / EX_after : execution accuracy over the evaluated set
"""
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    n_total: int = 0
    correct_before: int = 0
    correct_after: int = 0
    n_fix: int = 0
    n_break: int = 0
    questions: int = 0
    per_case: list = field(default_factory=list)

    @property
    def n_net(self): return self.n_fix - self.n_break
    @property
    def ex_before(self): return self.correct_before / self.n_total if self.n_total else 0
    @property
    def ex_after(self): return self.correct_after / self.n_total if self.n_total else 0
    @property
    def q_per_case(self): return self.questions / self.n_total if self.n_total else 0

    def report(self, name):
        print(f"\n{name}")
        print(f"  EX: {100*self.ex_before:.1f}% -> {100*self.ex_after:.1f}%  "
              f"(+{100*(self.ex_after-self.ex_before):.1f})")
        print(f"  N_fix={self.n_fix}  N_break={self.n_break}  N_net={self.n_net:+d}")
        print(f"  questions asked: {self.questions}  ({self.q_per_case:.2f} per query)")
