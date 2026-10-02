from datetime import date
from pathlib import Path
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
SRC = BASE / "db.sqlite3"
OUT_DIR = BASE / "exports"
STAMP = date.today().isoformat()
SQLITE_OUT = OUT_DIR / f"1bir-database-{STAMP}.sqlite3"
SQL_OUT = OUT_DIR / f"1bir-database-{STAMP}.sql"
DOWNLOADS = Path.home() / "Downloads" / f"1bir-database-{STAMP}.sqlite3"


def main():
    if not SRC.exists():
        raise SystemExit(f"Database not found: {SRC}")
    OUT_DIR.mkdir(exist_ok=True)
    if SQLITE_OUT.exists():
        SQLITE_OUT.unlink()

    conn = sqlite3.connect(SRC)
    target = SQLITE_OUT.resolve().as_posix().replace("'", "''")
    conn.execute(f"VACUUM INTO '{target}'")
    with SQL_OUT.open("w", encoding="utf-8") as fh:
        for line in conn.iterdump():
            fh.write(line + "\n")
    conn.close()
    shutil.copy2(SQLITE_OUT, DOWNLOADS)
    print(f"SQLite: {SQLITE_OUT} ({SQLITE_OUT.stat().st_size} bytes)")
    print(f"SQL:    {SQL_OUT} ({SQL_OUT.stat().st_size} bytes)")
    print(f"Copy:   {DOWNLOADS}")


if __name__ == "__main__":
    main()
