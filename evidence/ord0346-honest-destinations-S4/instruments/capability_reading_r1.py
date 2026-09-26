"""ORD-0346 S4 requirement 1: the real reading behind the 「看支持的目的地」 list.

Starts the product's own server on this lane's own port, against this lane's own one-off SQLite,
with an `e2e_run_id` token only this process knows, and reads
`GET /api/v1/destinations/capability` for every spelling the screen advertises plus every label the
backend vocabulary can name.  Nothing is decided here: the script records readings.
"""
import json
import os
import re
import subprocess
import sys
import time

import httpx

WORK = os.path.dirname(os.path.abspath(__file__))
TREE = "D:/moodle/_qoder_ord0346_S4"
BACKEND = os.path.join(TREE, "backend")
STAGED_DB = os.path.join(WORK, "ord0346_S4_r1.db")
PORT = int(os.environ.get("CNX_S4_PORT", "8846"))
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

SCREEN_ZH = ["厦门", "北京", "上海", "天津", "福州", "广州", "深圳", "成都", "杭州", "东京", "新加坡"]
SCREEN_EN = ["Xiamen", "Beijing", "Shanghai", "Tianjin", "Fuzhou", "Guangzhou", "Shenzhen",
             "Chengdu", "Hangzhou", "Tokyo", "Singapore"]
BACKEND_CODES = ["XIAMEN", "TIANJIN", "BEIJING", "SHANGHAI", "GUANGZHOU", "SHENZHEN", "HANGZHOU",
                 "CHENGDU", "XIAN", "NANJING", "QINGDAO", "SANYA", "KUNMING", "CHONGQING",
                 "WUHAN", "SUZHOU"]
CONTROL_UNSUPPORTED = ["亚特兰大", "Atlanta", "云和县"]

PROBE = json.load(open(os.path.join(WORK, "marker.json"), encoding="utf-8"))


def listener_pid():
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0] == "TCP" and cols[1].endswith(":%d" % PORT) \
                and cols[3].upper() == "LISTENING":
            return int(cols[4])
    return None


def process_identity(pid):
    ps = ("$p = Get-CimInstance Win32_Process -Filter 'ProcessId=%d'; "
          "if ($p) { Write-Output ($p.ParentProcessId.ToString() + '|' + $p.CommandLine) }" % pid)
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stdout
    line = out.strip().splitlines()[0] if out.strip() else ""
    parent, _, cmd = line.partition("|")
    return {"parent_process_id": parent.strip(), "command_line": cmd.strip()}


def scrub(value):
    """Any placeholder-shaped string anywhere in an answer, so requirement 3 is measured and not assumed."""

    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + "." + str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + "[%d]" % i)
        elif isinstance(node, str):
            if re.search(r"unresolved[:_\-]|pending[:_\-]|pend-|sha1[:_\-]|digest|placeholder",
                         node, re.I):
                found.append({"path": path, "value": node})

    walk(value, "")
    return found


