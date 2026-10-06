"""Lane 6a150e1e, building three cell 2 (pytest form of the same cases) -- the collections half, exercised against the real app.

Every case here is one of the criteria's "must go red" cases, run for real against `app.main:app`
through the same TestClient the suite uses. No mocks, no skips, no assertion loosened: if a door is
missing the case fails, which is the point.

The round trip is the building's sentence: a shelf a traveller deletes must come back and the
answer must say whether it did. The refusals are the other half of that sentence -- a shelf that was
not binned must be refused BY NAME rather than answered as an empty bin, because an empty answer is
what makes a real deletion look like nothing happened.
"""
from __future__ import annotations

import sys
import uuid

sys.path.insert(0, __file__.rsplit("/backend/", 1)[0] + "/backend")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def new_traveler() -> str:
    # `TravelerCreate` requires `timezone`; without it the door answers 422 and the whole script
    # dies on the first line, which reads like a product defect and is really a missing field here.
    r = client.post("/api/v1/travelers", json={
        "display_name": "收藏这半的读数", "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    assert r.status_code in (200, 201), (r.status_code, r.text[:200])
    return r.json()["id"]


def err(response) -> dict:
    """The named refusal, read the way this server actually writes it.

    `app.main`'s HTTPException handler nests `reason_code` and `details` under an `error` object.
    Reading them off the top level found them missing on eight cases and would have had me
    "fixing" doors that were already refusing correctly by name.
    """
    return (response.json() or {}).get("error") or {}


def new_folder(tid: str, name: str) -> str:
    r = client.post("/api/v1/collections", json={"name": name, "owner_traveler_id": tid})
    assert r.status_code == 201, (r.status_code, r.text[:200])
    return r.json()["id"]


def test_collection_bin_round_trip_and_named_refusals():
    """Every case is one of the criteria' must-go-red cases, run for real."""
    # --- 1. a shelf reads in the collection, and the bin says it is not there -------------------
    owner = new_traveler()
    other = new_traveler()
    fid = new_folder(owner, "周末想去的地方")

    listing = client.get("/api/v1/collections", params={"traveler_id": owner})
    check("collection read lists the new shelf", any(s["id"] == fid for s in listing.json()))

    bin_empty = client.get(f"/api/v1/travelers/{owner}/collections-bin")
    check("bin is empty before any delete", bin_empty.status_code == 200 and bin_empty.json() == [],
          f"status={bin_empty.status_code}")

    # --- 2. delete puts it in the bin, carrying the two stored facts ----------------------------
    gone = client.delete(f"/api/v1/travelers/{owner}/collections/{fid}")
    check("delete returns 204", gone.status_code == 204, f"status={gone.status_code}")

    after = client.get(f"/api/v1/travelers/{owner}/collections-bin")
    rows = after.json()
    check("bin now holds the shelf", len(rows) == 1 and rows[0]["id"] == fid, f"n={len(rows)}")
    check("bin row carries deleted_at", bool(rows and rows[0].get("deleted_at")),
          str(rows[0].get("deleted_at")) if rows else "")
    check("bin row carries bin_state", bool(rows) and rows[0].get("bin_state") == "IN_COLLECTION_BIN",
          str(rows[0].get("bin_state")) if rows else "")

    gone_from_listing = client.get("/api/v1/collections", params={"traveler_id": owner})
    check("binned shelf left the collection read",
          not any(s["id"] == fid for s in gone_from_listing.json()))

    # --- 3. the two refusals the building names, by name rather than as an empty bin -------------
    repeat = client.delete(f"/api/v1/travelers/{owner}/collections/{fid}")
    check("second delete is refused 409 by name",
          repeat.status_code == 409 and err(repeat).get("reason_code") == "COLLECTION_FOLDER_ALREADY_BINNED",
          f"status={repeat.status_code} code={err(repeat).get('reason_code')}")

    not_owned = client.delete(f"/api/v1/travelers/{other}/collections/{fid}")
    check("another traveller cannot delete it",
          not_owned.status_code == 404 and err(not_owned).get("reason_code") == "COLLECTION_FOLDER_NOT_OWNED",
          f"status={not_owned.status_code} code={err(not_owned).get('reason_code')}")

    other_bin = client.get(f"/api/v1/travelers/{other}/collections-bin")
    check("another traveller's bin does not hold it", other_bin.json() == [], f"n={len(other_bin.json())}")

    unknown = client.delete(f"/api/v1/travelers/{owner}/collections/{uuid.uuid4()}")
    check("unknown shelf id is refused 404 by name",
          unknown.status_code == 404 and err(unknown).get("reason_code") == "COLLECTION_FOLDER_UNKNOWN",
          f"status={unknown.status_code} code={err(unknown).get('reason_code')}")

    # --- 4. 找回 brings it back, and the answer is the shelf rather than the bin shape ------------
    back = client.post(f"/api/v1/travelers/{owner}/collections/{fid}/undelete")
    check("undelete returns 200", back.status_code == 200, f"status={back.status_code}")
    body = back.json()
    check("undelete answers the shelf shape, not the bin shape",
          "bin_state" not in body and body.get("id") == fid and body.get("name") == "周末想去的地方",
          f"keys={sorted(body)[:8]}")

    bin_now = client.get(f"/api/v1/travelers/{owner}/collections-bin")
    check("bin is empty again after the restore", bin_now.json() == [], f"n={len(bin_now.json())}")

    restored = client.get("/api/v1/collections", params={"traveler_id": owner})
    check("shelf is back in the collection read",
          any(s["id"] == fid for s in restored.json()))

    # --- 5. the 409 the building singles out: not-binned must not read as success ----------------
    again = client.post(f"/api/v1/travelers/{owner}/collections/{fid}/undelete")
    payload = again.json()
    check("undelete on a live shelf is refused 409 by name",
          again.status_code == 409 and err(again).get("reason_code") == "COLLECTION_FOLDER_NOT_BINNED",
          f"status={again.status_code} code={err(again).get('reason_code')}")
    check("that refusal carries deleted_at: null as the proof",
          (err(again).get("details") or {}).get("deleted_at", "missing") is None,
          str((err(again).get("details") or {}).get("deleted_at", "missing")))

    unknown_back = client.post(f"/api/v1/travelers/{owner}/collections/{uuid.uuid4()}/undelete")
    check("undelete on an unknown id is refused 404 by name",
          unknown_back.status_code == 404 and err(unknown_back).get("reason_code") == "COLLECTION_FOLDER_UNKNOWN",
          f"status={unknown_back.status_code} code={err(unknown_back).get('reason_code')}")

    not_mine = client.post(f"/api/v1/travelers/{other}/collections/{fid}/undelete")
    check("another traveller cannot restore it",
          not_mine.status_code == 404 and err(not_mine).get("reason_code") == "COLLECTION_FOLDER_NOT_OWNED",
          f"status={not_mine.status_code} code={err(not_mine).get('reason_code')}")

    # --- 6. the places on the shelf survive the round trip (soft, not cascade) ------------------
    # A fresh store has no places, and no product door creates one without a provider, so this case
    # writes a place row straight into the store rather than reporting "skipped". A skip here would
    # have left the whole soft-delete argument untested while the run still read as a pass -- and the
    # argument is the reason this half is soft at all: `collection_items.folder_id` CASCADES on a hard
    # delete, so a hard delete would take the places with it and 找回 would have nothing to bring back.
    places = client.get("/api/v1/places", params={"city_code": "CN-XIAMEN"})
    if not places.json():
        from app.db.models import Place  # noqa: E402
        from app.db.session import get_session  # noqa: E402
        import sqlalchemy as sa  # noqa: E402

        # `get_session` is a generator, not a context manager; `next()` on it is the session and the
        # trailing close is what commits-and-releases the way FastAPI's dependency would.
        gen = get_session()
        session = next(gen)
        if True:
            # Column set read off `Place` itself: `external_id` and the three text columns are NOT NULL,
            # so a row written without them fails at commit and the case would report "no place".
            session.add(Place(
                id="pin-soft-delete-r1", external_id="local-ruler:soft-delete-r1",
                name="收藏那半读数用的地点", category="landmark", city_code="CN-XIAMEN",
                provider_key="local-ruler", latitude=24.4798, longitude=118.0894,
                opening_hours_json="{}", tags_json="[]", metadata_json="{}",
                updated_at="2026-10-06T00:00:00", coordinate_system="WGS84",
            ))
            session.commit()
        places = client.get("/api/v1/places", params={"city_code": "CN-XIAMEN"})

    check("a place exists to collect", places.status_code == 200 and bool(places.json()),
          f"status={places.status_code} n={len(places.json()) if places.json() else 0}")
    if places.json():
        pid = places.json()[0]["id"]
        added = client.post(f"/api/v1/collections/{fid}/items", json={"place_id": pid, "note": "读数用"})
        check("a place can be put on the shelf", added.status_code == 201,
              f"status={added.status_code} body={added.text[:120]}")
        before_rows = client.get("/api/v1/collections", params={"traveler_id": owner}).json()
        before_n = next((s["item_count"] for s in before_rows if s["id"] == fid), 0)
        client.delete(f"/api/v1/travelers/{owner}/collections/{fid}")
        binned = client.get(f"/api/v1/travelers/{owner}/collections-bin").json()
        binned_n = next((s["item_count"] for s in binned if s["id"] == fid), 0)
        client.post(f"/api/v1/travelers/{owner}/collections/{fid}/undelete")
        after_rows = client.get("/api/v1/collections", params={"traveler_id": owner}).json()
        after_n = next((s["item_count"] for s in after_rows if s["id"] == fid), 0)
        check("places on the shelf survive delete (soft, not cascade)",
              before_n >= 1 and binned_n == before_n,
              f"before={before_n} binned={binned_n}")
        check("places are back on the shelf after the restore",
              after_n == before_n and after_n >= 1, f"before={before_n} after={after_n}")
    else:
        check("places on the shelf survive delete (soft, not cascade)", False, "no place to collect")
        check("places are back on the shelf after the restore", False, "no place to collect")

    # --- 7. negative control: the ruler is not simply saying yes ---------------------------------
    client.delete(f"/api/v1/travelers/{owner}/collections/{fid}")
    control = client.get(f"/api/v1/travelers/{owner}/collections-bin")
    check("negative control: after a fresh delete the bin is non-empty again",
          len(control.json()) == 1, f"n={len(control.json())}")

    failed = [n for n, ok, _ in results if not ok]
    print()
    print("TOTAL=%d PASS=%d FAIL=%d" % (len(results), len(results) - len(failed), len(failed)))
    if failed:
        print("FAILED=" + ", ".join(failed))
        raise AssertionError("FAILED=" + ", ".join(failed))
