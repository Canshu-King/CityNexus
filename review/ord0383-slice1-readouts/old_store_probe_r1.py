"""ORD-0383 slice 1 - the three readings the commander asked for at 16:52.

Nothing here opens a shared store. Every database is a file this process creates under
`--scratch` and prints the absolute path of. No `POST /api/v1/demo/reset` is called (it now
needs `X-Demo-Reset-Token`, and the order says do not try it on the shared preview anyway).
The "old library" is built from the authoritative tip's own schema.sql, taken with
`git show 1f8d7061...:backend/db/schema.sql`, so it is the real pre-ORD-0383 shape and not a
hand-written impression of it.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


def git_show(rev: str, path: str, repo: Path) -> str:
    out = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"],
                         capture_output=True, text=True, encoding="utf-8", check=False)
    assert out.returncode == 0, out.stderr[:200]
    return out.stdout


def pragma_columns(db: Path, table: str = "journeys") -> list[str]:
    with sqlite3.connect(db) as connection:
        return [str(row[1]) for row in connection.execute(
            f"PRAGMA table_info({table})").fetchall()]


def seed_one_journey(db: Path, journey_id: str) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    tz = timezone(timedelta(hours=8))
    start = datetime(2026, 11, 3, 9, 0, tzinfo=tz)
    # A UUID, because `JourneySchema.traveler_id` is typed UUID - a non-UUID probe id would make
    # the route fail on the schema, not on the column, and that reading would be about my script.
    traveler_id = "22222222-2222-4222-8222-222222222222"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO travelers (id, display_name, email, locale, timezone, created_at,"
            " updated_at) VALUES (?, 'ORD-0383 probe', NULL, 'zh-CN', 'Asia/Shanghai', ?, ?)",
            (traveler_id, now, now),
        )
        connection.execute(
            "INSERT INTO journeys (id, traveler_id, title, city_code, timezone, start_at,"
            " end_at, budget_currency, budget_amount_minor, planning_mode, status, created_at,"
            " updated_at) VALUES (?, ?, ?, 'CN-XIAMEN', 'Asia/Shanghai', ?, ?, "
            " 'CNY', 90000, 'balanced', 'DRAFT', ?, ?)",
            (journey_id, traveler_id, "the row that predates the column", start.isoformat(),
             (start + timedelta(days=2)).isoformat(), now, now),
        )
        connection.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True, type=Path)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tip", default="1f8d7061f9edd66652c198db983722cdd237f2b7")
    args = ap.parse_args()

    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    old_db = scratch / "ord0383_old_store.db"
    fresh_db = scratch / "ord0383_fresh_store.db"
    for path in (old_db, fresh_db):
        if path.exists():
            path.unlink()

    # A: the authoritative tip's schema - which does NOT have journeys.deleted_at.
    old_sql = git_show(args.tip, "backend/db/schema.sql", args.repo)
    with sqlite3.connect(old_db) as connection:
        connection.executescript(old_sql)
    print(f"[A] store={old_db}")
    print(f"[A] built from git show {args.tip}:backend/db/schema.sql bytes={len(old_sql)}")
    print(f"[A] pragma_before_seed={pragma_columns(old_db)}")
    journey_id = "11111111-1111-4111-8111-111111111111"
    seed_one_journey(old_db, journey_id)
    print(f"[A] seeded journeys.id={journey_id} deleted_at_absent_from_ddl="
          f"{'deleted_at' not in pragma_columns(old_db)}")

    # B: this lane's schema, fresh - for the column-order comparison in reading (3).
    with sqlite3.connect(fresh_db) as sqlite3_conn:
        sqlite3_conn.executescript(git_show("HEAD", "backend/db/schema.sql", args.repo))
    print(f"[B] store={fresh_db}")

    # (1) the boot path: importing app.main runs ensure_schema() on the engine the env var names.
    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{old_db.as_posix()}"
    os.environ["CITYNEXUS_PROVIDER_NETWORK_MODE"] = "direct"
    pragma_before_boot = pragma_columns(old_db)
    from app.main import app
    from fastapi.testclient import TestClient
    # raise_server_exceptions=False because the question is "what does the server answer", and a
    # raised traceback caught by TestClient would replace the product's own envelope with my script.
    client = TestClient(app, raise_server_exceptions=False)
    pragma_after_boot = pragma_columns(old_db)
    print(f"[1] importing app.main ran ensure_schema() on store A: "
          f"deleted_at_before={'deleted_at' in pragma_before_boot} "
          f"deleted_at_after={'deleted_at' in pragma_after_boot}")
    print(f"[1] pragma_after_boot={pragma_after_boot}")
    print(f"[1] position_of_deleted_at_index={pragma_after_boot.index('deleted_at')}"
          f" of_columns_total={len(pragma_after_boot)}")

    answer = client.get("/api/v1/journeys")
    listed = [str(item["id"]) for item in answer.json()] if answer.status_code == 200 else []
    print(f"[2a] GET /api/v1/journeys on a migrated-at-boot old store: status={answer.status_code}"
          f" rows_returned={len(listed)} contains_seeded_row={journey_id in listed}")

    # (2) now force the state the column-less store would be in if the guard had not run:
    # drop the column at runtime and read the same SQL the route builds.
    with sqlite3.connect(old_db) as connection:
        connection.execute("ALTER TABLE journeys DROP COLUMN deleted_at")
        connection.commit()
    print(f"[2] store={old_db} after ALTER DROP: pragma={pragma_columns(old_db)}")
    bare = None
    try:
        with sqlite3.connect(old_db) as connection:
            connection.execute(
                "SELECT count(*) FROM journeys WHERE journeys.deleted_at IS NULL"
                " ORDER BY journeys.created_at, journeys.id").fetchall()
    except sqlite3.OperationalError as exc:
        bare = str(exc)
    print(f"[2] bare_sql_without_the_column error={json.dumps(bare)}")

    missing = client.get("/api/v1/journeys")
    print(f"[2b] GET /api/v1/journeys with the column absent: status={missing.status_code}")
    print(f"[2b] body_bytes={len(missing.content)} body_first_400="
          f"{json.dumps(missing.text[:400])}")
    deleted = client.delete(f"/api/v1/journeys/{journey_id}")
    print(f"[2c] DELETE /api/v1/journeys/{{id}} with the column absent: status={deleted.status_code}"
          f" body_first_240={json.dumps(deleted.text[:240])}")
    single = client.get(f"/api/v1/journeys/{journey_id}")
    print(f"[2d] GET /api/v1/journeys/{{id}} (does not filter the column) status="
          f"{single.status_code} body_bytes={len(single.content)}")

    # (3) put it back the way boot leaves it, and print the column list the guard produces.
    from app.db import session as session_module
    session_module.ensure_schema(session_module.engine)
    restored = pragma_columns(old_db)
    print(f"[3] after re-running ensure_schema: pragma={json.dumps(restored)}")
    print(f"[3] fresh_store_pragma={json.dumps(pragma_columns(fresh_db))}")
    same_order = restored == pragma_columns(fresh_db)
    print(f"[3] migrated_order_equals_fresh_ddl_order={same_order}")
    after = client.get("/api/v1/journeys")
    print(f"[3] GET /api/v1/journeys again: status={after.status_code} "
          f"rows_returned={len(after.json()) if after.status_code == 200 else -1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
