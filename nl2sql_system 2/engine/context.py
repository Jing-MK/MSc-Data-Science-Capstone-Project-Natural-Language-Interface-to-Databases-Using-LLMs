"""Per-query context handed to agents: schema access + optional LLM proposer."""
from engine import schema


class Context:
    def __init__(self, conn, llm_propose=None, evidence="", question=""):
        self.conn = conn
        self.evidence = evidence
        self.question = question                 # the natural language question
        self.llm_propose = llm_propose          # optional: (sql, axis) -> [(sql, note)]
        self.columns = schema.all_columns(conn) # col_lower -> [(table, actual)]
        self._dom_cache = {}

    def domain(self, table, column):
        k = (table, column)
        if k not in self._dom_cache:
            self._dom_cache[k] = schema.column_domain(self.conn, table, column)
        return self._dom_cache[k]

    def foreign_keys(self, table):
        return schema.get_foreign_keys(self.conn, table)
