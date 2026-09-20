"""ORD-0079 must 2/3: the M3 vertical slice on the demo stage, measured end to end.

Run:  python review/probe-ord79-m3-slice.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord79/m3-slice.json

The order says M3 ("Event -> ReplanProposal -> Accept -> new ACTIVE plan") is blocked because
the seeded plan carries no inter-stop travel evidence.  `probe-ord79-mobility-evidence.py`
already read that plan row and found 56 sealed pairs, 5 of which are the legs the plan walks,
each tagged `EXPLICIT_FROZEN_FIXTURE`.  So the open question is no longer "is the evidence
there" but "does the whole slice actually complete, and what does each of the three event
shapes the panel can send cost".  This probe answers that with return codes, three ways:

    A  TRAFFIC_DELAY grounded on the cursor  -> replan -> ACCEPT -> new ACTIVE plan
    B  WEATHER grounded on the cursor        -> replan            (what the panel's button sends)
    C  WEATHER with no grounded target       -> replan            (the failure face, must 3a)

For each failure the report keeps the status code, the `error.code`, and how many times the
call was retried, which is exactly what must 3a asks for.  The stage is rebuilt from scratch
before each variant by the product's own `demo/reset`, so no variant inherits another's state.

Isolation as usual: own throwaway database, own ephemeral port, AI off, credentials popped in
this process, and the running preview instance is never contacted.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BACKEND = Path(r"D:\moodle\_qoder_integration_20260919\backend")
TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT_DIR = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord79")
RUN_ID = os.environ.get("PROBE_RUN_ID", "ord79-m3")
DB_FILE = BACKEND / f"_{RUN_ID}.db"
REPLAN_ATTEMPTS = 3


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=TREE, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return f"<git unavailable: {exc}>"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(DB_FILE) + suffix)
        if candidate.exists():
            candidate.unlink()

    env = dict(os.environ)
    for credential in (
        "DEEPSEEK_API_KEY",
        "CITYNEXUS_AI_API_KEY",
        "CITYNEXUS_HERMES_API_KEY",
        "CITYNEXUS_HERMES_API_SERVER_KEY",
    ):
        env.pop(credential, None)
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": f"sqlite:///./{DB_FILE.name}",
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    port = free_port()
    log_path = OUT_DIR.joinpath("uvicorn.log")
    with log_path.open("wb") as handle:
        server = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=BACKEND,
            env=env,
            stdout=handle,
            stderr=handle,
        )
    base = f"http://127.0.0.1:{port}"
    report: dict[str, object] = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "tree": str(TREE),
        "head": git(["rev-parse", "HEAD"]),
        "interpreter": str(PYTHON),
        "credentials": {"DEEPSEEK_API_KEY in server env": bool(env.get("DEEPSEEK_API_KEY"))},
        "server": {"pid": server.pid, "port": port, "database": DB_FILE.name},
        "live_valhalla_url": env.get("CITYNEXUS_LIVE_VALHALLA_URL"),
        "variants": [],
    }
    steps: list[dict[str, object]] = []

    def call(name: str, method: str, path: str, **kwargs: object) -> httpx.Response:
        began = time.perf_counter()
        response = httpx.request(method, f"{base}{path}", timeout=180.0, **kwargs)
        try:
            body = response.json()
        except Exception:
            body = {"_raw": response.text[:400]}
        steps.append(
            {
                "step": name,
                "path": path,
                "status_code": response.status_code,
                "ms": round((time.perf_counter() - began) * 1000.0, 1),
                "body": body if not isinstance(body, list) else {"_list_len": len(body)},
            }
        )
        return response

    def stage(variant: str) -> dict[str, object]:
        """reset -> prepare -> start, and hand back the journey plus its cursor."""

        steps.clear()
        call(f"{variant} reset", "POST", "/api/v1/demo/reset")
        prepared = call(f"{variant} prepare", "POST", "/api/v1/demo/prepare-scenario").json()
        call(f"{variant} start", "POST", "/api/v1/demo/start-scenario")
        scene = call(f"{variant} scene", "GET", "/api/v1/demo/scene").json()
        return {
            "variant": variant,
            "journey_id": prepared.get("journey_id"),
            "plan_before": scene.get("plan_version_id"),
            "cursor_id": scene.get("current_activity_id"),
            "scene_evidence_state": scene.get("evidence_state"),
            "scene_evidence_expires_at": scene.get("evidence_expires_at"),
        }

    def replan_with_retries(variant: str, journey_id: object, event_id: object) -> list[dict]:
        attempts = []
        for index in range(REPLAN_ATTEMPTS):
            response = call(
                f"{variant} replan {index + 1}",
                "POST",
                f"/api/v1/journeys/{journey_id}/replans",
                json={"trigger_event_id": event_id, "candidate_count": 2},
                headers={"Idempotency-Key": f"{variant}-probe-{index + 1}"},
            )
            body = response.json()
            attempts.append(
                {
                    "attempt": index + 1,
                    "status_code": response.status_code,
                    "error_code": (body.get("error") or {}).get("code")
                    if isinstance(body.get("error"), dict)
                    else None,
                    "message_key": (body.get("error") or {}).get("message_key")
                    if isinstance(body.get("error"), dict)
                    else None,
                    "detail": body.get("detail"),
                    "proposal_id": body.get("id"),
                }
            )
            if response.status_code in (200, 201):
                break
            time.sleep(1.0 + index)
        return attempts

    try:
        for _ in range(120):
            try:
                if httpx.get(f"{base}/health", timeout=2.0).status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            report["fatal"] = "server never answered /health"
            return 2

        variants: list[dict[str, object]] = []

        # --- A: the full M3 slice, grounded on the cursor -------------------------------
        record = stage("A-traffic-delay")
        event = call(
            "A event",
            "POST",
            f"/api/v1/journeys/{record['journey_id']}/events",
            json={
                "event_type": "TRAFFIC_DELAY",
                "severity": "MAJOR",
                "provenance": "SIMULATED",
                "affected_activity_id": record["cursor_id"],
                "payload": {"affected_activity_id": record["cursor_id"], "delay_minutes": 25},
            },
        ).json()
        record["replan_attempts"] = replan_with_retries(
            "A", record["journey_id"], event.get("id")
        )
        proposal_id = next(
            (
                item["proposal_id"]
                for item in record["replan_attempts"]
                if item.get("proposal_id")
            ),
            None,
        )
        if proposal_id:
            accepted = call(
                "A accept",
                "POST",
                f"/api/v1/replans/{proposal_id}/accept",
                headers={"Idempotency-Key": "A-accept-1"},
            )
            accepted_body = accepted.json()
            record["accept_status_code"] = accepted.status_code
            record["accept_error"] = (
                accepted_body.get("error")
                if isinstance(accepted_body.get("error"), dict)
                else accepted_body.get("detail")
            )
            after_scene = call("A scene after accept", "GET", "/api/v1/demo/scene").json()
            record["plan_after"] = after_scene.get("plan_version_id")
            record["journey_status_after"] = after_scene.get("journey_status")
            record["cursor_after"] = after_scene.get("current_activity_id")
            record["scene_evidence_state_after"] = after_scene.get("evidence_state")
            proposal = call("A proposal readback", "GET", f"/api/v1/replans/{proposal_id}").json()
            record["proposal_status"] = proposal.get("status")
            record["proposal_hard_constraints_passed"] = proposal.get("hard_constraints_passed")
            record["proposal_locked_commitments_preserved"] = proposal.get(
                "locked_commitments_preserved"
            )
            route = call(
                "A route-evidence after accept",
                "GET",
                f"/api/v1/journeys/{record['journey_id']}/route-evidence",
                params={"proposal_id": proposal_id},
            ).json()
            record["route_evidence_after_accept"] = {
                "snapshot_id": route.get("snapshot_id"),
                "provider": route.get("provider"),
                "frozen": route.get("frozen"),
                "fallback_reason": route.get("fallback_reason"),
            }
        variants.append(record)

        # --- B: the event type the panel's button actually sends -----------------------
        record = stage("B-weather")
        event = call(
            "B event",
            "POST",
            f"/api/v1/journeys/{record['journey_id']}/events",
            json={
                "event_type": "WEATHER",
                "severity": "MAJOR",
                "provenance": "SIMULATED",
                "affected_activity_id": record["cursor_id"],
                "payload": {"affected_activity_id": record["cursor_id"]},
            },
        ).json()
        record["replan_attempts"] = replan_with_retries(
            "B", record["journey_id"], event.get("id")
        )
        variants.append(record)

        # --- C: the failure face — an event with nothing grounded onto a target --------
        record = stage("C-ungrounded")
        event = call(
            "C event",
            "POST",
            f"/api/v1/journeys/{record['journey_id']}/events",
            json={
                "event_type": "WEATHER",
                "severity": "MAJOR",
                "provenance": "SIMULATED",
                "payload": {},
            },
        ).json()
        record["replan_attempts"] = replan_with_retries(
            "C", record["journey_id"], event.get("id")
        )
        variants.append(record)

        report["variants"] = variants
        report["all_steps"] = steps
        return 0
    finally:
        OUT_DIR.joinpath("m3-slice.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
            newline="\n",
        )
        server.terminate()
        try:
            server.wait(timeout=30)
        except Exception:
            server.kill()
        print("->", OUT_DIR / "m3-slice.json")


if __name__ == "__main__":
    raise SystemExit(main())
