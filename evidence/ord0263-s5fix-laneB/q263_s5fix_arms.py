"""ORD-0263 fifth state: reverse arms, with an artifact-level check that the mutation really shipped.

K1 came back GREEN with the classifier branch made unreachable, which is either (a) my mutation not
reaching the bundle, or (b) the ruler's five conditions being satisfiable through another path. Both are
measurements, so both get measured: each arm rebuilds, then greps the emitted asset for the mutation's
fingerprints and for the fifth-state strings BEFORE the browser is involved.

Arms (one variable each, restored and byte-verified in a finally-block):
  A_no_throw_in_v8Request  the 2xx-with-unusable-body stop removed -> the old TypeError path
  B_unreachable_branch     classifyReadFailure's fifth branch made unreachable, throw left in place
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
RULER = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0263_verifier_v3.py")
RULER_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ORIGIN_PORT, PREVIEW_PORT = 8443, 4443          # same origin pair, or the snapshot is a different site
DETACHED = 0x00000008 | 0x00000200
ARMS = {
    "A_no_throw_in_v8Request": {
        "file": LANE / "frontend" / "src" / "app" / "V8Experience.tsx",
        "target": "  if (body === null) {",
        "mutated": "  if (false && body === null) {",
        "expect": "RED",
    },
    "B_unreachable_classify_branch": {
        "file": LANE / "frontend" / "src" / "lib" / "failureAttribution.ts",
        "target": "if (isOriginResponseUnusable(error)) {",
        "mutated": "if (false && isOriginResponseUnusable(error)) {",
        "expect": "unknown-or-red",
    },
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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


def spawn(cmd, cwd, log, env=None):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env or dict(os.environ), stdout=fh,
                                stderr=subprocess.STDOUT, creationflags=DETACHED)


def get(url, timeout=8):
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, b""


def asset_fingerprints(dist: pathlib.Path) -> dict:
    """What actually got emitted, before any browser is asked."""
    files = sorted((dist / "assets").glob("index-*.js"))
    if not files:
        return {"assets": [], "note": "no index asset"}
    text = files[0].read_text(encoding="utf-8", errors="replace")
    return {"asset": files[0].name, "bytes": len(text),
            "count_ORIGIN_INVALID_RESPONSE": text.count("ORIGIN_INVALID_RESPONSE"),
            "count_failure_originInvalidResponse": text.count("failure.originInvalidResponse"),
            "count_OriginResponseUnusable": text.count("OriginResponseUnusableError"),
            "count_body_null_guard": text.count("===null") + text.count("=== null")}


def run_arm(v3, name: str, arm: dict) -> dict:
    f, tgt, mut = arm["file"], arm["target"], arm["mutated"]
    before = sha(f)
    src = f.read_text(encoding="utf-8")
    hits = src.count(tgt)
    res = {"arm": name, "file": f.name, "sites_hit": hits, "before_sha256": before, "expect": arm["expect"]}
    if hits != 1:
        res["aborted"] = f"expected exactly one mutation site, found {hits}"
        return res
    pv = origin = None
    dist = LANE / "frontend" / f"dist_arm_{name.split('_')[0]}"
    try:
        f.write_text(src.replace(tgt, mut, 1), encoding="utf-8", newline="\n")
        res["mutated_sha256"] = sha(f)
        b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", dist.name],
                           cwd=str(LANE / "frontend"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
        res["build_rc"] = b.returncode
        if b.returncode != 0:
            res["aborted"] = "build failed: " + " | ".join((b.stdout or b.stderr).splitlines()[-3:])
            return res
        res["artifact_fingerprints"] = asset_fingerprints(dist)
        pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", dist.name,
                    "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
                   LANE / "frontend", BASE / f"arm_{name}_preview.log",
                   dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": str(ORIGIN_PORT)})
        origin = spawn([PY, str(SPIKE / "q263_s5fix_origin.py"), "--mode", "html", "--port", str(ORIGIN_PORT),
                        "--log", str(BASE / f"arm_{name}_origin.log")], SPIKE, BASE / f"arm_{name}_origin_out.log")
        for _ in range(45):
            if listeners(ORIGIN_PORT) and listeners(PREVIEW_PORT) and get(f"http://127.0.0.1:{PREVIEW_PORT}/")[0] == 200:
                break
            time.sleep(1)
        out = BASE / f"arm_{name}_read.json"
        out.unlink(missing_ok=True)
        subprocess.run(["node", str(SPIKE / "q263_s5_expand_read.js"),
                        "--url", f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub",
                        "--profile", str(BASE / "profile_s5fix"), "--out", str(out), "--mode", name],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
        read = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
        nodes = read.get("state_nodes") or {}
        rows = [json.loads(l) for l in (BASE / f"arm_{name}_origin.log").read_text(encoding="utf-8").splitlines()
                if l.strip()] if (BASE / f"arm_{name}_origin.log").exists() else []
        inst = [x for x in rows if x["kind"] == "answered" and "/experience" in x["path"]]
        res["reader"] = {"nodes": nodes, "settled_after_ms": read.get("settled_after_ms"),
                         "origin_answered_rows": len(inst),
                         "text_head": (read.get("rendered_text") or "").replace("\n", " | ")[:200]}
        if not inst or not nodes.get("failure-view"):
            res["aborted"] = ("the mutated build produced no classified failure screen with an answered journey "
                              "row - not a valid comparison")
            return res
        shape = {"shape": "200_html",
                 "origin_answer": {"status": inst[-1]["status"], "thrown": False,
                                   "content_type": inst[-1]["content_type"], "body_bytes": inst[-1]["body_bytes"],
                                   "wire": f"arm_{name}_origin.log"},
                 "rendered_text": read.get("rendered_text") or "",
                 "snapshot_rows": (read.get("snapshot") or {}).get("rows"),
                 "buttons": read.get("buttons") or []}
        j = v3.judge_v5(shape)
        res["judge_v5"] = {"verdict": j["verdict"], "failed_conditions": j.get("failed_conditions"),
                           "measured_columns": (j.get("measured") or {}).get("rendered_attribution")}
        res["flipped_as_expected"] = (j["verdict"] == "RED") if arm["expect"] == "RED" else True
    finally:
        kill(listeners(ORIGIN_PORT) + listeners(PREVIEW_PORT))
        for h in (pv, origin):
            try:
                if h:
                    h.kill()
            except Exception:  # noqa: BLE001
                pass
        now = f.read_text(encoding="utf-8")
        f.write_text(now.replace(mut, tgt, 1), encoding="utf-8", newline="\n")
        res["after_restore_sha256"] = sha(f)
        res["restored_byte_exact"] = sha(f) == before
        shutil.rmtree(dist, ignore_errors=True)
    return res


def main() -> int:
    rb = RULER.read_bytes()
    if blob(rb) != RULER_BLOB:
        raise SystemExit("ABORT: ruler is not the published blob")
    spec = importlib.util.spec_from_file_location("ord0263_v3", str(RULER))
    v3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v3)
    if listeners(ORIGIN_PORT) or listeners(PREVIEW_PORT):
        print(f"ABORT: :{ORIGIN_PORT}/:{PREVIEW_PORT} busy {listeners(ORIGIN_PORT)} {listeners(PREVIEW_PORT)}")
        return 2
    rows = [run_arm(v3, n, a) for n, a in ARMS.items()]
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0263 第五态 · 反向臂（产物层先验，再跑屏）", "lane": "B c01d72a3",
           "shape_under_test": "200_html", "ruler": {"blob40": blob(rb), "entry": "judge_v5"},
           "arms": rows,
           "restores_all_byte_exact": all(r.get("restored_byte_exact") for r in rows)}
    p = BASE / "q263_s5fix_reverse_arms.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    for r in rows:
        print(f"\n== {r['arm']}  sites={r.get('sites_hit')} restored_exact={r.get('restored_byte_exact')}")
        if r.get("artifact_fingerprints"):
            print("   artifact:", json.dumps(r["artifact_fingerprints"], ensure_ascii=False)[:230])
        if r.get("judge_v5"):
            print("   judge_v5:", r["judge_v5"]["verdict"], json.dumps(r["judge_v5"]["failed_conditions"], ensure_ascii=False))
            print("   columns :", json.dumps(r["judge_v5"]["measured_columns"], ensure_ascii=False)[:230])
        if r.get("reader"):
            print("   screen  :", r["reader"]["text_head"][:170])
        if r.get("aborted"):
            print("   ABORTED :", r["aborted"])
    print("\nrestores all byte-exact:", out["restores_all_byte_exact"], "->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
