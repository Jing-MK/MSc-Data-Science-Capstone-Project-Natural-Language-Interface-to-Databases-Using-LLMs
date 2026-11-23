"""The four evaluation arms (report 6.2).

All arms draw candidates from the same decision-point agents, so the
comparison isolates the effect of the triage policy rather than the
candidate pool:

  * no_correction : the baseline prediction, unchanged (lower bound).
  * fix_always    : whenever candidates diverge, auto-select one, never ask.
  * ask_always    : consult the user on every divergence, no auto-triage.
  * triage        : automatic repair where an objective signal decides,
                    user consultation otherwise, abstention where no
                    candidate changes the result.
"""
from __future__ import annotations

from enum import Enum


class Arm(str, Enum):
    NO_CORRECTION = "no_correction"
    FIX_ALWAYS = "fix_always"
    ASK_ALWAYS = "ask_always"
    TRIAGE = "triage"
