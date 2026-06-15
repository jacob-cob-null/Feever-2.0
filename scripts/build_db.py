"""Build hospital_db.sqlite from Benchmark_raw.sql dump."""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL_PATH = ROOT / "models" / "reserved" / "database" / "Benchmark_raw.sql"
DB_PATH = ROOT / "models" / "reserved" / "hospital_db.sqlite"

CREATE_TABLE = """
CREATE TABLE medical_services (
    service_ID     INTEGER PRIMARY KEY,
    service_Name   TEXT NOT NULL,
    service_Origin TEXT NOT NULL,
    service_Price  DOUBLE PRECISION NOT NULL
);
"""


def main():
    if not SQL_PATH.exists():
        print(f"ERROR: SQL dump not found at {SQL_PATH}")
        sys.exit(1)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH.name}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(CREATE_TABLE)

    inserted = 0
    skipped = 0
    with open(SQL_PATH, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line.startswith("INSERT"):
                continue
            try:
                conn.execute(line)
                inserted += 1
            except sqlite3.Error:
                skipped += 1

    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM medical_services").fetchone()[0]
    hospitals = conn.execute(
        "SELECT DISTINCT service_Origin FROM medical_services ORDER BY service_Origin"
    ).fetchall()
    conn.close()

    print(f"Created {DB_PATH.name}")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped:  {skipped}")
    print(f"  Total:    {count}")
    print(f"  Hospitals: {len(hospitals)}")
    for (h,) in hospitals:
        print(f"    - {h}")


if __name__ == "__main__":
    main()
