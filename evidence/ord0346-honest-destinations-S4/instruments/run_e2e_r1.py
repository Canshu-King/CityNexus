"""ORD-0346 S4: run the panel spec against a backend this lane owns.

Starts uvicorn on this lane's port with this lane's one-off SQLite, proves the listener is the
process this script launched *and* is reading this lane's file (a marker row nobody else holds),
and only then starts Playwright.  A reading taken against a borrowed server would be worthless, so
the probe is a gate here, not a note: if it fails, nothing runs.
"""
import json
import os
import subprocess
import sys
import time

import httpx

WORK = os.path.dirname(os.path.abspath(__file__))
TREE = "D:/moodle/_qoder_ord0346_S4"
BACKEND = os.path.join(TREE, "backend")
FRONTEND = os.path.join(TREE, "frontend")
DB = os.path.join(WORK, "ord0346_S4_r1.db")
PROBE = json.load(open(os.path.join(WORK, "marker.json"), encoding="utf-8"))
BACKEND_PORT = int(os.environ.get("CNX_S4_PORT", "8851"))
FRONTEND_PORT = int(os.environ.get("CNX_S4_FE_PORT", "4196"))
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = "node"


def listener_pid(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0] == "TCP" and cols[1].endswith(":%d" % port) \
                and cols[3].upper() == "LISTENING":
            return int(cols[4])
    return None


def main():
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
        "CITYNEXUS_ANYWHERE_RESOLVER": "off",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "PHOTON_BASE_URL": "http://127.0.0.1:9",
        "PYTHONPATH": BACKEND,
    })
    for port in (BACKEND_PORT, FRONTEND_PORT):
        if listener_pid(port):
            raise SystemExit("REFUSE: port %d is already taken; this lane will not borrow a server" % port)
    log = open(os.path.join(WORK, "server_e2e.log"), "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PY, "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(BACKEND_PORT), "--log-level", "warning"],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
    proofs = {"launcher_process_id": proc.pid, "backend_port": BACKEND_PORT,
              "frontend_port": FRONTEND_PORT,
              "database_url": env["CITYNEXUS_DATABASE_URL"]}
    try:
        for _ in range(80):
            try:
                if httpx.get("http://127.0.0.1:%d/api/v1/health" % BACKEND_PORT, timeout=2).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        proofs["listener_process_id"] = listener_pid(BACKEND_PORT)
        marker = httpx.get("http://127.0.0.1:%d/api/v1/places" % BACKEND_PORT,
                          params={"city_code": PROBE["marker_city_code"], "include_structural": "true"},
                          timeout=10.0)
        absent = httpx.get("http://127.0.0.1:%d/api/v1/places" % BACKEND_PORT,
                           params={"city_code": PROBE["absent_city_code"]}, timeout=10.0)
        ids = sorted({str(row.get("id")) for row in marker.json()}) if marker.status_code == 200 else []
        proofs["store_identity"] = {"marker_rows": len(ids), "marker_id_expected": PROBE["marker_place_id"],
                                    "marker_id_returned": ids,
                                    "absent_rows": len(absent.json()) if absent.status_code == 200 else None}
        if PROBE["marker_place_id"] not in ids or proofs["store_identity"]["absent_rows"] != 0:
            raise SystemExit("NOT MEASURED: the listener on %d is not this lane's server: %s"
                             % (BACKEND_PORT, json.dumps(proofs)))
        run_env = dict(env)
        run_env.update({
            "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT),
            "CITYNEXUS_ORD0346_PORT": str(FRONTEND_PORT),
            "CITYNEXUS_ORD0346_REPORT": os.path.join(WORK, "report-ord0346.json").replace("\\", "/"),
            "CITYNEXUS_EVIDENCE_DIR": os.environ.get("CNX_S4_EVIDENCE")
            or os.path.join(WORK, "evidence").replace("\\", "/"),
        })
        # The lane also re-runs the two wizard gates this panel belongs to; see the config comment.
        if os.environ.get("CNX_S4_MATCH"):
            run_env["CITYNEXUS_ORD0346_MATCH"] = os.environ["CNX_S4_MATCH"]
        if os.environ.get("CNX_S4_REPORT"):
            run_env["CITYNEXUS_ORD0346_REPORT"] = os.path.join(WORK, os.environ["CNX_S4_REPORT"])
        started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        spec = subprocess.run(
            [NODE, os.path.join(FRONTEND, "node_modules", "@playwright", "test", "cli.js"),
             "test", "-c", "playwright.ord0346-S4.config.ts"],
            cwd=FRONTEND, env=run_env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=900)
        out = spec.stdout + spec.stderr
        proofs["spec_exit_code"] = spec.returncode
        proofs["spec_output_tail"] = out[-4000:]
        proofs["started_at_local"] = started
        proofs["finished_at_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        print(out[-6000:])
    finally:
        subprocess.run(["taskkill", "/PID", str(proofs.get("listener_process_id") or proc.pid),
                        "/T", "/F"], capture_output=True)
        log.close()
        proofs["listener_after_teardown"] = listener_pid(BACKEND_PORT)
        # Timestamped: a second arm of the same order must not overwrite the first one's proofs.
        proofs["specs_matched"] = os.environ.get("CNX_S4_MATCH", "default (qoder-ord0346-*)")
        path = os.path.join(WORK, "e2e_run_proofs_%s.json" % time.strftime("%H%M%S"))
        json.dump(proofs, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("proofs ->", path)
        print("backend listener after teardown:", proofs["listener_after_teardown"])


if __name__ == "__main__":
    main()
