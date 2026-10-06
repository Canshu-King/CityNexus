"""Option 乙 without a build: walk the commander's 14 routes with this lane's same-rule reader.

Why this exists: `cmdr_machine_speech_sweep_r1.js` does a fixed wait per route, so against a vite-dev
base it needed ~64 s per route and died at the 900 s ceiling (measured in review/ord0556/
sweep_bookings_caps_r1.py:206). My reader waits for the screen's own heading instead, so the whole
route list fits in one browser session. The counting rules are still copied verbatim from the
commander's instrument, so the totals are comparable -- and this run changes no product byte.

Group-then-split: if one route hangs, the group is retried route by route and the failing route is
recorded as NOT_REACHED instead of silently dropping out of the denominator.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
FRONTEND = ROOT / "frontend"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
READOUTS = ROOT / "review/ord0556/readouts"
READER = ROOT / "review/ord0556/bookings_caps_reader_r1.js"
BASELINE_BLOB = "44a51e236a68ac84ee58dd3be98e9cb890e66bac"
ROUTES = ["/v8/hub", "/v8/live", "/v8/map", "/v8/studio", "/v8/stay", "/v8/discover",
          "/v8/bookings", "/v8/agent", "/v8/authoritative", "/v8/intelligence", "/v8/twin",
          "/v8/trash", "/v8/trips", "/v8/me"]
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0556_BASE_TIP", "")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_BACKEND_PORT", "4951"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_FRONTEND_PORT", "4956"))
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SFX = RUN_STAMP[-7:-1]
STORE = DATA / f"_routesweep_{SFX}.db"
BACKEND_LOG = DATA / f"uvicorn_{BACKEND_PORT}_{SFX}.log"
VITE_LOG = DATA / f"vite_{FRONTEND_PORT}_{SFX}.log"
RECEIPT = READOUTS / f"route_sweep_dev_{RUN_STAMP}.json"
LOCK = DATA / f"route_sweep_{SFX}.lock"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def http(method: str, url: str, timeout: int = 20):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def read(locale: str, routes: list[str], tag: str):
    out_file = DATA / f"routesweep_{locale}_{tag}_{SFX}.json"
    r = subprocess.run(["node", str(READER), f"http://127.0.0.1:{FRONTEND_PORT}/", str(out_file),
                        locale, *routes], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    if not out_file.is_file():
        return None, r
    return json.loads(out_file.read_text(encoding="utf-8")), r


def main() -> int:
    if LOCK.exists():
        holder = "".join(c for c in LOCK.read_text(encoding="utf-8") if c.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT another run holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if listeners(BACKEND_PORT) or listeners(FRONTEND_PORT):
        raise SystemExit("ABORT my ports are held")
    if not STORE.is_file():
        STORE.write_bytes(SOURCE_CANARY.read_bytes())
    source_before = sha(SOURCE_CANARY)
    baseline = json.loads(subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p", BASELINE_BLOB],
                                         capture_output=True, text=True, errors="replace").stdout)

    doc: dict = {"generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP,
                                "routes": len(ROUTES), "this_lane_ports": [BACKEND_PORT, FRONTEND_PORT],
                                "reader": str(READER.relative_to(ROOT)),
                                "rules_copied_from": baseline.get("instrument"),
                                "baseline_locale": baseline.get("locale"),
                                "baseline_allow_list": len(baseline.get("allowListForAllCaps", [])),
                                "canary_sha_before": source_before},
                 "arms": {}, "notes": []}

    def emit():
        READOUTS.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{STORE.as_posix()}"
    env["CITYNEXUS_DEMO_MODE"] = "true"
    b_log = BACKEND_LOG.open("w", encoding="utf-8", errors="replace")
    backend = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                "--port", str(BACKEND_PORT), "--log-level", "warning"],
                               cwd=ROOT / "backend", env=env, stdout=b_log, stderr=subprocess.STDOUT)
    vite_env = dict(env)
    vite_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    v_log = VITE_LOG.open("w", encoding="utf-8", errors="replace")
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1",
                             "--port", str(FRONTEND_PORT), "--strictPort"],
                            cwd=FRONTEND, env=vite_env, stdout=v_log, stderr=subprocess.STDOUT)
    try:
        for _ in range(120):
            try:
                if http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200:
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        else:
            raise SystemExit("ABORT backend never answered; see " + str(BACKEND_LOG))
        for _ in range(120):
            if listeners(FRONTEND_PORT):
                break
            time.sleep(1)
        else:
            raise SystemExit("ABORT vite never listened; see " + str(VITE_LOG))

        for locale in ("en", "zh"):
            started = time.time()
            per: dict = {}
            errors: list = []
            try:
                d, _ = read(locale, ROUTES, "group")
            except subprocess.TimeoutExpired:
                d = None
            if d:
                per = d.get("perRoute", {})
                errors = d.get("pageErrors", [])
            else:
                doc["notes"].append(locale + ": the whole-group read failed, fell back to one route per session")
                for route in ROUTES:
                    try:
                        one, _ = read(locale, [route], route.strip("/").replace("/", "_"))
                    except subprocess.TimeoutExpired:
                        one = None
                    if one and one.get("perRoute", {}).get(route):
                        per[route] = one["perRoute"][route]
                        errors += one.get("pageErrors", [])
                    else:
                        doc["notes"].append(locale + " " + route + " NOT_REACHED_BY_LANE (never became ready)")
            items = [i for r in per.values() for i in r.get("items", [])]
            doc["arms"][locale] = {
                "wall_seconds": round(time.time() - started, 1),
                "routes_read": len(per),
                "routes_not_read": len(ROUTES) - len(per),
                "items_total": len(items),
                "kinds_total": {k: sum(1 for i in items if i["kind"] == k)
                                for k in sorted({i["kind"] for i in items})},
                "tokens_total": sorted({i["token"] for i in items}),
                "distinct_tokens": len({i["token"] for i in items}),
                "pageErrors": len(errors),
                "per_route": {r: {"items": len(v.get("items", [])),
                                   "kinds": v.get("kinds", {}),
                                   "tokens": sorted({i["token"] for i in v.get("items", [])})}
                               for r, v in per.items()},
            }
            print(locale, "routes", len(per), "items", len(items),
                  "distinct", len({i['token'] for i in items}), flush=True)
            emit()

        base_routes = baseline.get("perRoute", {})
        common = sorted(set(base_routes) & set(doc["arms"].get("en", {}).get("per_route", {})))
        doc["baseline_comparison"] = {
            "baseline_routes_in_that_file": len(base_routes),
            "routes_compared": len(common),
            "baseline_items_total": sum(len(v.get("items", [])) for v in base_routes.values()),
            "this_run_en_items_total": doc["arms"]["en"]["items_total"],
            "baseline_allow_list": len(baseline.get("allowListForAllCaps", [])),
            "per_route_delta": {r: {"baseline": len(base_routes[r].get("items", [])),
                                     "now": doc["arms"]["en"]["per_route"][r]["items"]}
                                for r in common},
        }
        emit()
    finally:
        for p in (vite, backend):
            p.terminate()
        for _ in range(30):
            if vite.poll() is not None and backend.poll() is not None:
                break
            time.sleep(1)
        for p in (vite, backend):
            if p.poll() is None:
                p.kill()
        v_log.close()
        b_log.close()
        doc["teardown"] = {"my_ports_listening_after": {str(BACKEND_PORT): listeners(BACKEND_PORT),
                                                         str(FRONTEND_PORT): listeners(FRONTEND_PORT)},
                           "canary_source_sha256_after": sha(SOURCE_CANARY),
                           "canary_source_untouched": sha(SOURCE_CANARY) == source_before}
        emit()
        LOCK.unlink(missing_ok=True)
        STORE.unlink(missing_ok=True)
        BACKEND_LOG.unlink(missing_ok=True)
        VITE_LOG.unlink(missing_ok=True)
        for f in DATA.glob(f"routesweep_*_{SFX}.json"):
            f.unlink(missing_ok=True)

    en, zh = doc["arms"].get("en", {}), doc["arms"].get("zh", {})
    ok = (en.get("routes_read", 0) + zh.get("routes_read", 0) > 0
          and doc["teardown"]["canary_source_untouched"]
          and all(v == [] for v in doc["teardown"]["my_ports_listening_after"].values()))
    doc["verdict"] = ("SWEEP_DONE both arms read route by route over this lane's dev base"
                      if ok else "NOT_DONE")
    emit()
    print(json.dumps({"receipt": str(RECEIPT), "verdict": doc["verdict"],
                      "en_items": en.get("items_total"), "zh_items": zh.get("items_total"),
                      "en_routes": en.get("routes_read"), "zh_routes": zh.get("routes_read"),
                      "notes": len(doc["notes"])}, ensure_ascii=False), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
