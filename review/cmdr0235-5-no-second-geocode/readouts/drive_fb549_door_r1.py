"""Door reading for CMDR 02:35 (5): does the second bounded geocode really disappear?

Both arms run the real product path, each on its own private backend and its own private sqlite:

  tip    = clean 5a4cdbd2 (`wt543tip`)   - the rule not yet applied
  branch = the same tip + my gate (`wt_fb549`)

The quantity the ruling is about is *how many times Nominatim is asked*, and no field in the
response carries it (`anchor_legs` records the provider legs, not the bounded fallback), so the
client's base URL is pointed at a local listener that logs every inbound request and answers the
same empty array Nominatim answers when it finds nothing. Photon, Overpass, the anchor legs and the
journey state stay the product's own: if the anchor was not grounded by a real leg answer, this
reading does not prove the ruling and says so. Three ownership receipts per backend, same batch.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid as uuidlib
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
EVID = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/evidence/fb549")
EVID.mkdir(parents=True, exist_ok=True)
FORBIDDEN = {"8000", "4781", "4782", "4783", "4785", "4786", "4787", "8693"}
# The gate is reached only when a leg grounded the city *and* the category search came back empty
# without erroring, so the default payload asks for a rare category in the smallest legal radius.
# Override through the environment; nothing else about the path is touched.
DOOR = {"query": os.environ.get("DOOR_QUERY", "gallery"),
        "radius_m": int(os.environ.get("DOOR_RADIUS", "100")),
        "limit": int(os.environ.get("DOOR_LIMIT", "8")),
        "timeout": os.environ.get("DOOR_TIMEOUT", "12"),
        "stub": os.environ.get("DOOR_STUB", "empty"),
        "tag": os.environ.get("DOOR_TAG", "answered_zero")}
# Which generation each arm runs is an operator choice, not a constant: after 02:35 (5) landed, the
# pre-gate comparison arm has to be an *older* checkout, so the trees come from the environment.
ARMS = (
    (os.environ.get("DOOR_A_LABEL", "tip"),
     pathlib.Path(os.environ.get("DOOR_A_TREE", r"D:/moodle/_qoder_seed_ord0489/wt543tip")),
     os.environ.get("DOOR_A_PORT", "8831"), os.environ.get("DOOR_A_STUB", "8835")),
    (os.environ.get("DOOR_B_LABEL", "branch"),
     pathlib.Path(os.environ.get("DOOR_B_TREE", r"D:/moodle/_qoder_seed_ord0489/wt_fb549")),
     os.environ.get("DOOR_B_PORT", "8832"), os.environ.get("DOOR_B_STUB", "8836")),
)


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def port_listening(port: str) -> list[int]:
    out = sh(["netstat", "-ano", "-p", "TCP"])
    return [int(line.split()[-1]) for line in out.splitlines()
            if f":{port} " in line and "LISTENING" in line.upper()]


def proc_info(pid: int) -> dict:
    ps = (
        "$p = Get-CimInstance Win32_Process -Filter 'ProcessId=%d'; "
        "if ($p) { [pscustomobject]@{cl=$p.CommandLine; pp=$p.ParentProcessId} "
        "| ConvertTo-Json -Compress } else { 'null' }" % pid
    )
    raw = sh(["powershell", "-NoProfile", "-Command", ps]).strip()
    try:
        return json.loads(raw) if raw and raw != "null" else {}
    except Exception:  # noqa: BLE001
        return {"parse_error": raw[:200]}


def ancestry(pid: int, depth: int = 6) -> list[int]:
    chain, current = [], pid
    for _ in range(depth):
        info = proc_info(current)
        parent = info.get("pp")
        if not isinstance(parent, int) or parent in (0, current):
            break
        chain.append(parent)
        current = parent
    return chain


# A synthetic Nominatim jsonv2 row, used only by DOOR_STUB=one to ask what the second bounded
# geocode could have supplied. It is not product data and never reaches a shared database: the arm
# that uses it runs on its own throwaway sqlite file, deleted by the driver.
_SYNTHETIC_ROW = [{
    "lat": "39.12500", "lon": "117.19000", "class": "amenity", "type": "cafe",
    "display_name": "SYNTHETIC-NOMINATIM-ROW not product data", "name": "SYNTHETIC-NOMINATIM-ROW",
    "osm_type": "node", "osm_id": 987654321, "address": {"city": "Tianjin"},
}]


class _Stub(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.server.hits.append(self.path)
        asked_limit = parse_qs(urlparse(self.path).query).get("limit", ["1"])[0]
        if DOOR["stub"] == "empty":
            body = b"[]"
        elif DOOR["stub"] == "limit_aware":
            # The anchor leg asks with limit=1 and the bounded fallback with the payload limit, so
            # answering only the wider ask keeps the synthetic row out of the *anchor* - otherwise
            # this instrument would itself decide which leg grounds the city (measured: attempt
            # supply_one_try1 did exactly that, and both arms reported nominatim_city_anchor).
            body = b"[]" if int(asked_limit) <= 1 else json.dumps(_SYNTHETIC_ROW).encode("utf-8")
        else:
            body = json.dumps(_SYNTHETIC_ROW).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        return None


def start_stub(port: str) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", int(port)), _Stub)
    srv.hits = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def call(port, method, path, body=None, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw[:1] in "[{" else raw[:300]), time.monotonic() - t0
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw), time.monotonic() - t0
        except Exception:
            return exc.code, {"raw": raw[:300]}, time.monotonic() - t0
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:200]}, time.monotonic() - t0


def run_arm(name: str, tree: pathlib.Path, port: str, stub_port: str) -> dict:
    rec: dict = {
        "arm": name, "tree": str(tree), "port": port, "stub_port": stub_port,
        "tree_head": sh(["git", "-C", str(tree), "rev-parse", "HEAD"]).strip(),
        "real_city_blob_at_head": sh(["git", "-C", str(tree), "rev-parse",
                                      "HEAD:backend/app/integrations/discovery/real_city.py"]).strip(),
        "real_city_working_bytes_sha1": sh(["git", "-C", str(tree), "hash-object",
                                            "backend/app/integrations/discovery/real_city.py"]).strip(),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    for p in (port, stub_port):
        if p in FORBIDDEN or port_listening(p):
            rec["aborted"] = f"port {p} refused or already in use"
            return rec

    db = RUN / f"_fb549door_{name}_{DOOR['tag']}.db"
    for suf in ("", "-wal", "-shm"):
        f = pathlib.Path(str(db) + suf)
        if f.exists():
            f.unlink()
    stub = start_stub(stub_port)
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db.as_posix()}",
        "CITYNEXUS_REAL_CITY_ENABLED": "true",
        "CITYNEXUS_REAL_CITY_MODE": "live",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_DEMO_MODE": "false",
        "CITYNEXUS_NOMINATIM_URL": f"http://127.0.0.1:{stub_port}",
        "CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS": str(DOOR["timeout"]),
        "PYTHONIOENCODING": "utf-8",
    })
    rec["provider_pointers"] = {
        "CITYNEXUS_NOMINATIM_URL": env["CITYNEXUS_NOMINATIM_URL"],
        "CITYNEXUS_PHOTON_BASE_URL": env.get("CITYNEXUS_PHOTON_BASE_URL", "(unset -> product default)"),
        "CITYNEXUS_OVERPASS_URL": env.get("CITYNEXUS_OVERPASS_URL", "(unset -> product default)"),
        "CITYNEXUS_PROVIDER_NETWORK_MODE": env.get("CITYNEXUS_PROVIDER_NETWORK_MODE", "(unset -> auto)"),
    }
    log_path = RUN / f"backend_fb549door_{name}_{port}_{DOOR['tag']}.log"
    log = open(log_path, "wb")
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port,
         "--app-dir", str(tree / "backend"), "--log-level", "info"],
        cwd=str(tree / "backend"), env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        ready = False
        for _ in range(90):
            if call(port, "GET", "/api/v1/health")[0] == 200:
                ready = True
                break
            time.sleep(1)
        rec["backend_ready"] = ready

        marker = f"fb549-door-{name}-{uuidlib.uuid4().hex[:12]}"
        st_m, _r, _t = call(port, "POST", "/api/v1/travelers",
                            {"display_name": marker, "email": f"{marker}@example.invalid",
                             "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            rows = con.execute("select id, display_name from travelers where display_name=?",
                               (marker,)).fetchall()
        finally:
            con.close()
        pids = port_listening(port)
        listeners = {str(pid): proc_info(pid) for pid in pids}
        rec["ownership"] = {
            "P1_marker_row_in_my_file": {
                "http_status": st_m, "marker": marker, "rows_read_from_my_db": len(rows),
                "proves": "the process answering :%s writes the sqlite file this driver created" % port,
            },
            "P2_listener_identity": {
                "port": port, "listener_pids": pids, "command_lines": listeners,
                "my_launcher_pid": proc.pid,
                "launcher_is_listener_or_ancestor": any(
                    pid == proc.pid or proc.pid in ancestry(pid) for pid in pids),
            },
            "P3_my_boot_log": {
                "path": str(log_path),
                "bytes": log_path.stat().st_size if log_path.exists() else 0,
                "names_this_port": port in log_path.read_text(encoding="utf-8", errors="replace"),
            },
        }

        st_trav, trav, _ = call(port, "POST", "/api/v1/travelers", {
            "display_name": f"回退腿二次地理编码门读数 {name}", "email": f"fb549-{name}@example.invalid",
            "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(
            hour=9, minute=0, second=0, microsecond=0)
        st_j, journey, _ = call(port, "POST", "/api/v1/journeys", {
            "traveler_id": (trav or {}).get("id"), "title": f"天津 3 天（{name}）",
            "city_code": "CN-TIANJIN", "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=3)).isoformat(),
            "budget": {"currency": "CNY", "amount_minor": 600000},
            "planning_mode": "balanced", "party_size": 2})
        jid = (journey or {}).get("id")
        rec["journey"] = {"traveler_status": st_trav, "journey_status": st_j, "id": jid}

        stub.hits.clear()
        st_d, body, elapsed = call(port, "POST", f"/api/v1/journeys/{jid}/real-city/discover",
                                   {"query": DOOR["query"], "radius_m": DOOR["radius_m"],
                                    "limit": DOOR["limit"], "mode": "live"}, timeout=300)
        status = (body or {}).get("provider_status") or {}
        legs = {}
        for item in status.get("anchor_legs") or []:
            legs[str(item.get("leg"))] = {k: item.get(k) for k in
                                          ("attempted", "answered", "http_status", "bytes", "outcome")}
        hits = list(stub.hits)
        rec["discover"] = {
            "asked": {"query": DOOR["query"], "radius_m": DOOR["radius_m"],
                      "limit": DOOR["limit"], "mode": "live",
                      "provider_timeout_seconds": DOOR["timeout"],
                      "stub_answers": DOOR["stub"]},
            "http_status": st_d, "elapsed_seconds": round(elapsed, 2),
            "mode": (body or {}).get("mode"),
            "candidates": len((body or {}).get("candidates") or []),
            "fallback_geocode_key_present": "fallback_geocode" in status,
            "fallback_geocode": status.get("fallback_geocode"),
            "anchor_source": (status.get("anchor") or {}).get("source"),
            "anchor_location": (status.get("anchor") or {}).get("location"),
            "failure_stage": status.get("failure_stage"),
            "fallback_reason": status.get("fallback_reason"),
            "overpass": status.get("overpass"),
            "anchor_legs": legs,
            "provider_status_keys": sorted(status.keys()),
        }
        rec["nominatim_inbound"] = {
            "count": len(hits),
            "requests": [{"limit": parse_qs(urlparse(h).query).get("limit", [None])[0],
                          "q": parse_qs(urlparse(h).query).get("q", [None])[0]} for h in hits],
        }
        stub.shutdown()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=25)
        except Exception:  # noqa: BLE001
            proc.kill()
        log.close()
        rec["port_after_teardown"] = {"still_listening": port_listening(port)}
    return rec


def main() -> int:
    report = {"at": datetime.now(timezone.utc).isoformat(),
              "interpreter": sh([PY, "-V"]).strip(),
              "door": dict(DOOR),
              "stub_row_declared_synthetic": _SYNTHETIC_ROW[0]["display_name"] if DOOR["stub"] == "one" else None,
              "command": "run/drive_fb549_door_r1.py", "arms": {}}
    for name, tree, port, stub_port in ARMS:
        print(f"### arm {name} ({port})")
        rec = run_arm(name, tree, port, stub_port)
        report["arms"][name] = rec
        print(json.dumps({k: rec[k] for k in rec if k in
                          ("ownership", "discover", "nominatim_inbound", "provider_pointers",
                           "journey", "aborted", "tree_head", "working_blob_sha1")},
                         ensure_ascii=False, indent=2))
    out = EVID / f"door_real_path_{DOOR['tag']}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten: {out} ({out.stat().st_size} bytes)")
    t, b = report["arms"][ARMS[0][0]], report["arms"][ARMS[1][0]]
    print("\n=== the pair ===")
    for label, path in (("nominatim asks", ("nominatim_inbound", "count")),
                        ("anchor source", ("discover", "anchor_source")),
                        ("fallback_geocode", ("discover", "fallback_geocode")),
                        ("mode", ("discover", "mode")),
                        ("discover seconds", ("discover", "elapsed_seconds"))):
        def dig(rec):
            for part in path:
                rec = rec.get(part) if isinstance(rec, dict) else None
            return rec
        print(f"  {label:18s} tip={dig(t)!r}  branch={dig(b)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
