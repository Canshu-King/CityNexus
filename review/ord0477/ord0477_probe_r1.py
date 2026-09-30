"""ORD-0477 in-process probe: does the door import, what does the generated spec say, and does the
sort answer?  Writes its own scratch sqlite file and one UTF-8 JSON report (the console here is GBK,
so no CJK is printed).  Nothing here is evidence for the ledger; it is the reading that decides
whether the gate is worth building."""
from __future__ import annotations

import json
import os
import pathlib
import sys

TREE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0477")
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
DB = RUN / "_ord0477_probe.db"
REPORT = RUN / "ord0477_probe_r1.json"
if DB.exists():
    DB.unlink()
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB.as_posix()
os.environ["CITYNEXUS_E2E_RUN_ID"] = "ord0477_probe"
sys.path.insert(0, str(TREE / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

out: dict = {"python": sys.version.split()[0], "db": DB.as_posix()}

spec = app.openapi()
journeys_get = spec["paths"]["/api/v1/journeys"]["get"]
out["parameters"] = journeys_get.get("parameters")
out["responses_keys"] = sorted(journeys_get["responses"])
out["responses_422"] = journeys_get["responses"].get("422")

ROWS = [
    ("zoo walk", "2026-11-03T09:00:00+08:00", "2026-11-04T09:00:00+08:00"),
    ("Apple market", "2026-11-03T08:00:00+00:00", "2026-11-04T08:00:00+00:00"),
    ("\u6cb3\u6cbf\u591c\u8bdd", "2026-11-05T09:00:00", "2026-11-06T09:00:00"),
]

with TestClient(app) as client:
    traveler = client.post(
        "/api/v1/travelers",
        json={"display_name": "probe", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    out["traveler_status"] = traveler.status_code
    tid = traveler.json()["id"]

    out["creates"] = []
    for title, start, end in ROWS:
        created = client.post(
            "/api/v1/journeys",
            json={
                "traveler_id": tid,
                "title": title,
                "city_code": "CN-TIANJIN",
                "timezone": "Asia/Shanghai",
                "start_at": start,
                "end_at": end,
                "budget": {"currency": "CNY", "amount_minor": 90000},
            },
        )
        out["creates"].append(
            {
                "title": title,
                "status": created.status_code,
                "id": (created.json() or {}).get("id") if created.status_code == 201 else None,
                "detail": None if created.status_code == 201 else created.text[:200],
            }
        )

    stored = client.get("/api/v1/journeys").json()
    out["stored_start_at"] = {row["title"]: row.get("start_at") for row in stored}

    for tier in [None, "RECENT_UPDATE", "DEPARTURE_DATE", "TITLE"]:
        url = "/api/v1/journeys" + (f"?sort={tier}" if tier else "")
        answer = client.get(url)
        body = answer.json()
        out.setdefault("orders", {})[str(tier)] = {
            "status": answer.status_code,
            "titles": [row["title"] for row in body] if isinstance(body, list) else body,
        }

    refused = client.get("/api/v1/journeys?sort=by_mood")
    out["refusal"] = {"status": refused.status_code, "body": refused.json()}

    # the empty-collection reading: every trip this probe made goes in the bin, then the door answers
    for row in stored:
        out.setdefault("deletes", []).append(
            client.delete(f"/api/v1/journeys/{row['id']}").status_code
        )
    for tier in [None, "RECENT_UPDATE", "DEPARTURE_DATE", "TITLE"]:
        url = "/api/v1/journeys" + (f"?sort={tier}" if tier else "")
        answer = client.get(url)
        out.setdefault("empty", {})[str(tier)] = {
            "status": answer.status_code,
            "body": answer.json(),
        }

REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("report", REPORT.as_posix(), "bytes", REPORT.stat().st_size)
