"""Build a small SQLite database mirroring the real BIRD `california_schools`
schema (same table and columns), seeded so that REAL BIRD dev questions
reproduce their real prediction/gold behaviour. The questions and SQL used
in the demo are the REAL ones from dev.json (searchable by question_id);
only the database is a small stand-in so the demo runs without the full
BIRD download. The full evaluation uses the real BIRD dev databases.

Demo cases (all on the `schools` table):

  * QID 86 (AUTO-FIX) - "administrator's last name for the school with
    Charter number 40". pred filters CharterNum = '40' (0 rows); gold filters
    '0040' (the zero-padded code actually stored). The predicate agent
    enumerates '0040' from the column's stored domain -> empty-vs-non-empty
    objective signal -> auto-fixed, no user needed.

  * QID 63 (ASK) - "administrators of chartered schools with charter number
    00D2". pred projects eight columns (all admin name slots); gold projects
    four (AdmFName1, AdmLName1, School, City). Both non-empty but different
    -> intent-dependent -> the user picks the intended result table.

  * ABSTAIN - a correct query (schools in a county) where every candidate
    agrees -> left untouched, never corrupting a correct query.
"""
from __future__ import annotations

import os
import sqlite3
import sys


def build(db_dir: str) -> str:
    os.makedirs(os.path.join(db_dir, "california_schools"), exist_ok=True)
    path = os.path.join(db_dir, "california_schools", "california_schools.sqlite")
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Real BIRD `schools` columns used by these questions.
    c.execute("""
        CREATE TABLE schools (
            CDSCode TEXT PRIMARY KEY,
            County  TEXT,
            District TEXT,
            School  TEXT,
            City    TEXT,
            Charter INTEGER,
            CharterNum TEXT,
            StatusType TEXT,
            AdmFName1 TEXT, AdmLName1 TEXT,
            AdmFName2 TEXT, AdmLName2 TEXT,
            AdmFName3 TEXT, AdmLName3 TEXT
        )
    """)

    rows = [
        # QID 86: the school with charter number stored as '0040' (zero-padded).
        # pred's CharterNum='40' matches nothing; gold's '0040' matches this row.
        ("01-100", "Alameda", "Oakland Unified", "Oakland Tech", "Oakland",
         1, "0040", "Active", "Maria", "Santos", None, None, None, None),
        # QID 63: chartered schools with charter number '00D2'. Two rows.
        ("01-200", "Alameda", "Berkeley Unified", "Berkeley Charter", "Berkeley",
         1, "00D2", "Active", "John", "Lee", "Amy", "Ng", None, None),
        ("01-201", "Alameda", "Berkeley Unified", "Bay Charter", "Berkeley",
         1, "00D2", "Active", "Carlos", "Diaz", None, None, None, None),
        # filler rows (different county / charter) for the ABSTAIN query.
        ("02-300", "Fresno", "Fresno Unified", "Fresno High", "Fresno",
         0, "", "Active", "Dana", "Park", None, None, None, None),
        ("02-301", "Fresno", "Fresno Unified", "Edison High", "Fresno",
         0, "", "Closed", "Sam", "Cole", None, None, None, None),
    ]
    c.executemany(
        "INSERT INTO schools VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/dev_databases"
    p = build(out)
    print("built demo DB at:", p)
