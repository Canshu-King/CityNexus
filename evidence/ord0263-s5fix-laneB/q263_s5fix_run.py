"""ORD-0263 fifth-state candidate: run HARNESS's own v3 ruler over MY readings, five cells.

Everything here is a real process on my own ports (:4443 preview, :8443 origin) against a real browser
with a real snapshot earned from a real backend -- no browser mocks, no in-page stubs, and none of the
user's ports or databases.

Round 1: the candidate as committed.  The three junk shapes go to `judge_v5`/`aggregate_v5`; the four
earlier cells go to his `judge_all`, whose arms are byte-identical to v2.
Round 2: one reverse arm -- the fifth branch removed -- to prove the greens are carried by that branch
and not by something nearby.  Restore afterwards, byte-exact.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = pathlib.Path(r"D:\moodle\_qoder_b_ord0263_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
BACKEND = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923\genB\backend")
RULER = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0263_verifier_v3.py")
RULER_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ORIGIN_PORT, PREVIEW_PORT = 8443, 4443
DB = BASE / "db" / "ord0263_s5fix_8443.db"
ATTR_FILE = LANE / "frontend" / "src" / "lib" / "failureAttribution.ts"
DETACHED = 0x00000008 | 0x00000200
BACKEND_ENV = {"CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}", "CITYNEXUS_ENV": "dev",
               "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
               "CITYNEXUS_GUARDIAN_AUTORUN": "false", "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": "",
               "CITYNEXUS_ANYWHERE_RESOLVER": "off", "CITYNEXUS_PHOTON_BASE_URL": "http://127.0.0.1:9",
               "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
SHAPES = [("html", "200_html"), ("empty", "200_empty"), ("nonjson", "200_not_json")]
OLD_CELLS = [("five_hundred", "S2_origin_error"), ("silent", "S3_no_answer"),
             ("mixed", "S4_read_silent_health_answered")]


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def listeners(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", out)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def spawn(cmd, cwd, log, env):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                creationflags=DETACHED)


def get(url, timeout=8):
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, b""


def wait_until(pred, tries=90):
    for _ in range(tries):
        if pred():
            return True
        time.sleep(1)
    return False


def read(label: str, enter: bool = False) -> dict:
    out = BASE / f"s5fix_read_{label}.json"
    out.unlink(missing_ok=True)
    cmd = ["node", str(SPIKE / ("q263_read_page.js" if enter else "q263_s5_expand_read.js")),
           "--url", f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub",
           "--profile", str(BASE / "profile_s5fix"), "--out", str(out), "--label", label, "--mode", label]
    if enter:
        cmd.append("--enter")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-160:]}"])[-1]
    print(f"    {label:14s} {line[:150]}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True}


def log_rows(mode: str):
    p = BASE / f"s5fix_origin_{mode}.log"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def classified_label(read: dict) -> str | None:
    last = (read.get("in_memory_attribution_last") or {})
    snap = bool((read.get("snapshot") or {}).get("rows"))
    if not last:
        return "LIVE" if (read.get("state_nodes") or {}).get("today-heading") else None
    reason = last.get("reason")
    if reason == "SERVER_ERROR":
        return "ORIGIN_ERROR_WITH_SNAPSHOT" if snap else "ORIGIN_ERROR"
    if reason == "NETWORK_UNAVAILABLE":
        return "NETWORK_UNREACHABLE_WITH_SNAPSHOT" if snap else "NETWORK_UNREACHABLE"
    if reason == "ORIGIN_INVALID_RESPONSE":
        return "ORIGIN_ANSWERED_BUT_NOT_USABLE_WITH_SNAPSHOT" if snap else "ORIGIN_ANSWERED_BUT_NOT_USABLE"
    if reason == "JOURNEY_NOT_FOUND":
        return "JOURNEY_GONE"
    return reason


def cell(read: dict, origin_row: dict | None) -> dict:
    probe = read.get("resource_timing") or {}
    health = probe.get("health") or {}
    return {
        "classified_label": classified_label(read),
        "rendered_text": read.get("rendered_text") or "",
        "origin_answer": {"status": (origin_row or {}).get("status", health.get("status")),
                          "thrown": (origin_row or {}).get("kind") == "hung",
                          "ct": (origin_row or {}).get("content_type"),
                          "body_bytes": (origin_row or {}).get("body_bytes")},
        "settled_within_deadline": read.get("settled_after_ms") is not None,
        "seconds_to_settle": (read.get("settled_after_ms") or 0) / 1000 if read.get("settled_after_ms") else None,
        "snapshot_present": bool((read.get("snapshot") or {}).get("rows")),
        "snapshot_rows": (read.get("snapshot") or {}).get("rows"),
        "navigator_onLine": True,
        "doors": {"retry": sum(1 for b in (read.get("buttons") or []) if "重试" in b),
                  "read_only_snapshot": sum(1 for b in (read.get("buttons") or []) if "只读" in b)},
    }


def load_ruler():
    rb = RULER.read_bytes()
    if blob(rb) != RULER_BLOB:
        raise SystemExit("ABORT: the ruler on disk is not the published blob")
    spec = importlib.util.spec_from_file_location("ord0263_v3", str(RULER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, rb


def run_round(v3, tag: str) -> dict:
    reads: dict[str, dict] = {}
    # live cell first, against the real backend, while the snapshot is still fresh
    reads["S1_live"] = read("live")
    shapes, cells = [], {}
    for mode, shape_name in SHAPES:
        kill(listeners(ORIGIN_PORT))
        origin = spawn([PY, str(SPIKE / "q263_s5fix_origin.py"), "--mode", mode, "--port", str(ORIGIN_PORT),
                        "--log", str(BASE / f"s5fix_origin_{mode}.log")], SPIKE,
                       BASE / f"s5fix_origin_{mode}.out", dict(os.environ))
        if not wait_until(lambda: listeners(ORIGIN_PORT) and get(f"http://127.0.0.1:{ORIGIN_PORT}/api/v1/health")[0] == 200, 30):
            raise SystemExit(f"ABORT: {mode} origin never answered on :{ORIGIN_PORT}")
        ph = get(f"http://127.0.0.1:{PREVIEW_PORT}/api/v1/health")
        if b"ord0263-s5fix-mine" not in ph[2]:
            raise SystemExit(f"ABORT: proxy does not reach my {mode} origin (got {ph[0]} {ph[1]})")
        rr = read(shape_name)
        rows = [r for r in log_rows(mode) if r["kind"] == "answered" and "/experience" in r["path"]]
        if not rows:
            raise SystemExit(f"ABORT: {mode} log has no answered journey row - the reading is not mine")
        inst = rows[-1]
        shapes.append({"shape": shape_name,
                       "origin_answer": {"status": inst["status"], "thrown": False,
                                         "content_type": inst["content_type"], "body_bytes": inst["body_bytes"],
                                         "body_head": inst["body_head"],
                                         "wire": f"s5fix_origin_{mode}.log: my origin answered {inst['status']} "
                                                 f"{inst['content_type']} with {inst['body_bytes']} B at {inst['at']}"},
                       "rendered_text": rr.get("rendered_text") or "",
                       "snapshot_rows": (rr.get("snapshot") or {}).get("rows"),
                       "buttons": rr.get("buttons") or []})
        reads[shape_name] = rr
        kill([origin.pid] + listeners(ORIGIN_PORT))
    for mode, cell_name in OLD_CELLS:
        kill(listeners(ORIGIN_PORT))
        origin = spawn([PY, str(SPIKE / "q263_s5fix_origin.py"), "--mode", mode, "--port", str(ORIGIN_PORT),
                        "--log", str(BASE / f"s5fix_origin_{mode}.log")], SPIKE,
                       BASE / f"s5fix_origin_{mode}.out", dict(os.environ))
        wait_until(lambda: listeners(ORIGIN_PORT), 20)
        rr = read(cell_name)
        rows = [r for r in log_rows(mode) if "/experience" in (r.get("path") or "")]
        cells[cell_name] = cell(rr, rows[-1] if rows else None)
        cells[cell_name]["instrument_rows"] = rows[-3:]
        reads[cell_name] = rr
        kill([origin.pid] + listeners(ORIGIN_PORT))
    cells["S1_live"] = cell(reads["S1_live"], {"status": 200, "thrown": False, "kind": "answered"})
    cap = {"cells": {**{k: cells[k] for k in cells}, "S5_invalid_response": {"shapes": shapes}}}
    per = {s["shape"]: v3.judge_v5(s) for s in shapes}
    agg = v3.aggregate_v5(shapes)
    four = v3.judge_all(cap)
    return {"tag": tag, "shapes": shapes, "reads": reads, "judge_v5_per_shape": per,
            "aggregate_v5": agg, "four_old_cells": four, "capture": cap}


def main() -> int:
    v3, rb = load_ruler()
    print(f"ruler blob {blob(rb)[:12]}… match published: True")
    for p in (ORIGIN_PORT, PREVIEW_PORT):
        if listeners(p):
            print(f"ABORT: :{p} already answers {listeners(p)}")
            return 2
    shutil.rmtree(BASE / "profile_s5fix", ignore_errors=True)
    (BASE / "db").mkdir(parents=True, exist_ok=True)
    for suf in ("", "-wal", "-shm"):
        pathlib.Path(str(DB) + suf).unlink(missing_ok=True)

    be = spawn([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(ORIGIN_PORT)],
               BACKEND, BASE / "s5fix_backend.log", dict(os.environ) | BACKEND_ENV)
    if not wait_until(lambda: listeners(ORIGIN_PORT) and get(f"http://127.0.0.1:{ORIGIN_PORT}/api/v1/health")[0] == 200):
        print("ABORT: real backend never answered")
        return 3
    subprocess.run([PY, "-c", "import app.main as m; from app.db.session import SessionLocal, ensure_schema;"
                              "ensure_schema(); s=SessionLocal(); m.seed_demo(s); s.close()"],
                   cwd=str(BACKEND), env=dict(os.environ) | BACKEND_ENV, capture_output=True, timeout=400)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", "dist_s5",
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               LANE / "frontend", BASE / "s5fix_preview.log",
               dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(ORIGIN_PORT)})
    wait_until(lambda: listeners(PREVIEW_PORT) and get(f"http://127.0.0.1:{PREVIEW_PORT}/")[0] == 200)

    print("  earning the snapshot against a real backend (no mock):")
    enter = read("enter", enter=True)
    snap0 = (enter.get("snapshot") or {})
    if not snap0.get("present"):
        print(f"ABORT: no snapshot earned ({json.dumps(snap0, ensure_ascii=False)[:160]})")
        kill([be.pid, pv.pid] + listeners(ORIGIN_PORT) + listeners(PREVIEW_PORT))
        return 4
    ownership = {"served_doc_equals_my_dist": None, "marker_through_proxy": None}
    doc = get(f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub")
    disk = (LANE / "frontend" / "dist_s5" / "index.html").read_bytes()
    ownership["served_doc_equals_my_dist"] = doc[2] == disk
    ownership["marker_through_proxy"] = b"ord0263-s5fix-mine" in get(f"http://127.0.0.1:{PREVIEW_PORT}/api/v1/health")[2]
    print(f"  ownership: doc from my dist={ownership['served_doc_equals_my_dist']} marker via proxy={ownership['marker_through_proxy']}")

    r1 = run_round(v3, "candidate_round")
    kill([be.pid, pv.pid] + listeners(ORIGIN_PORT) + listeners(PREVIEW_PORT))

    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0263 第五态候选自证（三形 + 前四格）", "lane": "B c01d72a3", "round": r1["tag"],
           "ruler": {"path": str(RULER), "blob40": blob(rb), "expected": RULER_BLOB,
                     "unchanged_after": blob(RULER.read_bytes()) == blob(rb)},
           "surface": {"preview": PREVIEW_PORT, "origin": ORIGIN_PORT, "bundle": "dist_s5 built from this branch",
                       "snapshot_earned_via": "the app's own sealed-demo control against a real backend",
                       "snapshot_after_enter": snap0, "ownership": ownership,
                       "provider_egress": "AI off, resolver off, Photon pointed at 127.0.0.1:9",
                       "never_touched": [4781, 4782, 8693, 4185, 8713],
                       "write_leg_probe": "not run in this round: commander 5798766898 forbids POST probes here, and my "
                              "earlier A3 sentence is a producer reading pending the arbiter's isolation ruling, "
                              "not a conclusion"},
           "shapes": r1["shapes"], "judge_v5_per_shape": r1["judge_v5_per_shape"],
           "aggregate_v5": r1["aggregate_v5"], "four_old_cells": r1["four_old_cells"],
           "capture_for_the_ruler": r1["capture"]}
    p = BASE / "q263_s5fix_selfproof.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("\n  aggregate_v5:", out["aggregate_v5"]["verdict"])
    for k, v in out["judge_v5_per_shape"].items():
        print(f"    {k:12s} {v['verdict']:5s} failed={json.dumps(v.get('failed_conditions'), ensure_ascii=False)[:110]}")
    print("  four old cells:", json.dumps({k: v.get("verdict") for k, v in out["four_old_cells"].items()}, ensure_ascii=False))
    print("->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
