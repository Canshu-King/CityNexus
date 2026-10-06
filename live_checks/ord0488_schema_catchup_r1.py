"""ORD-0488: does a from-zero boot actually get every table the doors need?

Three modes, one file, re-runnable:

  --mode declared            the table names `backend/db/schema.sql` creates, plus the ORM
                             declarations, and the difference between the two sets
  --mode inspect --db PATH   read that database strictly `mode=ro` and print the same sets
                             against what is really in it
  --mode boot --db PATH      run the product's own startup path (`import app.main`, which calls
                             `ensure_schema()` at module level in `backend/app/main.py`) against
                             PATH, then
                             inspect.  PATH is WRITTEN by this mode -- point it at a copy, never
                             at a live database.

The route-count column answers "how many doors are there" with the denominator named, because
151 / 164 / 158 are all true of different readings and only one of them is about tables.

Nothing here opens a socket and nothing here calls `POST /api/v1/demo/reset`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
SCHEMA_SQL = BACKEND / "db" / "schema.sql"
MODELS_PY = BACKEND / "app" / "db" / "models.py"

CREATE_RE = re.compile(r'CREATE TABLE IF NOT EXISTS\s+"?([a-z_0-9]+)"?', re.I)
TABLENAME_RE = re.compile(r'__tablename__\s*=\s*["\x27]([a-z_0-9]+)["\x27]')


def declared_tables() -> list[str]:
    return sorted(set(CREATE_RE.findall(SCHEMA_SQL.read_text(encoding="utf-8"))))


def model_tables() -> list[str]:
    return sorted(set(TABLENAME_RE.findall(MODELS_PY.read_text(encoding="utf-8"))))


def tables_in(db_path: str) -> list[str]:
    conn = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        return sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            if not row[0].startswith("sqlite_")
        )
    finally:
        conn.close()


def route_denominators() -> dict[str, int]:
    """Count the doors four different honest ways."""
    from app.main import app  # noqa: PLC0415 - boot IS the thing under test

    api = [r for r in app.routes if str(getattr(r, "path", "")).startswith("/api/v1")]
    pairs = {(m, r.path) for r in api for m in (getattr(r, "methods", None) or set())
             if m not in {"HEAD", "OPTIONS"}}
    spec = app.openapi()
    operations = sum(
        1
        for item in spec["paths"].values()
        for verb in item
        if verb.lower() in {"get", "post", "put", "patch", "delete"}
    )
    return {
        "api_route_objects": len(api),
        "method_path_pairs": len(pairs),
        "openapi_paths": len(spec["paths"]),
        "openapi_operations": operations,
    }


def boot(db_path: str) -> int:
    """Run the product startup path against `db_path` in a clean child process."""
    env = dict(os.environ)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{Path(db_path).as_posix()}"
    env.pop("DEEPSEEK_API_KEY", None)
    probe = (
        "import app.main as m;"
        "import json;"
        "print('BOOT_OK routes=%d' % len([r for r in m.app.routes"
        " if str(getattr(r,'path','')).startswith('/api/v1')]))"
    )
    return subprocess.call(
        [sys.executable, "-c", probe], cwd=str(BACKEND), env=env
    )


SHARED_PREVIEW_DB = "D:/moodle/_qoder_preview_20260920/_preview.db"


def refuse_shared_write(args: argparse.Namespace) -> None:
    """`--routes` imports app.main, and that import calls `ensure_schema()` against
    `CITYNEXUS_DATABASE_URL`.  Pointing it at the shared preview database would therefore WRITE
    the one database this order must never write, so the mode is refused rather than warned about.
    """
    wanted = str(Path(args.db or "").resolve()).replace("\\", "/").lower()
    shared = str(Path(SHARED_PREVIEW_DB).resolve()).replace("\\", "/").lower()
    if args.mode in {"boot", "inspect"} and wanted == shared and args.routes:
        raise SystemExit(
            "REFUSED: --routes boots the app against --db, and --db is the shared preview "
            "database. Read it with --mode inspect alone (that path is mode=ro only)."
        )
    if args.mode == "boot" and wanted == shared:
        raise SystemExit("REFUSED: --mode boot writes --db; --db is the shared preview database.")
    if args.mode == "inspect" and args.routes:
        # Not a courtesy: `inspect` promises mode=ro, and importing the app is a write, so the
        # combination would make the read-only reading a lie about itself.
        raise SystemExit(
            "REFUSED: --mode inspect is read-only and --routes boots the app, which writes. "
            "Ask for route counts with --mode boot against a database you mean to write."
        )


def report(args: argparse.Namespace) -> int:
    refuse_shared_write(args)
    declared = declared_tables()
    models = model_tables()
    out: dict[str, object] = {
        "schema_sql": SCHEMA_SQL.relative_to(BACKEND.parent).as_posix(),
        "declared_count": len(declared),
        "model_count": len(models),
        "models_missing_from_ddl": sorted(set(models) - set(declared)),
        "ddl_not_a_model": sorted(set(declared) - set(models)),
    }
    if args.mode == "declared":
        out["declared_tables"] = declared
    else:
        if args.mode == "inspect" and not Path(args.db).exists():
            raise SystemExit(f"REFUSED: --mode inspect needs an existing database, {args.db} is not one.")
        if args.mode == "boot":
            rc = boot(args.db)
            out["boot_child_exit_code"] = rc
        present = tables_in(args.db)
        out["db"] = args.db
        out["present_count"] = len(present)
        out["missing_in_db"] = sorted(set(declared) - set(present))
        out["present_not_declared"] = sorted(set(present) - set(declared))
    if args.routes:
        sys.path.insert(0, str(BACKEND))
        os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{Path(args.db).as_posix()}"
        os.environ.pop("DEEPSEEK_API_KEY", None)
        out["route_denominators"] = route_denominators()
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    if args.mode == "declared":
        return 0
    complete = not out.get("missing_in_db", [])
    print("VERDICT: %s (%d missing)" % ("COMPLETE" if complete else "INCOMPLETE",
                                        len(out.get("missing_in_db", []))))
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("declared", "inspect", "boot"), default="declared")
    parser.add_argument("--db")
    parser.add_argument("--routes", action="store_true")
    return report(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
