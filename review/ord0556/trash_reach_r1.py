"""ORD-0556 follow-up, sixth leg: reach /v8/trash without a heading gate and record what is on screen.

Two claims get tested here:
 1. the screen was NOT unreachable because of product state -- it was unreachable *to my reader*, whose
    readiness waits for an h1/h2 and this panel paints its title only as a `v8-kicker` span;
 2. whether the panel is actually mounted and which branch of its state machine is on screen (no viewer /
    loading / empty / read-failed / rows), with the server calls it makes.

Own lane stack on my own ports over a copy of the commander's canary store; the source store is opened
never, copied, then hash-checked. Zero product bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
FRONTEND = ROOT / "frontend"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
OUT_DIR = ROOT / "review/ord0556/readouts"
PROBE = ROOT / "review/ord0556/trash_probe_r1.js"
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_BACKEND_PORT", "4951"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_FRONTEND_PORT", "4956"))
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
STORE = DATA / f"_trashprobe_{RUN}.db"
CASES = [("/v8/trash", "en"), ("/v8/trash", "zh"), ("/v8/bookings", "en")]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    # Column form is `TCP  local  remote  STATE  PID`: the state is column 3 and the local address is
    # column 1. The first version of this helper looked for a line ENDING in LISTENING and therefore
    # never saw a listener, which made a healthy stack read as "vite never listened".
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout or ""
    found = set()
    for ln in out.split("\n"):
        cols = ln.split()
        if len(cols) >= 4 and cols[0] == "TCP" and cols[3].upper() == "LISTENING" \
                and cols[1].endswith(f":{port}"):
            found.add(cols[-1])
    return sorted(found)


def http(method: str, url: str, timeout: int = 20):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main() -> int:
    if listeners(BACKEND_PORT) or listeners(FRONTEND_PORT):
        raise SystemExit("ABORT my ports are held")
    if not SOURCE_CANARY.is_file():
        raise SystemExit("ABORT canary source missing")
    source_before = sha(SOURCE_CANARY)
    STORE.write_bytes(SOURCE_CANARY.read_bytes())
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = "*"
    env["PYTHONIOENCODING"] = "utf-8"
    # The env recipe is copied verbatim from the runner that demonstrably boots this tree
    # (review/ord0556/route_sweep_dev_r1.py:110-115) -- guessing variable names here is how the first
    # run of this leg booted nothing.
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{STORE.as_posix()}"
    env["CITYNEXUS_DEMO_MODE"] = "true"

    b_log = (DATA / f"uvicorn_{BACKEND_PORT}_{RUN}.log").open("w", encoding="utf-8", errors="replace")
    backend = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                "--port", str(BACKEND_PORT), "--log-level", "warning"],
                               cwd=str(ROOT / "backend"), env=env, stdout=b_log, stderr=subprocess.STDOUT)
    vite_env = dict(env)
    vite_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    v_log = open(DATA / f"vite_{FRONTEND_PORT}_{RUN}.log", "w", encoding="utf-8")
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1",
                             "--port", str(FRONTEND_PORT), "--strictPort"],
                            cwd=str(FRONTEND), env=vite_env, stdout=v_log, stderr=subprocess.STDOUT)
    doc = {"generation": {"run": RUN, "backend_port": BACKEND_PORT, "frontend_port": FRONTEND_PORT,
                          "store": "copy of commander canary, opened never",
                          "canary_sha_before": source_before,
                          "tree_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                                      capture_output=True, text=True).stdout.strip(),
                          "probe": str(PROBE.relative_to(ROOT)).replace("\\", "/")},
           "cases": [], "verdict": None}
    ready = False
    listening = False
    try:
        for _ in range(120):
            try:
                if http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1.0)
        if not ready:
            doc["aborted"] = "backend never answered health; see " + str(DATA / f"uvicorn_{BACKEND_PORT}_{RUN}.log")
        else:
            for _ in range(180):
                if listeners(FRONTEND_PORT):
                    listening = True
                    break
                time.sleep(1.0)
            if not listening:
                doc["aborted"] = "vite never listened; see " + str(DATA / f"vite_{FRONTEND_PORT}_{RUN}.log")
        if doc.get("aborted") is None:
            for route, locale in CASES:
                    out_file = DATA / f"trashprobe_{route.rsplit('/', 1)[-1]}_{locale}_{RUN}.json"
                    r = subprocess.run(["node", str(PROBE), f"http://127.0.0.1:{FRONTEND_PORT}/",
                                        str(out_file), locale, route],
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", timeout=180)
                    if not out_file.is_file():
                        doc["cases"].append({"route": route, "locale": locale,
                                             "aborted": (r.stdout or r.stderr or "")[:200]})
                        continue
                    row = json.loads(out_file.read_text(encoding="utf-8"))
                    f = row["facts"]
                    # Negative control, bolted in because the first run of this leg silently rendered the
                    # hub for all three cases: the painted address must BE the route asked for.
                    painted = f["url"].split("://", 1)[-1].split("/", 1)[-1]
                    if "/" + painted.lstrip("/") != route:
                        doc["cases"].append({"route": route, "locale": locale,
                                             "aborted": f"navigated elsewhere: painted /{painted}"})
                        continue
                    heading_gate = f["h1_count"] + f["h2_count"]
                    doc["cases"].append({
                        "route": route, "locale": locale,
                        "url_read": f["url"],
                        "route_matches_painted_url": True,
                        "h1_count": f["h1_count"], "h2_count": f["h2_count"],
                        "would_my_reader_have_become_ready": heading_gate > 0,
                        "kicker_text": f["kicker_text"],
                        "testids_present": [k for k, v in f["present"].items() if v],
                        "body_chars": f["body_chars"],
                        "body_head": f["inner_head"][:200],
                        "caps_words": f["caps_words"],
                        "api_calls": f["api_calls"],
                        "page_errors": f["page_errors"],
                        "wall_ms": f["wall_ms"],
                    })
                    print(json.dumps({"case": f"{route} {locale}", "url_painted": painted, "h1h2": heading_gate,
                                      "testids": doc["cases"][-1]["testids_present"],
                                      "chars": f["body_chars"]}), flush=True)
    finally:
        for p in (vite, backend):
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(3.0)
        for p in (vite, backend):
            if p.poll() is None:
                p.kill()
        v_log.close()
        b_log.close()
        doc["teardown"] = {"my_ports_listening_after": {str(BACKEND_PORT): sorted(listeners(BACKEND_PORT)),
                                                        str(FRONTEND_PORT): sorted(listeners(FRONTEND_PORT))},
                           "canary_source_sha256_after": sha(SOURCE_CANARY),
                           "canary_source_untouched": sha(SOURCE_CANARY) == source_before}
        for f in (STORE, pathlib.Path(str(STORE) + "-wal"), pathlib.Path(str(STORE) + "-shm")):
            f.unlink(missing_ok=True)
        # logs stay on disk: a run that aborts is worth less than a run whose log can be read
        for f in DATA.glob(f"trashprobe_*_{RUN}.json"):
            f.unlink(missing_ok=True)

    read = len(doc["cases"])
    # A case that aborted inside the probe contributes a row of shape {"route","locale","aborted"} only;
    # the earlier version indexed the reading fields on every row and died with a KeyError before it
    # could write the receipt. Abort rows are counted, they are not read.
    full = [c for c in doc["cases"] if "aborted" not in c]
    aborted = [c for c in doc["cases"] if "aborted" in c]
    trash = [c for c in full if c["route"] == "/v8/trash"]
    doc["counts"] = {"cases_attempted": read, "cases": len(CASES),
                     "cases_aborted": len(aborted),
                     "trash_cases": len(trash),
                     "trash_without_heading": len([c for c in trash if not c["would_my_reader_have_become_ready"]]),
                     "trash_panel_mounted": len([c for c in trash if "journey-trash-panel" in c["testids_present"]]),
                     "page_errors_total": sum(len(c["page_errors"]) for c in full)}
    if doc.get("aborted"):
        doc["verdict"] = "ABORT_STACK " + doc["aborted"]
    else:
        doc["verdict"] = ("TRASH_READ " if len(aborted) == 0 else "TRASH_PARTIAL ") + \
                         f"{doc['counts']['trash_without_heading']} of {len(trash)} trash reads had no heading element"
    doc["aborted_detail"] = aborted

    out = OUT_DIR / f"trash_reach_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"receipt": out.name, "verdict": doc["verdict"], "counts": doc["counts"],
                      "teardown_ok": doc["teardown"]["canary_source_untouched"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
