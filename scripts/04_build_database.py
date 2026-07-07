"""
04_build_database.py
--------------------
Loads the processed CSVs into a local SQLite database so the queries in
sql/analysis_queries.sql can be run exactly as written.

Output:  data/mk_analysis.db  (gitignored — rebuild any time with this script)

Run:   python scripts/04_build_database.py
Then:  sqlite3 data/mk_analysis.db
       .read sql/analysis_queries.sql
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE = Path("data/mk_analysis.db")
PROCESSED = Path("data/processed")

# table name -> source CSV
TABLES = {
    "prices": "prices_clean.csv",
    "crimes": "crime_by_outcode_month.csv",
    "outcode_summary": "outcode_summary.csv",
    "monthly_trends": "monthly_trends.csv",
}


def main() -> None:
    DB_FILE.unlink(missing_ok=True)  # rebuild from scratch every run
    conn = sqlite3.connect(DB_FILE)

    for table, csv_name in TABLES.items():
        df = pd.read_csv(PROCESSED / csv_name)
        df.to_sql(table, conn, index=False)
        print(f"  {table:16s} {len(df):>6,} rows")

    # Indexes on the join/filter columns the analysis queries actually use.
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_prices_outcode ON prices(outcode)")
    cur.execute("CREATE INDEX idx_prices_month   ON prices(month)")
    cur.execute("CREATE INDEX idx_crimes_outcode ON crimes(outcode)")
    conn.commit()
    conn.close()
    print(f"Database ready: {DB_FILE}")


if __name__ == "__main__":
    main()
