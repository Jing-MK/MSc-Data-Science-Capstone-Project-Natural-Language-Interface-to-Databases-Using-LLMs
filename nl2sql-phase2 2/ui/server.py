"""Optional live-mode demo server.

Runs the REAL framework on demand against the configured databases, with
the LLM enabled if a key is present. Lets you show, live, that the demo is
not a recording - the same traces are produced by actually executing
queries and (optionally) calling the model.

Start:
    pip install flask flask-cors
    python ui/server.py            # serves http://127.0.0.1:5000

The page (index.html) uses the pre-computed demo_data.js by default; the
live endpoint is here so you can switch to it in front of the examiner.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from nl2sql.config import load_config
from nl2sql.engine.execution import Executor, result_key
from nl2sql.engine.orchestrator import Orchestrator
from nl2sql.engine.schema import SchemaReader
from nl2sql.agents.base import AgentContext
from nl2sql.system import default_agents
from nl2sql.types import Candidate

app = Flask(__name__, static_folder=".")
CORS(app)
CFG = load_config()


def _table(res):
    return {"ok": res.ok, "columns": res.columns,
            "rows": [[str(c) for c in r] for r in res.rows[:8]],
            "row_count": res.row_count, "error": res.error}


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.route("/api/correct", methods=["POST"])
def correct():
    """Run the real pipeline on one case and return the full trace."""
    data = request.get_json(force=True)
    db_id = data["db_id"]
    ex = Executor(CFG.db_path(db_id), CFG.framework.busy_timeout_ms)
    reader = SchemaReader(CFG.db_path(db_id))
    schema = reader.read(db_id)
    orch = Orchestrator(ex)

    gold_key = result_key(ex.run(data["gold_sql"])) if data.get("gold_sql") else None
    ctx = AgentContext(question=data["question"], evidence=data.get("evidence", ""),
                       predicted_sql=data["pred_sql"], schema=schema, reader=reader,
                       llm=CorrectionLLM(), use_llm=CFG.framework.use_llm_propose)

    cands = [Candidate(sql=data["pred_sql"], axis="baseline", source="baseline",
                       note="the baseline prediction")]
    for agent in default_agents():
        try:
            cands.extend(agent.enumerate(ctx))
        except Exception:
            continue

    outcome = orch.triage(cands)
    return jsonify({
        "action": outcome.action.value,
        "reason": outcome.reason,
        "pred_table": _table(ex.run(data["pred_sql"])),
        "candidates": [{"axis": c.axis, "note": c.note, "objective": c.objective,
                        "table": _table(ex.run(c.sql))} for c in cands],
        "llm_enabled": CFG.framework.use_llm_propose,
    })


def CorrectionLLM():
    from nl2sql.llm.client import LLMClient
    return LLMClient(CFG.llm)


if __name__ == "__main__":
    print("LLM enabled:", CorrectionLLM().enabled)
    print("DB root:", CFG.bird.db_root)
    app.run(host="127.0.0.1", port=5000, debug=False)
