"""ORD-0553 r14 -- can a non-destructive door feed the v13 spec, measured on an empty store.

The cell waiting for a ruling is `frontend/e2e/v13-authoritative-integrity.spec.ts:21`: its first call is
`POST /api/v1/demo/reset`, which the commander forbids absolutely (it clears the board before seeding).
The tip carries a second door, `POST /api/v1/demo/scene/ensure`, documented as add-only.  Whether that
door can actually replace the first one is a measurement, not a reading of a docstring, so this file:

  * starts from a genuinely empty store (zero place rows, zero journeys) in MY directory;
  * records each refusal of the door and proves the refusal wrote nothing (count before == count after);
  * takes the door to its success answer and reads back what state it leaves;
  * then replays the spec's own next three calls (generate -> select -> start) against that state and
    records their HTTP answers -- which is the question the ruling actually turns on;
  * and includes a counter-arm that must fail, so a green here is not a rubber stamp.

`demo/reset` is never called by this file.  The interpreter is the project venv; nothing here opens the
shared preview database.
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import uuid

# `Settings` is frozen at import time (backend/app/config.py), and `demo_mode_enabled()` reads it, so
# every switch has to be in the environment before the first `app.*` import below.  The first version
# of this instrument set them after importing app.db.session and every arm answered DEMO_MODE_REQUIRED
# -- a red caused by the instrument, not by the door.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DEMO_SCENE_TOKEN"] = "cmdra-r14-" + uuid.uuid4().hex

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import get_session, make_engine  # noqa: E402

SCENE_ENV = "CITYNEXUS_DEMO_SCENE_TOKEN"
SCENE_HEADER = "X-Demo-Scene-Token"
RESET_HEADER = "X-Demo-Reset-Token"
TABLES = ["places", "travelers", "journeys", "plan_versions", "activities"]
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "_evidence", "r14_scene_door.json")


def counts(conn):
    have = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    return {t: (conn.execute("select count(*) from %s" % t).fetchone()[0] if t in have else "NO_TABLE")
            for t in TABLES}


os.environ[SCENE_ENV] = "cmdra-r14-" + uuid.uuid4().hex
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")
path = os.path.join(tempfile.gettempdir(), "cmdra_r14_%s.db" % uuid.uuid4().hex[:8])
engine = make_engine("sqlite:///%s" % path.replace("\\", "/"))
Base.metadata.create_all(engine)
sessions = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def _override():
    with sessions() as session:
        yield session


from app.main import app  # noqa: E402

app.dependency_overrides[get_session] = _override
client = TestClient(app)
conn = sqlite3.connect(path)
out = {"instrument": "cmdra_0553_scene_door_r14", "store_path_is_temp": True,
       "reset_was_called": False, "arms": [], "readings": {}}


def arm(ident, ok, observed):
    out["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


def post(route, headers=None, body=None):
    r = client.post(route, headers=headers or {}, json=body if body is not None else {})
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"text": r.text[:200]}


start = counts(conn)
out["readings"]["empty_store_counts"] = start
arm("store_starts_really_empty",
    all(v == 0 for v in start.values()),
    "counts %s" % json.dumps(start))

code, body = post("/api/v1/demo/scene/ensure", headers={"Idempotency-Key": "k1"})
after_no_token = counts(conn)
out["readings"]["no_token_body"] = json.dumps(body)[:260]
arm("ensure_without_token_refuses_by_name_and_writes_nothing",
    code == 403 and "SCENE_TOKEN_REQUIRED" in json.dumps(body) and after_no_token == start,
    "http=%s named=%s counts_equal_before_after=%s" % (
        code, "SCENE_TOKEN_REQUIRED" in json.dumps(body), after_no_token == start))

code, body = post("/api/v1/demo/scene/ensure", headers={SCENE_HEADER: os.environ[SCENE_ENV]})
out["readings"]["no_key_body"] = json.dumps(body)[:260]
arm("ensure_without_idempotency_key_refuses",
    code == 422, "http=%s body_keys=%s" % (code, sorted(body)[:6] if isinstance(body, dict) else None))

key = "cmdra-r14-" + uuid.uuid4().hex
code, body = post("/api/v1/demo/scene/ensure",
                  headers={SCENE_HEADER: os.environ[SCENE_ENV], "Idempotency-Key": key})
after_ok = counts(conn)
out["readings"]["ensure_http"] = code
out["readings"]["ensure_body_keys"] = sorted(body)[:14] if isinstance(body, dict) else None
out["readings"]["counts_after_ensure"] = after_ok
arm("ensure_writes_on_an_empty_store",
    code in (200, 201) and any(isinstance(v, int) and v > 0 for v in after_ok.values()),
    "http=%s counts=%s" % (code, json.dumps(after_ok)))

# two more calls on the key above: one legal replay, one real conflict
code_same, body_same = post("/api/v1/demo/scene/ensure",
                            headers={SCENE_HEADER: os.environ[SCENE_ENV], "Idempotency-Key": key})
after_same = counts(conn)
out["readings"]["replay_same_key_same_signed_fields"] = {
    "http": code_same, "idempotency_replay": bool(isinstance(body_same, dict)
                                                  and body_same.get("idempotency_replay")),
    "counts_equal_after_replay": after_same == after_ok}
arm("replaying_the_same_signed_request_is_a_receipt_not_a_second_board",
    code_same < 400 and out["readings"]["replay_same_key_same_signed_fields"]["idempotency_replay"]
    and after_same == after_ok,
    "http=%s flagged_replay=%s counts_unchanged=%s" % (
        code_same, out["readings"]["replay_same_key_same_signed_fields"]["idempotency_replay"],
        after_same == after_ok))

code2, body2 = post("/api/v1/demo/scene/ensure",
                    headers={SCENE_HEADER: os.environ[SCENE_ENV], "Idempotency-Key": key},
                    body={"city_code": "CN-TIANJIN"})
after2 = counts(conn)
out["readings"]["conflict_body"] = json.dumps(body2)[:260]
arm("counterexample_same_key_different_SIGNED_field_conflicts",
    code2 == 422 and "IDEMPOTENCY_KEY_REUSE_CONFLICT" in json.dumps(body2),
    "http=%s named=%s counts_unchanged=%s -- the signature covers city_code and journey_id "
    "(canonical_request_signature in demo_scene.py), so an unsigned field is a legal replay and "
    "my first version aimed this arm at the wrong field" % (
        code2, "IDEMPOTENCY_KEY_REUSE_CONFLICT" in json.dumps(body2), after2 == after_ok))

scene_code, scene = client.get("/api/v1/demo/scene").status_code, client.get("/api/v1/demo/scene").json()
jid = scene.get("journey_id") if isinstance(scene, dict) else None
out["readings"]["demo_scene_http"] = scene_code
out["readings"]["demo_scene_journey_id_present"] = bool(jid)
out["readings"]["demo_scene_keys"] = sorted(scene)[:14] if isinstance(scene, dict) else None

if jid:
    code, gen = post("/api/v1/journeys/%s/plans/generate" % jid,
                     headers={"Content-Type": "application/json"}, body={"candidate_count": 1})
    plans = gen if isinstance(gen, list) else []
    out["readings"]["spec_step_generate"] = {"http": code, "produced": len(plans)}
    sel_code = sel_body = None
    if plans:
        sel_code, sel_body = post("/api/v1/journeys/%s/plans/%s/select" % (jid, plans[0].get("id")),
                                  headers={"Idempotency-Key": "sel-" + uuid.uuid4().hex})
        out["readings"]["spec_step_select"] = {"http": sel_code}
    st_code, st_body = post("/api/v1/journeys/%s/start" % jid)
    out["readings"]["spec_step_start"] = {"http": st_code,
                                          "code_answered": (st_body.get("error", {}) or {}).get("code")
                                          if isinstance(st_body, dict) and st_code >= 400 else None}
    ok_walk = (code < 400 and len(plans) > 0 and (sel_code or 0) < 400 and st_code < 400)
    arm("the_v13_steps_after_the_seed_line_run_on_this_door_state", ok_walk,
        "generate=%s/%s select=%s start=%s" % (code, len(plans), sel_code, st_code))

    code, twin = client.get("/api/v1/journeys/%s/twin" % jid).status_code, client.get(
        "/api/v1/journeys/%s/twin" % jid).json()
    ex = (twin.get("context", {}) or {}).get("execution", {}) if isinstance(twin, dict) else {}
    out["readings"]["twin_after_the_walk"] = {"http": code, "now_state": ex.get("now_state"),
                                              "next_state": ex.get("next_state")}

for k in ("no_token", "no_key", "ok", "replay", "generate", "select", "start"):
    pass
app.dependency_overrides.pop(get_session, None)
conn.close()
red = [a["id"] for a in out["arms"] if a["verdict"] == "FAIL"]
out["verdict"] = "GREEN" if not red else "RED"
out["red_arms"] = red
io.open(REPORT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False))
