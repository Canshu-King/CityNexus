"""ORD-0432 item 3: two rendered arms (zh / en) of the new disruption summary.

Everything the browser reads travels through the candidate bundle and my own lane backend:

  lane sqlite (seeded copy) -> uvicorn on :8621 -> `vite preview` on :4821 proxying /api to 8621
                             -> the r3 instrument drives Chrome at /v8/live in both locales.

Three ownership proofs run before the browser is opened, because a 200 on my port can be another
lane's process:
  P1 the MAJOR event I POSTed is readable through the preview's own /api proxy,
  P2 the asset the served index.html names hashes to the bytes on my disk,
  P3 `/demo/scene` names the journey I seeded, so the sealed-demo entry lands on my journey.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
BUILD = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\build\frontend")
DIST = BUILD / "_dist_ord0432"
OUT = LANE / "ord0432_two_arm"
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
NODE = "node"
JID = "22222222-2222-4222-8222-222222222222"
EXPECT = ["有重大变动没处理", "Major disruption open", "服务器摘要：需要复核", "Server summary: review needed",
          "服务器摘要：这台设备还没读到", "Server summary: not read by this device yet"]


def free_port() -> int:
    """Ask the OS for an unused port: a chosen "lane port" can already be somebody else's.
    Measured on the first run of this script - the commander's own static proxy held :4821,
    `--strictPort` lost the race, and `wait()` reported a server that was not mine."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


BACKEND_PORT = int(os.environ.get("ORD0432_BACKEND_PORT") or free_port())
PREVIEW_PORT = int(os.environ.get("ORD0432_PREVIEW_PORT") or free_port())
db = LANE / f"_ord0432_screen_{BACKEND_PORT}.db"
BE = f"http://127.0.0.1:{BACKEND_PORT}"
FE = f"http://127.0.0.1:{PREVIEW_PORT}"


