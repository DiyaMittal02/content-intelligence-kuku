"""Bulk-load the generated CSVs into a Postgres database defined by schema.sql.

Usage:
    createdb kuku_ci
    psql -d kuku_ci -f database/schema.sql
    python database/load_to_postgres.py --dsn "dbname=kuku_ci user=postgres"

Uses COPY for speed. Requires psycopg2 (pip install psycopg2-binary).
"""
import argparse
import os

import psycopg2

TABLES = [  # load order respects foreign keys
    "users", "titles", "episodes", "sessions",
    "subscriptions", "payments", "consumption_events", "app_events",
]


def main(dsn, data_dir):
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()
    for t in TABLES:
        path = os.path.join(data_dir, f"{t}.csv")
        with open(path, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            cols = header.split(",")
            print(f"COPY {t} ({len(cols)} cols) from {os.path.basename(path)} ...")
            cur.copy_expert(
                f"COPY {t} ({header}) FROM STDIN WITH (FORMAT csv, NULL '')", f
            )
    conn.commit()
    # quick sanity counts
    for t in TABLES:
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"  {t:20} {cur.fetchone()[0]:>12,}")
    cur.close()
    conn.close()
    print("Load complete.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default="dbname=kuku_ci")
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "data", "synthetic"))
    args = ap.parse_args()
    main(args.dsn, args.data)