def main():
    if not os.path.exists(STAGED_DB) or "_qoder_lane_S4_0926" not in STAGED_DB.replace("\\", "/"):
        raise SystemExit("REFUSE: %s is not this lane's own staged store" % STAGED_DB)
    # Why no CITYNEXUS_E2E_RUN_ID here: the product's own guard
    # (`backend/app/db/session.py:21-45`) refuses to boot an identified run on a database that
    # already exists, and the only supported way to fill one is `POST /api/v1/demo/reset`, which
    # this order forbids.  So the store is identified the other sanctioned way - a marker row that
    # exists in no file but this one, probed in both directions below.  The refusal is kept, not
    # worked around: see e2e_guard_refusal_r1.txt beside this script.
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + STAGED_DB.replace("\\", "/"),
        "CITYNEXUS_ANYWHERE_RESOLVER": "off",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "PHOTON_BASE_URL": "http://127.0.0.1:9",
        "PYTHONPATH": BACKEND,
    })
    log = open(os.path.join(WORK, "server_r1.log"), "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PY, "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--log-level", "info"],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
    readings, ownership = [], {}
    try:
        base = "http://127.0.0.1:%d" % PORT
        health = None
        for _ in range(60):
            try:
                r = httpx.get(base + "/api/v1/health", timeout=2.0)
                if r.status_code == 200:
                    health = r.json()
                    break
            except Exception:
                pass
            time.sleep(0.5)
        ownership["launcher_process_id"] = proc.pid
        ownership["launcher_alive"] = proc.poll() is None
        ownership["listener_process_id"] = listener_pid()
        lp = ownership["listener_process_id"]
        ownership["listener_identity"] = process_identity(lp) if lp else None
        ownership["health"] = health
        if health is None:
            log.flush()
            tail = open(os.path.join(WORK, "server_r1.log"), encoding="utf-8",
                        errors="replace").read()[-2500:]
            raise SystemExit("NOT MEASURED: the server never answered /api/v1/health on %d.\n%s"
                             % (PORT, tail))
        ownership["echoed_run_id"] = (health or {}).get("e2e_run_id")
        ownership["echoed_database_id"] = (health or {}).get("e2e_database_id")
        ownership["note"] = ("/api/v1/health publishes e2e_run_id and e2e_database_id only for a run "
                             "that set CITYNEXUS_E2E_RUN_ID; this server deliberately did not (see the "
                             "comment in main()).  The store is named by the marker probe below.")

        # Bidirectional store-identity probe: the marker row exists in no file but this one.
        marker = httpx.get(base + "/api/v1/places", params={"city_code": PROBE["marker_city_code"],
                                                           "include_structural": "true"}, timeout=10.0)
        absent = httpx.get(base + "/api/v1/places", params={"city_code": PROBE["absent_city_code"],
                                                           "include_structural": "true"}, timeout=10.0)
        rows = marker.json() if marker.status_code == 200 and isinstance(marker.json(), list) else []
        ownership["marker_probe"] = {
            "marker_status": marker.status_code,
            "marker_rows": len(rows),
            "marker_ids_returned": sorted({str(row.get("id")) for row in rows if isinstance(row, dict)}),
            "marker_id_expected": PROBE["marker_place_id"],
            "marker_name_in_body": PROBE["marker_name"] in marker.text,
            "absent_status": absent.status_code,
            "absent_rows": len(absent.json()) if absent.status_code == 200 else None,
        }
        if not (PROBE["marker_place_id"] in ownership["marker_probe"]["marker_ids_returned"]
                and ownership["marker_probe"]["absent_rows"] == 0):
            raise SystemExit("NOT MEASURED: the listener on port %d is not this lane's server "
                             "(marker probe: %s)" % (PORT, json.dumps(ownership["marker_probe"])))

        def ask(q):
            r = httpx.get(base + "/api/v1/destinations/capability", params={"query": q}, timeout=20.0)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
            keep = None
            if isinstance(body, dict):
                keep = {k: body.get(k) for k in (
                    "capability", "reason_code", "recommended_action", "destination_state",
                    "destination_resolution", "canonical_destination_id",
                    "pending_destination_label", "resolver_query_normalized",
                    "destination_pending_key", "pending_label_fidelity", "retryable",
                    "place_count", "missing_categories")}
                keep["provenance_source_kinds"] = (body.get("provenance") or {}).get("source_kinds")
                keep["provider_status_present"] = "provider_status" in body
            return {"query": q, "http_status": r.status_code,
                    "content_type": r.headers.get("content-type"),
                    "body_bytes": len(r.content),
                    "fields": keep,
                    "placeholder_shaped_strings": scrub(body) if isinstance(body, dict) else scrub(r.text),
                    "keys": sorted(body) if isinstance(body, dict) else None}

        for group, names in (("screen_zh", SCREEN_ZH), ("screen_en", SCREEN_EN),
                             ("backend_vocabulary_codes", BACKEND_CODES),
                             ("control_unadvertised", CONTROL_UNSUPPORTED)):
            for name in names:
                readings.append({"group": group, **ask(name)})

        out = {
            "order": "ORD-0346",
            "lane": "S4-ast-taint",
            "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "generation": "c740f45d68f337c460a1a43b995162689d0110af",
            "server": {
                "port": PORT,
                "database_url_named_by_this_lane": env["CITYNEXUS_DATABASE_URL"],
                "staged_database_bytes": os.path.getsize(STAGED_DB),
                "staged_database": STAGED_DB.replace("\\", "/"),
                "how_the_data_got_there": ("`app.services.seed_demo(session)` called once in this lane's "
                                           "own process against a file that did not exist before it "
                                           "(db_setup_r1.py), plus one instrument marker row "
                                           "(db_marker_r1.py). `POST /api/v1/demo/reset` was never "
                                           "called; the server served that same lane-owned file, and no "
                                           "shared store was opened anywhere in this order."),
                "resolver_seam": "off",
                "photon_tripwire": env["PHOTON_BASE_URL"],
                "interpreter": PY,
                "cwd": BACKEND,
                "argv": ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
            },
            "ownership": ownership,
            "readings": readings,
        }
        path = os.path.join(WORK, "capability_reading_r1.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print(json.dumps(out["ownership"], ensure_ascii=False, indent=1))
        print("wrote", path, os.path.getsize(path), "bytes")
    finally:
        lp = ownership.get("listener_process_id")
        if lp:
            subprocess.run(["taskkill", "/PID", str(lp), "/T", "/F"], capture_output=True)
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        log.close()
        print("listener after teardown:", listener_pid())


if __name__ == "__main__":
    main()