def listener_pids(port: int) -> list[str]:
    raw = subprocess.run(["netstat", "-ano"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stdout or ""
    return sorted({line.split()[-1] for line in raw.splitlines()
                   if f":{port} " in line and "LISTENING" in line})



def popen(cmd, cwd, env, log):
    return subprocess.Popen(cmd, cwd=str(cwd), env=env,
                            stdout=log.open("w", encoding="utf-8"), stderr=subprocess.STDOUT)


def wait(url, rounds=90):
    for _ in range(rounds):
        try:
            if httpx.get(url, timeout=4).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def gate(name: str, ok: bool, detail) -> None:
    print(f"GATE {name}: {'ok' if ok else 'REFUSED'} {json.dumps(detail, ensure_ascii=False)[:300]}")
    if not ok:
        raise RuntimeError(f"ownership gate refused: {name}")


def _arms(body: dict) -> dict:
    arms = {}
    for arm_name in ("zh", "en"):
        arm = body[arm_name]
        arms[arm_name] = {"entry_used": arm["entry_used"], "reached_route": arm["reached_route"],
                          "on_requested_route": arm["on_requested_route"],
                          "locale_read": arm["locale_read"], "leaf_count": arm["leaf_count"],
                          "ascii_prose_count": arm["ascii_prose_count"],
                          "expect": {x["text"]: x["on_screen"] for x in arm["expect"]}}
    return arms


def main() -> int:
    report: dict = {"backend_port": BACKEND_PORT, "preview_port": PREVIEW_PORT, "db": str(db)}
    try:
        _run(report)
    except Exception as exc:  # a refused gate still has to leave a receipt
        report["fatal"] = f"{type(exc).__name__}: {exc}"
    path = OUT / "ORD0432_TWO_ARM.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in report if k != "arms"}, ensure_ascii=False, indent=1)[:2200])
    if "arms" in report:
        print("ARMS", json.dumps(report["arms"], ensure_ascii=False)[:900])
    print("WROTE", path)
    return 0 if report.get("verdict_two_arm_rendered_reading") else 1


def _run(report: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    env_db = {**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
               "CITYNEXUS_DEMO_MODE": "true"}
    subprocess.run([str(PY), str(LANE / "seed_lane_db.py")], check=True, capture_output=True,
                   text=True, env={**env_db, "LANE_BACKEND_ROOT": str(TREE / "backend")})
    backend = popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                     "--port", str(BACKEND_PORT)], TREE / "backend",
                    {**env_db, "PYTHONPATH": "."}, OUT / "_backend.log")
    preview = None
    try:
        healthy = wait(f"{BE}/api/v1/health")
        pids = listener_pids(BACKEND_PORT)
        report["P0_backend_listener"] = {"healthy": healthy, "netstat_pids": pids,
                                         "my_pid": str(backend.pid)}
        gate("P0_backend_answered", healthy, report["P0_backend_listener"])
        with httpx.Client(base_url=BE, timeout=60) as c:
            gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
            if gen.status_code == 201 and gen.json():
                c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
                c.post(f"/api/v1/journeys/{JID}/start")
            acts = c.get(f"/api/v1/journeys/{JID}/plans").json()
            active = next((p for p in acts if p.get("status") == "ACTIVE"), None)
            last = max(active["activities"], key=lambda a: a["end_at"]) if active else None
            ev = c.post(f"/api/v1/journeys/{JID}/events", json={
                "event_type": "CLOSURE", "severity": "MAJOR",
                "affected_activity_id": last["id"] if last else None,
                "provenance": "SIMULATED",
                "payload": {"reason": "ORD-0432 two-arm reading"}})
            report["event"] = {"http": ev.status_code, "id": (ev.json() or {}).get("id")}
            twin = c.get(f"/api/v1/journeys/{JID}/twin").json()
            env_block = twin["context"]["feasibility_envelope"]
            report["server_truth_via_backend"] = {"robust": env_block["robust"],
                                                 "risk_reason_codes": env_block["risk_reason_codes"],
                                                 "latest_event_id": twin["latest_event_id"]}
        conn = sqlite3.connect(db)
        mine = [row[0] for row in conn.execute(
            "select id from events where journey_id=? and severity='MAJOR'", (JID,)).fetchall()]
        conn.close()
        report["P0b_marker_row_is_in_my_file"] = {"posted_id": report["event"]["id"],
                                                 "maJOR_rows_in_my_db": mine,
                                                 "in_my_file": report["event"]["id"] in mine}

        preview = popen([NODE, str(BUILD / "node_modules/vite/bin/vite.js"), "preview",
                         "--host", "127.0.0.1", "--outDir", str(DIST), "--port", str(PREVIEW_PORT), "--strictPort"],
                        BUILD, {**os.environ, "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)},
                        OUT / "_preview.log")
        alive = wait(f"{FE}/")
        pids = listener_pids(PREVIEW_PORT)
        report["P4_preview_listener"] = {"answered": alive, "netstat_pids": pids,
                                         "my_pid": str(preview.pid) if preview else None}
        gate("P4_preview_port_answered", alive, report["P4_preview_listener"])

        index = httpx.get(f"{FE}/", timeout=30).text
        asset = re.search(r'/assets/(index-[A-Za-z0-9_-]+\.js)', index)
        gate("P5_served_index_names_an_asset", bool(asset), {"index_head": index[:200]})
        name = asset.group(1)
        served = httpx.get(f"{FE}/assets/{name}", timeout=60).content
        on_disk = DIST / "assets" / name
        report["P2_preview_serves_my_bytes"] = {
            "asset": name, "asset_exists_in_my_dist": on_disk.is_file(),
            "served_sha1": hashlib.sha1(served).hexdigest(),
            "disk_sha1": hashlib.sha1(on_disk.read_bytes()).hexdigest() if on_disk.is_file() else None}
        gate("P2_preview_serves_my_bytes", on_disk.is_file()
             and report["P2_preview_serves_my_bytes"]["served_sha1"]
             == report["P2_preview_serves_my_bytes"]["disk_sha1"],
             report["P2_preview_serves_my_bytes"])

        via_proxy = httpx.get(f"{FE}/api/v1/journeys/{JID}/events", timeout=60).json()
        report["P1_event_readable_through_preview"] = (
            report["event"]["id"] in [item["id"] for item in via_proxy])
        gate("P1_event_readable_through_preview", report["P1_event_readable_through_preview"],
             {"event_id": report["event"]["id"]})
        scene = httpx.get(f"{FE}/api/v1/demo/scene", timeout=60).json()
        report["P3_scene_names_my_journey"] = {"scene_journey_id": scene.get("journey_id"),
                                             "demo_mode": scene.get("demo_mode"),
                                             "is_lane_journey": scene.get("journey_id") == JID}

        expect_path = OUT / "_expect.json"
        expect_path.write_text(json.dumps(EXPECT, ensure_ascii=False), encoding="utf-8", newline="\n")
        scan = subprocess.run(
            [NODE, str(LANE / "_untranslated_scan_r3.js"), FE, "live", str(OUT) + "/",
             str(expect_path)],
            cwd=str(LANE), capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "NODE_PATH": str(BUILD / "node_modules")})
        report["scan_stdout"] = (scan.stdout or "")[-1800:]
        report["scan_stderr"] = (scan.stderr or "")[-600:]
        report["scan_exit"] = scan.returncode
        receipt = OUT / "untranslated_live_r3.json"
        if receipt.exists():
            body = json.loads(receipt.read_text(encoding="utf-8"))
            arms = _arms(body)
            report["arms"] = arms
            report["verdict_two_arm_rendered_reading"] = bool(
                body.get("arms_comparable")
                and arms["zh"]["expect"].get("有重大变动没处理") is True
                and arms["zh"]["expect"].get("Major disruption open") is False
                and arms["en"]["expect"].get("Major disruption open") is True
                and arms["en"]["expect"].get("有重大变动没处理") is False)
            report["instrument_verdict"] = body.get("verdict")
    finally:
        for proc in (preview, backend):
            if proc is None:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except Exception:
                proc.kill()

    path = OUT / "ORD0432_TWO_ARM.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:3500])
    print("WROTE", path)
    return 0 if report.get("verdict_two_arm_rendered_reading") else 1


if __name__ == "__main__":
    raise SystemExit(main())
