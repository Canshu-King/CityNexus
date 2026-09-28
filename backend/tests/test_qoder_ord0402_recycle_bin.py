"""ORD-0402 slice 1 - the recycle bin gets its own door, and it says what it knows.

Measured at the authoritative tip `8f4ddfa9feffe4233b48cbf608caf8e1bbb76291`: the server could
soft-delete a trip (ORD-0383) and bring it back (ORD-0399), but nothing listed what was in the bin.
A screen would have had to conclude "that trip was deleted" from it being missing in
`GET /api/v1/journeys`, which is exactly the inference the order forbids.

What the four hard constraints became in code, and which arm proves each:

1. `GET /api/v1/journeys` is untouched.  One arm compares that function's bytes against the same
   function as recorded at the baseline tip in `review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json`,
   so "not one word changed" is a diff, not a promise.  The record is a committed file rather than
   a `git show` because the suite is also run on `git archive` exports, which have no `.git`;
2. every bin row carries `deleted_at` as stored and `bin_state` = IN_RECYCLE_BIN, both read from
   the column rather than inferred - the arms check the value equals what the DELETE wrote and
   that the state word has exactly one possible value;
3. the contract and the generated client move in the same commit - the last arm parses both and
   compares operation ids, because the checked-in `frontend/src/generated/api.ts` was two slices
   behind and that drift is what the ORD-0387 contract-sync arms were built to catch;
4. no pagination, no per-traveller scope, no filter: an arm reads the contract's parameter list
   for this path and asserts it is empty, so the copy cannot promise a filter the door lacks.

The two doors partition the store - live rows plus bin rows equal every row - which is the
reading that makes "it is in the bin" and "it is in the list" one fact instead of two guesses.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import Traveler
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend/src/generated/api.ts"
BASELINE_TIP = "8f4ddfa9feffe4233b48cbf608caf8e1bbb76291"
BASELINE_ARTIFACT = ROOT / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)


def _store_path() -> Path:
    from conftest import RESOLVED_TEST_DATABASE

    return Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1)).expanduser().resolve()


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0402 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey() -> str:
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": _traveler(),
            "title": "ORD-0402",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _bin_rows() -> list[dict]:
    answer = client.get("/api/v1/recycle-bin/journeys")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert isinstance(body, list), type(body)
    return list(body)


def _bin_ids() -> list[str]:
    return [str(row["id"]) for row in _bin_rows()]


def _list_ids() -> list[str]:
    answer = client.get("/api/v1/journeys")
    assert answer.status_code == 200, answer.text
    return [str(item["id"]) for item in answer.json()]


def _stored_deleted_at(journey_id: str) -> tuple[str | None, int]:
    with sqlite3.connect(_store_path()) as connection:
        row = connection.execute(
            "SELECT deleted_at, rowid FROM journeys WHERE id = ?", (journey_id,)
        ).fetchone()
    return (row[0] if row else None), (int(row[1]) if row else -1)


def _journey_function(text: str) -> str:
    start = text.index('@app.get("/api/v1/journeys", response_model=list[JourneySchema])')
    end = text.index('@app.delete("/api/v1/journeys/{journey_id}", status_code=204)')
    return text[start:end]


# ----------------------------------------------------- constraint 1: the other door is intact


def test_the_existing_list_door_was_not_touched_down_to_its_bytes() -> None:
    """The order said not one word, so this is a byte diff against the recorded baseline.

    The baseline is a committed artifact, not a `git show` (ORD-0402 tail): the suite is also run
    on whole-tree `git archive` exports, and a git call there dies with rc 128 - `fatal: not a git
    repository` - which reports the environment and says nothing about the door.  The artifact
    pins the tip and the `main.py` blob it was cut from, so it cannot be quietly re-pointed at a
    later tree, and its own bytes are checked against the hash recorded inside it.
    """

    assert BASELINE_ARTIFACT.is_file(), (
        f"baseline record missing from this tree: {BASELINE_ARTIFACT} - it ships with the arm, so "
        "a partial export that drops review/ cannot judge this door"
    )
    baseline = json.loads(BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    assert baseline["baseline_tip"] == BASELINE_TIP, baseline["baseline_tip"]
    recorded = baseline["segment_lf"]
    assert hashlib.sha256(recorded.encode("utf-8")).hexdigest() == baseline["segment_sha256"], (
        "the baseline record no longer matches the hash inside it: regenerate it, do not hand-patch it"
    )

    # Newline convention is the store's business; the words are the order's.
    mine = _journey_function((ROOT / "backend/app/main.py").read_text(encoding="utf-8"))
    mine = mine.replace("\r\n", "\n")
    assert recorded == mine, "list_journeys moved - the order forbids changing this door"
    # And it still answers only the not-deleted rows, with the binned trip absent.
    journey_id = _journey()
    assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204
    assert journey_id not in _list_ids(), "the old door started answering binned rows"
    live = _journey()
    entry = next(item for item in client.get("/api/v1/journeys").json() if item["id"] == live)
    assert "deleted_at" not in entry and "bin_state" not in entry, sorted(entry)


# ------------------------------------------ constraint 2: the bin says so, in the row itself


def test_the_bin_answers_with_the_stored_moment_and_one_named_state() -> None:
    journey_id = _journey()
    assert journey_id not in _bin_ids(), "a live trip appeared in the bin"

    assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204
    stored, rowid = _stored_deleted_at(journey_id)
    assert stored is not None, (stored, rowid)

    rows = _bin_rows()
    entry = next((row for row in rows if str(row["id"]) == journey_id), None)
    assert entry is not None, _bin_ids()
    assert entry["bin_state"] == "IN_RECYCLE_BIN", entry
    # the original value, not a reformatted or invented one
    assert datetime.fromisoformat(str(entry["deleted_at"])) == datetime.fromisoformat(stored), (
        entry["deleted_at"],
        stored,
    )
    # the trip part is the same body getJourney answers for that row
    single = client.get(f"/api/v1/journeys/{journey_id}")
    assert single.status_code == 200, single.text
    for field in ("traveler_id", "title", "city_code", "status", "planning_mode"):
        assert entry[field] == single.json()[field], field
    print(
        f"[ord0402][bin] store={_store_path()} journeys.id={journey_id} rowid={rowid} "
        f"bin_state={entry['bin_state']} deleted_at_returned={entry['deleted_at']} "
        f"deleted_at_stored={stored} rows_in_bin={len(rows)}"
    )


def test_live_rows_and_bin_rows_partition_the_whole_store() -> None:
    kept = _journey()
    binned_a = _journey()
    binned_b = _journey()
    for journey_id in (binned_a, binned_b):
        assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204

    listed = set(_list_ids())
    binned = set(_bin_ids())
    with sqlite3.connect(_store_path()) as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM journeys").fetchone()[0])
        stored_binned = int(
            connection.execute(
                "SELECT COUNT(*) FROM journeys WHERE deleted_at IS NOT NULL"
            ).fetchone()[0]
        )
    assert {binned_a, binned_b} <= binned, sorted(binned - {binned_a, binned_b})
    assert len(binned) == stored_binned, (len(binned), stored_binned)
    assert listed.isdisjoint(binned), sorted(listed & binned)
    assert len(listed) + len(binned) == total, (len(listed), len(binned), total)
    assert kept in listed and kept not in binned, (kept, sorted(listed)[:3])
    print(
        f"[ord0402][partition] store={_store_path()} list_rows={len(listed)} "
        f"bin_rows={len(binned)} stored_not_null_rows={stored_binned} journeys_total={total}"
    )


def test_the_bin_orders_newest_deletion_first() -> None:
    first = _journey()
    second = _journey()
    for journey_id in (first, second):
        assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204
    ids = _bin_ids()
    moments = [str(row["deleted_at"]) for row in _bin_rows()]
    assert moments == sorted(moments, reverse=True), moments
    assert ids.index(second) < ids.index(first), (ids.index(second), ids.index(first))


def test_undeleting_moves_the_row_out_of_the_bin_and_back_into_the_list() -> None:
    journey_id = _journey()
    assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204
    assert journey_id in _bin_ids(), "the trip never reached the bin"

    assert client.post(f"/api/v1/journeys/{journey_id}/undelete").status_code == 200
    assert journey_id not in _bin_ids(), "the bin still holds a trip that was brought back"
    assert journey_id in _list_ids(), "the list did not get it back"
    stored, _rowid = _stored_deleted_at(journey_id)
    assert stored is None, stored


# --------------------------------- constraints 3 and 4: the contract, the client, no filters


def _contract_operations(spec: dict) -> set[str]:
    return {
        str(operation["operationId"])
        for path in spec["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }


def test_the_contract_declares_the_door_with_both_bin_facts_and_no_filter() -> None:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    path = spec["paths"]["/recycle-bin/journeys"]
    operation = path["get"]
    assert operation["operationId"] == "listRecycleBinJourneys", sorted(operation)
    assert "parameters" not in path and "parameters" not in operation, (
        "constraint 4: this version has no pagination, no scope and no filter parameter, so the "
        "contract must not advertise one either"
    )
    item = operation["responses"]["200"]["content"]["application/json"]["schema"]["items"]
    assert item == {"$ref": "#/components/schemas/RecycleBinJourney"}, item
    component = spec["components"]["schemas"]["RecycleBinJourney"]
    assert component["allOf"][0] == {"$ref": "#/components/schemas/Journey"}, component
    added = component["allOf"][1]
    assert sorted(added["required"]) == ["bin_state", "deleted_at"], added
    assert added["properties"]["bin_state"]["enum"] == ["IN_RECYCLE_BIN"], added
    assert added["properties"]["deleted_at"]["format"] == "date-time", added


def test_the_generated_client_carries_every_operation_the_contract_declares() -> None:
    """The drift the ORD-0387 arms were built for, measured as a set on both artifacts.

    The checked-in `frontend/src/generated/api.ts` predated ORD-0383 and ORD-0399, so this arm is
    also the guard that the regeneration in this commit did not drop anything: every operationId
    in the contract has to appear as an `operations["..."]` reference in the generated file.
    """

    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    contract_ops = _contract_operations(spec)
    generated = GENERATED.read_text(encoding="utf-8")
    missing = sorted(op for op in contract_ops if f'operations["{op}"]' not in generated)
    assert missing == [], f"{len(missing)} contract operations are absent from api.ts: {missing}"
    for needed in ("listRecycleBinJourneys", "RecycleBinJourney", "IN_RECYCLE_BIN"):
        assert needed in generated, needed
    print(
        f"[ord0402][codegen] contract_operations={len(contract_ops)} "
        f"missing_from_generated_api_ts={len(missing)} "
        f"api_ts_bytes={len(generated.encode('utf-8'))} "
        f"recycle_bin_reference_present={'listRecycleBinJourneys' in generated}"
    )


# ------------------------------------------------------ the cross-lane seam, pinned both ways

PANEL = ROOT / "frontend/src/features/trash/journeyTrash.ts"


def test_the_panels_one_constant_and_field_names_match_the_route_that_was_landed() -> None:
    """Slice 2 reaches this door through one TS literal, and nothing checked the two agree.

    The panel was written against a door that was not on the line when it was cut, and it names
    the path and the row fields itself in `frontend/src/features/trash/journeyTrash.ts`.  This arm
    reads those literals out of that file and holds them against the live route table and a real
    answer, so a rename on either side goes red here rather than surfacing as a silently empty bin
    on a phone.  It is a seam, not a copy: it asserts only what the two files already promise.
    """

    source = PANEL.read_text(encoding="utf-8")
    declared_path = re.search(r'TRASH_LIST_PATH = "([^"]+)"', source).group(1)
    block = re.search(r"export type DiscardedJourney = \{(.*?)\n\};", source, re.DOTALL).group(1)
    declared_fields = re.findall(r"^\s*(\w+)\??:", block, re.MULTILINE)
    expected_word = re.search(r"`(IN_[A-Z_]+)` is what this file expects", source).group(1)

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/v1" + declared_path in paths, sorted(path for path in paths if "journey" in path)
    assert {"/api/v1" + declared_path, "/api/v1/journeys"} <= paths, sorted(paths)

    journey_id = _journey()
    assert client.delete(f"/api/v1/journeys/{journey_id}").status_code == 204
    row = next(item for item in _bin_rows() if str(item["id"]) == journey_id)
    absent = [name for name in declared_fields if name not in row]
    assert absent == [], f"the panel declares fields this door does not send: {absent}"
    assert str(row["bin_state"]) == expected_word, (row["bin_state"], expected_word)
    # The raw column value, because the panel treats a null there as "the server did not answer".
    stored, _rowid = _stored_deleted_at(journey_id)
    assert datetime.fromisoformat(str(row["deleted_at"])) == datetime.fromisoformat(stored), (
        row["deleted_at"],
        stored,
    )
    print(
        f"[ord0402][seam] panel=frontend/src/features/trash/journeyTrash.ts "
        f"declared_path={declared_path} declared_field_count={len(declared_fields)} "
        f"missing_from_the_row={len(absent)} expected_bin_state={expected_word} "
        f"route_table_contains_the_path=True"
    )
