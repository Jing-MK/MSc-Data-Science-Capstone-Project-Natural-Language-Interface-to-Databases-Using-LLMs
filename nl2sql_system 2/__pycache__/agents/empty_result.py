"""EmptyResultAgent: Detects empty query results and proposes fixes.

Common error: SQL returns 0 rows when it should return data.
Possible causes:
1. Wrong WHERE condition value (case mismatch, wrong column)
2. JOIN that filters out all rows
3. Overly restrictive conditions

This agent uses execution-grounded feedback: if query returns empty but schema
suggests data exists, propose alternatives.
"""
import re
from agents.base import Agent
from engine.types import Candidate
from engine.execution import execute


class EmptyResultAgent(Agent):
    axis = "empty_result"

    def enumerate(self, sql, ctx):
        """Generate candidates to fix empty result sets."""
        out = []

        # Execute the SQL to check if it returns empty results
        try:
            cols, rows = execute(ctx.conn, sql)
            if rows:  # Not empty, no problem
                return out
        except:
            return out  # Can't execute, skip

        # SQL returned 0 rows - this might be an error
        # Strategy 1: Try removing JOIN clauses one by one
        # (JOIN might be filtering out all rows)
        join_pattern = r'\s+(?:INNER\s+)?JOIN\s+\w+(?:\s+AS\s+\w+)?\s+ON\s+[^\s]+\s*=\s*[^\s]+'

        joins = list(re.finditer(join_pattern, sql, re.I))
        if joins:
            # Try removing each JOIN
            for i, join_match in enumerate(joins):
                new_sql = sql[:join_match.start()] + sql[join_match.end():]

                # Also need to fix table aliases in SELECT/WHERE if we removed a JOIN
                # For simplicity, just propose it and let execution verify
                try:
                    test_cols, test_rows = execute(ctx.conn, new_sql)
                    if test_rows:  # Removing this JOIN gives results!
                        out.append(Candidate(
                            new_sql, self.axis,
                            f"remove JOIN #{i+1} (caused empty result)"
                        ))
                except:
                    pass  # This removal doesn't work, skip

        # Strategy 2: Try removing WHERE conditions one by one
        where_match = re.search(r'\bWHERE\s+(.*?)(?:\s+(?:GROUP|ORDER|LIMIT|$))', sql, re.I | re.S)
        if where_match:
            where_clause = where_match.group(1).strip()

            # Split by AND
            conditions = re.split(r'\s+AND\s+', where_clause, flags=re.I)

            if len(conditions) > 1:
                # Try removing each condition
                for i, cond in enumerate(conditions):
                    # Reconstruct WHERE without this condition
                    new_conditions = [c for j, c in enumerate(conditions) if j != i]
                    new_where = ' AND '.join(new_conditions)

                    new_sql = sql.replace(
                        f"WHERE {where_clause}",
                        f"WHERE {new_where}"
                    )

                    try:
                        test_cols, test_rows = execute(ctx.conn, new_sql)
                        if test_rows:  # Removing this condition gives results!
                            out.append(Candidate(
                                new_sql, self.axis,
                                f"remove condition '{cond.strip()[:50]}...' (caused empty result)"
                            ))
                    except:
                        pass

        # Strategy 3: Check for case mismatch in string literals
        # Find all string literals in WHERE clause
        if where_match:
            where_clause = where_match.group(1)

            # Find quoted strings
            for match in re.finditer(r"['\"]([^'\"]+)['\"]", where_clause):
                literal = match.group(1)

                # Try different case variations
                variations = [
                    literal.lower(),
                    literal.upper(),
                    literal.title(),
                    literal.capitalize()
                ]

                for var in variations:
                    if var != literal:
                        new_sql = sql.replace(f"'{literal}'", f"'{var}'")
                        new_sql = new_sql.replace(f'"{literal}"', f'"{var}"')

                        try:
                            test_cols, test_rows = execute(ctx.conn, new_sql)
                            if test_rows:
                                out.append(Candidate(
                                    new_sql, self.axis,
                                    f"fix case: '{literal}' -> '{var}'"
                                ))
                        except:
                            pass

        return out
