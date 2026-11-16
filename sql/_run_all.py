"""Validate every sql/*.sql file runs against the generated CSVs via DuckDB.
Not part of the deliverable's narrative; a developer aid to prove the SQL is valid.
Prints the LAST result set of each file (usually the summary) plus any errors."""
import glob, os, sys
import duckdb

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "database", "data", "synthetic")

con = duckdb.connect()
for t in ["users","titles","episodes","sessions","subscriptions","payments",
          "consumption_events","app_events"]:
    con.execute(f"""CREATE VIEW {t} AS
                    SELECT * FROM read_csv_auto('{os.path.join(DATA, t+'.csv')}', header=true)""")

files = sorted(glob.glob(os.path.join(HERE, "0*.sql")))
only = sys.argv[1] if len(sys.argv) > 1 else None
for fp in files:
    if only and only not in fp:
        continue
    name = os.path.basename(fp)
    raw = open(fp, encoding="utf-8").read()
    # remove -- line comments first, then split on semicolons
    sql = "\n".join(line.split("--")[0] for line in raw.splitlines())
    stmts = [s.strip() for s in sql.split(";") if s.strip()]
    print(f"\n########## {name}  ({len(stmts)} statements) ##########")
    for i, st in enumerate(stmts, 1):
        try:
            res = con.execute(st)
            rows = res.fetchall()
            cols = [d[0] for d in res.description] if res.description else []
            tag = f"[stmt {i}] OK  {len(rows)} rows"
            print(tag)
            # show a small preview of the first few rows
            if rows:
                print("   cols:", cols)
                for r in rows[:8]:
                    print("   ", r)
        except Exception as e:
            print(f"[stmt {i}] ERROR: {e}")
            print("   >>>", st[:160].replace("\n", " "))
print("\nvalidation done.")
