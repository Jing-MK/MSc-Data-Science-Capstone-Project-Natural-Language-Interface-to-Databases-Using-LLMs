"""Qwen (DashScope) client, used in exactly two places (report 5.6):

  1. ``propose`` - propose candidate alternatives for the open-ended
     projection and predicate clauses (the ``llm_propose`` hook);
  2. ``phrase_question`` - phrase a clarification question in natural
     language once the framework has already decided what to ask.

The LLM never decides *whether* to involve the user; that decision rests
only on execution-result clustering.

The key is read from config (DASHSCOPE_API_KEY env var overrides the
file), so no secret lives in the repository. If no key is configured or
the ``openai`` package is missing, the client degrades gracefully: every
method returns an empty / deterministic result, and the framework runs as
the rule-based lower bound.
"""
from __future__ import annotations

import json
from typing import List, Optional

from ..config import LLMConfig


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._client = None
        self._enabled = False
        self._init()

    def _init(self) -> None:
        key = (self.cfg.api_key or "").strip()
        if not key or key.startswith("sk-REPLACE"):
            self._enabled = False
            return
        try:
            from openai import OpenAI
        except Exception:
            self._enabled = False
            return
        try:
            self._client = OpenAI(api_key=key, base_url=self.cfg.base_url,
                                  timeout=self.cfg.timeout_seconds)
            self._enabled = True
        except Exception:
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _chat(self, system: str, user: str) -> str:
        if not self._enabled:
            return ""
        try:
            extra = {}
            # DashScope accepts enable_thinking via extra_body.
            if self.cfg.enable_thinking is not None:
                extra = {"extra_body": {"enable_thinking": self.cfg.enable_thinking}}
            resp = self._client.chat.completions.create(
                model=self.cfg.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=self.cfg.temperature,
                **extra,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return ""

    # ---- (1) propose candidates for open-ended clauses -----------------
    def propose(self, question: str, evidence: str, schema_summary: str,
                predicted_sql: str, axis: str) -> List[str]:
        """Ask the model for alternative full SQL queries that differ from
        the prediction only along the given clause. Returns a list of SQL
        strings (possibly empty)."""
        if not self._enabled:
            return []
        system = (
            "You are a SQL assistant for the BIRD benchmark. Given a user "
            "question, external evidence, a database schema and a predicted "
            "SQLite query, you propose alternative queries that a user might "
            "have intended. Each alternative must differ from the prediction "
            f"ONLY in its {axis} clause. Return ONLY a JSON array of SQL "
            "strings, no prose."
        )
        user = (
            f"Question: {question}\n"
            f"Evidence: {evidence}\n"
            f"Schema:\n{schema_summary}\n"
            f"Predicted SQL: {predicted_sql}\n"
            f"Propose up to 3 alternative queries differing only in the "
            f"{axis}. JSON array only."
        )
        out = self._chat(system, user)
        return _parse_sql_array(out)

    # ---- (2) phrase a clarification question ---------------------------
    def phrase_question(self, question: str, axis: str,
                        option_summaries: List[str]) -> str:
        """Turn the decided axis + option tables into a friendly, SQL-free
        question for a non-expert user."""
        if not self._enabled:
            return ""
        system = (
            "You help a non-technical person choose between answers to their "
            "database question. Ask a short, plain-English question that does "
            "NOT mention SQL or column internals. One sentence."
        )
        opts = "\n".join(f"- {s}" for s in option_summaries)
        user = (
            f"The person asked: {question}\n"
            f"The answers differ in: {axis}\n"
            f"The options (as result previews):\n{opts}\n"
            f"Write one short question helping them pick."
        )
        return self._chat(system, user)


def _parse_sql_array(text: str) -> List[str]:
    if not text:
        return []
    text = text.strip()
    # Strip markdown fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        pass
    return []
