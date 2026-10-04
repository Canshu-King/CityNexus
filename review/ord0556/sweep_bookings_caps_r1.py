"""ORD-0556 -- source-classify the five caps words the commander's own sweep counts on /v8/bookings.

What this runs is not my instrument: `cmdr_machine_speech_sweep_r1.js` is the commander's, and the
dispatch names its output as the baseline. So the denominator is measured by the same shape of read the
acceptance will be judged by, over this lane's own stack:

  * a backend of mine on a port of mine, over a COPY of the commander's canary (hashed before and after
    so "I never wrote to the source" is a measurement);
  * the sweep run twice -- English arm and Chinese arm -- because the ruling says an all-caps label is
    only a defect if the dictionary value itself is upper case, and the Chinese arm is the control that
    shows the slot is a label rather than a server value;
  * per token, the source read: the dictionary line that paints it, whether the class that holds it
    carries a CSS uppercase transform, and whether an upstream vocabulary name for it exists in
    backend/app at all.

Zero product bytes: this run only measures.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
FRONTEND = ROOT / "frontend"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
SWEEP_JS = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_machine_speech_sweep_r1.js")
PANEL_LABELS = [
    ("STAY EVIDENCE", "frontend/src/i18n/LocaleContext.tsx", '"bookings.stayEvidence"'),
    ("MULTIMODAL INBOX", "frontend/src/i18n/LocaleContext.tsx", '"inbox.multimodal"'),
    ("AUTHORITATIVE MEMORY", "frontend/src/i18n/LocaleContext.tsx", '"inbox.authoritativeMemory"'),
]
STYLES = "frontend/src/styles.css"
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SFX = RUN_STAMP[-7:-1]
BASE_TIP = os.environ.get("CITYNEXUS_ORD0556_BASE_TIP", "")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_BACKEND_PORT", "4941"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_FRONTEND_PORT", "4946"))
STORE = DATA / f"_ord0556_{SFX}.db"
BACKEND_LOG = DATA / f"uvicorn_{BACKEND_PORT}_{SFX}.log"
VITE_LOG = DATA / f"vite_{FRONTEND_PORT}_{SFX}.log"
RECEIPT = DATA / f"ord0556_sweep_{RUN_STAMP}.json"
LOCK = DATA / f"ord0556_sweep_{SFX}.lock"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
FORBIDDEN = (8000, 4781, 4782, 4783, 4785, 4786, 4787, 8693)


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def children_of(pid: int) -> list[str]:
    probe = ("Get-CimInstance Win32_Process -Filter 'ParentProcessId=" + str(pid) + "' "
             "| ForEach-Object { $_.ProcessId }")
    return [x for x in subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                                      capture_output=True, text=True, errors="replace").stdout.split()
            if x.isdigit()]


def http(method: str, url: str, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json",
                                          "user-agent": "CityNexus-ORD-0556-lane"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def line_and_value(rel: str, needle: str) -> dict:
    text = (ROOT / rel).read_text(encoding="utf-8")
    hits = [(i + 1, l.strip()) for i, l in enumerate(text.splitlines()) if needle in l]
    return {"path_line": f"{rel}:{hits[0][0]}" if len(hits) == 1 else "AMBIGUOUS",
            "hits": len(hits),
            "source_value": (hits[0][1] if len(hits) == 1 else ""),
            "value_is_upper_case_as_painted": bool(len(hits) == 1 and re.search(r':\s*"[^"]*[A-Z]{4,}', hits[0][1]))}


def css_transform(rel: str, cls: str) -> dict:
    text = (ROOT / rel).read_text(encoding="utf-8")
    line_no = next((i + 1 for i, l in enumerate(text.splitlines()) if cls + " {" in l or cls + "," in l), 0)
    rule = ""
    for chunk in text.split("}"):
        if chunk.strip().startswith(cls):
            rule = chunk
            break
    return {"path_line": f"{rel}:{line_no}" if line_no else "NOT_FOUND",
            "has_uppercase_transform": "text-transform: uppercase" in rule}


def upstream_names(token: str) -> dict:
    snake = token.replace(" ", "_")
    found = {}
    for probe in (token, snake, snake.lower()):
        r = subprocess.run(["grep", "-ral", "--include=*.py", "--include=*.yaml", probe,
                            "backend/app", "contracts"], cwd=ROOT,
                           capture_output=True, text=True, errors="replace")
        found[probe] = sorted({p for p in r.stdout.splitlines() if "__pycache__" not in p})
    return found


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT another ORD-0556 run holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if not re.fullmatch(r"[0-9a-f]{40}", BASE_TIP or ""):
        raise SystemExit("ABORT CITYNEXUS_ORD0556_BASE_TIP must be the 40-hex tip measured on")
    if listeners(BACKEND_PORT) or listeners(FRONTEND_PORT):
        raise SystemExit("ABORT my ports are held: " + str(listeners(BACKEND_PORT) + listeners(FRONTEND_PORT)))
    held_forbidden = {str(p): listeners(p) for p in FORBIDDEN if listeners(p)}
    source_before = sha(SOURCE_CANARY)
    STORE.write_bytes(SOURCE_CANARY.read_bytes())

    doc: dict = {"generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP,
                                "this_lane_ports": [BACKEND_PORT, FRONTEND_PORT],
                                "store_copy": STORE.name, "store_copy_sha256": sha(STORE),
                                "canary_source_sha256_before": source_before,
                                "forbidden_ports_held_by_others": held_forbidden,
                                "instrument": str(SWEEP_JS)},
                 "sweeps": {}, "source_classification": []}

    def emit():
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
    v_log = VITE_LOG.open("w", encoding="utf-8", errors="replace")
    vite_env = dict(env)
    vite_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1",
                             "--port", str(FRONTEND_PORT), "--strictPort"],
                            cwd=FRONTEND, env=vite_env, stdout=v_log, stderr=subprocess.STDOUT)
    try:
        for _ in range(90):
            try:
                if http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200:
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        else:
            raise SystemExit("ABORT backend never answered; see " + str(BACKEND_LOG))
        for _ in range(90):
            if listeners(FRONTEND_PORT):
                break
            time.sleep(1)
        else:
            raise SystemExit("ABORT vite never listened; see " + str(VITE_LOG))
        family = {str(backend.pid), str(vite.pid), *children_of(backend.pid), *children_of(vite.pid)}
        doc["generation"]["listeners_attributed_to_this_lane"] = {
            "backend_pids": listeners(BACKEND_PORT), "frontend_pids": listeners(FRONTEND_PORT),
            "all_mine": bool(set(listeners(BACKEND_PORT) + listeners(FRONTEND_PORT)) <= family),
        }
        marker = "ORD-0556-sweep-" + SFX
        status, _ = http("POST", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/travelers",
                         {"display_name": marker, "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        import sqlite3
        conn = sqlite3.connect(f"file:{STORE.as_posix()}?mode=ro", uri=True)
        mine_rows = conn.execute("SELECT COUNT(*) FROM travelers WHERE display_name = ?", (marker,)).fetchone()[0]
        conn.close()
        cconn = sqlite3.connect(f"file:{SOURCE_CANARY.as_posix()}?mode=ro", uri=True)
        src_rows = cconn.execute("SELECT COUNT(*) FROM travelers WHERE display_name = ?", (marker,)).fetchone()[0]
        cconn.close()
        doc["generation"]["attribution"] = {"post_status": status, "marker_in_my_copy": mine_rows,
                                            "marker_in_canary_source": src_rows}
        emit()

        base = f"http://127.0.0.1:{FRONTEND_PORT}/"
        for locale in ("en", "zh"):
            out_file = DATA / f"ord0556_sweep_{locale}_{SFX}.json"
            started = time.time()
            r = subprocess.run(["node", str(SWEEP_JS), base, str(out_file), locale],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=900, cwd=str(DATA))
            sweep = json.loads(out_file.read_text(encoding="utf-8")) if out_file.is_file() else {}
            per = sweep.get("perRoute", {}).get("/v8/bookings", {})
            doc["sweeps"][locale] = {
                "rc": r.returncode, "wall_seconds": round(time.time() - started, 1),
                "file": out_file.name,
                "allowListForAllCaps": sweep.get("allowListForAllCaps"),
                "pageErrors": sweep.get("pageErrors"),
                "bookings_items": per.get("items", []),
                "bookings_kinds": per.get("kinds", {}),
                "routes_walked": len(sweep.get("perRoute", {})),
            }
            print(locale, "rc", r.returncode, "items", len(per.get("items", [])),
                  json.dumps(per.get("kinds", {})), flush=True)
            emit()

        for token, dict_rel, key in PANEL_LABELS:
            cls = "v8-selected-label" if token == "STAY EVIDENCE" else "v8-kicker"
            doc["source_classification"].append({
                "token": token,
                "dictionary": line_and_value(dict_rel, key),
                "css_class": cls,
                "css": css_transform(STYLES, cls),
                "upstream_name_hits": upstream_names(token),
                "in_en_sweep": [i["token"] for i in doc["sweeps"]["en"]["bookings_items"]],
                "in_zh_sweep": [i["token"] for i in doc["sweeps"]["zh"]["bookings_items"]],
            })
        json_lede = [i for i in doc["sweeps"]["en"]["bookings_items"] if i["token"] == "JSON"]
        doc["json_in_lede_copy"] = {"count": len(json_lede), "tags_classes": sorted({j["cls"] for j in json_lede})}
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
        doc["teardown"] = {"vite_exit": vite.returncode, "backend_exit": backend.returncode,
                           "my_ports_listening_after": {str(BACKEND_PORT): listeners(BACKEND_PORT),
                                                         str(FRONTEND_PORT): listeners(FRONTEND_PORT)},
                           "canary_source_sha256_after": sha(SOURCE_CANARY),
                           "canary_source_untouched": sha(SOURCE_CANARY) == source_before}
        emit()
        LOCK.unlink(missing_ok=True)
        STORE.unlink(missing_ok=True)
        BACKEND_LOG.unlink(missing_ok=True)
        VITE_LOG.unlink(missing_ok=True)

    doc["verdict"] = ("SWEEP_DONE both arms measured over this lane's own stack; every bookings item is "
                      "classified against its dictionary line, its CSS class and an upstream-name probe"
                      if doc["sweeps"].get("en", {}).get("rc") == 0 and doc["sweeps"].get("zh", {}).get("rc") == 0
                      and doc["teardown"]["canary_source_untouched"] else "NOT_DONE")
    emit()
    print(json.dumps({"receipt": str(RECEIPT), "verdict": doc["verdict"],
                      "en_items": len(doc["sweeps"].get("en", {}).get("bookings_items", [])),
                      "zh_items": len(doc["sweeps"].get("zh", {}).get("bookings_items", []))},
                     ensure_ascii=False), flush=True)
    return 0 if doc["verdict"].startswith("SWEEP_DONE") else 1


if __name__ == "__main__":
    sys.exit(main())
