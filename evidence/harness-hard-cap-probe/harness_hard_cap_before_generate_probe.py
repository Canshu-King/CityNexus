"""EXP-HARNESS-010 (PREPARED, NOT RUN): hard capability before generate - does the response say why?

Sequencing: the arbiter put this narrow probe *after* B's ORD-0219 steps ③④⑤ (ledger 00:41 block §④),
and the tip right now is `0437b5c` = **Revert "feat(backend): the sealed demo carries its own
accessibility evidence"** (`services.py` -45/+3, and B's 218-line ORD-0219 test file deleted). With no
accessibility evidence on the demo places there is nothing for a HARD capability to conflict with, so a
run today would be **vacuous**, not green. Hence: prepare, and refuse to sign anything until the
precondition holds.

Question the probe answers (declared before measuring, so the verdict cannot be back-fitted):
    write a HARD capability that conflicts with the demo evidence, then
    `POST /api/v1/journeys/{id}/plans/generate`;
    if candidate/plan counts drop against the control arm **and** the response names no blocker
        => SILENT_CANDIDATE_LOSS   (an explainability order is warranted)
    if it names a blocker                            => HONEST_BLOCKER
    if nothing drops                                 => NO_EFFECT

Discipline:
  * black box only, as ordered: `PUT /travelers/{id}/capabilities` then `POST .../plans/generate`;
    no product edits for the probe, no direct evaluator calls, no DB row surgery;
  * disposable fixture: its own throwaway SQLite file inside the lab, seeded through
    `app.services.seed_demo` - `POST /api/v1/demo/reset` is never issued (R13 / ORD-0125);
  * the producer precheck decides whether a result may be interpreted at all;
  * `--dry-run` proves only wiring (import, route presence, request schema) and measures nothing.

Run it later with:  python lab/tools/harness_hard_cap_before_generate_probe.py --head <sha>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
BLOCKER_HINTS = ("blocker", "blockers", "reason", "reason_code", "reason_codes", "unsatisfied",
                 "constraint", "failures", "conflict", "conflicts", "excluded", "filtered",
                 "not_plannable", "diagnostics", "warnings")
DROP_HINTS = ("candidate", "options", "plans", "plans_created", "generated", "count", "total")


def export_root(head: str) -> Path:
    return LAB / f"snap_{head}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default="", help="SHA of the export to measure (lab/snap_<sha>)")
    ap.add_argument("--code", default="STEP_FREE_REQUIRED",
                    help="capability code to declare HARD (default: the one the demo evidence conflicts with)")
    ap.add_argument("--dry-run", action="store_true", help="prove wiring only; measure nothing")
    ap.add_argument("--out", default="", help="receipt path (default: lab/evidence/hard_cap_probe_*.json)")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    head = args.head or subprocess.run(["git", "-C", r"D:\moodle\_qoder_integration_20260919",
                                        "rev-parse", "--short", "HEAD"],
                                       capture_output=True, text=True).stdout.strip()
    root = export_root(head)
    backend = root / "backend"
    if not (backend / "app").is_dir():
        print(f"no export for {head}: run\n"
              f"  git -C D:/moodle/_qoder_integration_20260919 archive {head} backend data contracts tools "
              f"| tar -x -C lab/snap_{head}")
        return 2

    db = LAB / "evidence" / "_db" / f"hard_cap_probe_{os.getpid()}.db"
    env_add = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db}",
        "CITYNEXUS_DEMO_MODE": "false", "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "", "PYTHONIOENCODING": "utf-8",
    }
    print(f"head={head} export={root.name} interpreter={PY.name} db={db.name}")
    print("plan of calls:"
          "\n  0) seed the disposable fixture in-process (app.services.seed_demo; NO demo/reset)"
          "\n  1) GET  /api/v1/journeys/{id}/plans            (baseline)"
          "\n  2) POST /api/v1/journeys/{id}/plans/generate     control arm (no hard capability)"
          f"\n  3) PUT  /api/v1/travelers/{{id}}/capabilities     [{args.code} severity=HARD]"
          "\n  4) POST /api/v1/journeys/{id}/plans/generate     treatment arm"
          "\n  5) compare counts; look for a named blocker in the response; verdict = "
          "SILENT_CANDIDATE_LOSS | HONEST_BLOCKER | NO_EFFECT")

    if args.dry_run:
        # wiring proof only: import the app, confirm the two routes exist and print the
        # request body schema the probe will use. No seeding, no POST, no verdict.
        os.environ.update(env_add)
        sys.path.insert(0, str(backend))
        import app.main as product_main  # noqa: WPS433
        spec = product_main.app.openapi()
        want = ("/api/v1/journeys/{journey_id}/plans/generate",
                "/api/v1/travelers/{traveler_id}/capabilities")
        out = {"dry_run": True, "head": head, "at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
               "routes": {}}
        for path in want:
            ops = spec["paths"].get(path)
            out["routes"][path] = sorted(ops) if ops else "ABSENT"
            print(f"  route {path}: {out['routes'][path]}")
        gen = (spec["paths"].get(want[0], {}) or {}).get("post", {})
        schema = json.dumps(gen.get("requestBody", {}), ensure_ascii=False)
        out["generate_request_body"] = schema[:400]
        print(f"  generate requestBody: {schema[:200]}")
        cap = (spec["paths"].get(want[1], {}) or {}).get("put", {})
        out["capabilities_request_body"] = json.dumps(cap.get("requestBody", {}),
                                                      ensure_ascii=False)[:400]
        print(f"  capabilities requestBody: {out['capabilities_request_body'][:200]}")
        dest = Path(args.out) if args.out else LAB / "evidence" / f"hard_cap_probe_dryrun_{time.strftime('%H%M')}.json"
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
        print(f"\nDRY RUN ONLY - nothing seeded, nothing measured. receipt: {dest.name}")
        return 0

    # ---- measurement path (only meaningful once B's producer is back) ----------------------
    os.environ.update(env_add)
    sys.path.insert(0, str(backend))
    from fastapi.testclient import TestClient                    # noqa: E402
    import app.main as product_main                              # noqa: E402
    from app.db.session import SessionLocal, ensure_schema        # noqa: E402
    from app.db.models import Journey, Place, Traveler            # noqa: E402

    ensure_schema()
    session = SessionLocal()
    try:
        product_main.seed_demo(session)
        traveler_id = str(session.query(Traveler).first().id)
        journey_id = str(session.query(Journey).first().id)
        metas = [p.metadata_json for p in session.query(Place).all()]
    finally:
        session.close()

    def parse(meta):
        if isinstance(meta, str):
            try:
                return json.loads(meta or "{}")
            except ValueError:
                return {}
        return meta or {}

    carrying = sum(1 for m in metas if any(
        k in parse(m) for k in ("accessibility_evidence", "step_free", "stroller_accessible",
                                "luggage_accessible")))
    pre = {"places": len(metas), "places_with_accessibility_evidence": carrying}
    print(f"precondition: {pre}")
    if carrying == 0:
        print(f"PRECONDITION_NOT_MET: no demo place carries accessibility evidence at {head}, "
              "so a HARD capability has nothing to conflict with and the probe would be vacuous. "
              "Re-run after the producer lands (ORD-0219 steps ③④⑤).")
        return 4

    client = TestClient(product_main.app)
    counts: dict[str, object] = {}

    def summarize(label: str, resp) -> dict:
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"_unparseable": resp.text[:200]}
        blob = json.dumps(body, ensure_ascii=False).lower()
        named = sorted({h for h in BLOCKER_HINTS if h in blob})
        numbers = {k: v for k, v in (body.items() if isinstance(body, dict) else [])
                   if isinstance(v, (int, list)) and any(h in k.lower() for h in DROP_HINTS)}
        out = {"status": resp.status_code, "named_hint_keys": named, "count_fields": numbers,
               "top_keys": sorted(body)[:14] if isinstance(body, dict) else type(body).__name__}
        counts[label] = out
        print(f"  {label}: status={out['status']} counts={numbers} named={named or '-'}")
        return out

    baseline = client.get(f"/api/v1/journeys/{journey_id}/plans")
    summarize("existing_plans", baseline)
    summarize("control_generate", client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={}))
    payload = [{"code": args.code, "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
                "params": {"requirement": "step_free"}, "scope": "TRAVELER",
                "source": "USER_CONFIRMED", "provenance": "USER_STATED",
                "explicit": True, "confirmed": True, "active": True}]
    summarize("write_hard_capability", client.put(f"/api/v1/travelers/{traveler_id}/capabilities",
                                                  json=payload))
    summarize("treatment_generate", client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={}))

    ctrl = counts.get("control_generate", {})
    trea = counts.get("treatment_generate", {})
    dropped = any(isinstance(v, int) and isinstance(trea.get("count_fields", {}).get(k), int)
                  and trea["count_fields"][k] < v for k, v in (ctrl.get("count_fields") or {}).items())
    named = bool((trea.get("named_hint_keys") or []))
    verdict = ("SILENT_CANDIDATE_LOSS" if dropped and not named
               else "HONEST_BLOCKER" if dropped and named
               else "NO_EFFECT")
    receipt = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "head": head,
               "code_under_test": args.code, "precondition": pre, "arms": counts,
               "verdict": verdict, "declared_rule": "drop without named blocker => SILENT_CANDIDATE_LOSS",
               "demo_reset_issued": 0, "product_files_changed": 0}
    dest = Path(args.out) if args.out else LAB / "evidence" / f"hard_cap_probe_{head}_{time.strftime('%H%M')}.json"
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nverdict={verdict}  receipt: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
