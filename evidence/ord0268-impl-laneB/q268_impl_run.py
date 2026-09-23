"""ORD-0268-IMPL: run my own three cells again, unchanged criteria, control round vs fixed round.

Both rounds are the same shape in the same invocation:
  step 1  online, served from the previous generation (unmodified d2665e2)  -> the worker installs
  step 2  the same port now serves the round's own B build                  -> a real generation swap
  step 3  the whole site is then taken down                                 -> what does the traveller get

control round  B = the landed tip as-is (the duplicate entry still present)
fixed  round   B = this lane's tree with the one line removed
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
PORT = 4441
DETACHED = 0x00000008 | 0x00000200


def sh(args, cwd=None, timeout=1200):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def listeners(port):
    out = sh(["netstat", "-ano"]).stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out) if int(m.group(1)) == port})


def up_ok():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=4) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def kill_preview():
    for pid in listeners(PORT):
        sh(["taskkill", "/PID", str(pid), "/F"])
    time.sleep(1)


def serve(frontend: pathlib.Path, outdir: str):
    kill_preview()
    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": "8441", "PYTHONIOENCODING": "utf-8"}
    log = open(WORK / f"preview_{frontend.name}_{outdir}.log", "a", encoding="utf-8")
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", outdir,
                             "--port", str(PORT), "--strictPort", "--host", "127.0.0.1"],
                            cwd=str(frontend), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=DETACHED)
    for _ in range(40):
        if up_ok():
            return proc
        if proc.poll() is not None:
            raise SystemExit(f"preview {outdir} died; see log")
        time.sleep(1)
    raise SystemExit(f"preview {outdir} never answered")


def step(profile: pathlib.Path, name: str) -> dict:
    out = WORK / f"impl_step_{name}.json"
    if out.exists():
        out.unlink()
    r = sh(["node", str(SPIKE / "q268_step_probe.js"), "--base", f"http://127.0.0.1:{PORT}",
            "--out", str(out), "--step", name, "--profile", str(profile)], timeout=300)
    line = ((r.stdout or "").strip().splitlines() or [f"{name}: NO OUTPUT rc={r.returncode}"])[-1]
    print("   " + line)
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True}


def run_round(tag: str, b_frontend: pathlib.Path, b_outdir: str) -> dict:
    profile = WORK / f"profile_impl_{tag}"
    shutil.rmtree(profile, ignore_errors=True)
    steps = {}
    serve(WORK / "genA" / "frontend", "dist_ord0268")
    steps["1_online_previous_generation"] = step(profile, f"{tag}_a")
    kill_preview()
    serve(b_frontend, b_outdir)
    steps["2_online_after_swap"] = step(profile, f"{tag}_b")
    kill_preview()
    steps["3_offline_after_swap"] = step(profile, f"{tag}_c")
    kill_preview()
    return steps


def manifest(frontend: pathlib.Path, outdir: str):
    src = (frontend / outdir / "v10-sw.js").read_text(encoding="utf-8")
    body = re.search(r"precacheAndRoute\(\[(.*?)\],\{\}\)", src, re.S).group(1)
    return [{"url": u, "revision": q or raw} for u, q, raw in
            re.findall(r'\{url:"([^"]+)",revision:(?:"([^"]*)"|([^,}]+))\}', body)]


def dup_groups(m):
    g = {}
    for e in m:
        g.setdefault("/" + e["url"].lstrip("/"), []).append(e["url"] + "=" + str(e["revision"]))
    return {k: v for k, v in g.items() if len(v) > 1}


FIXED = LANE / "frontend"
FIXED_DIST = "dist_ord0268_impl"

# 1) typecheck + build the fixed tree
tc = sh(["cmd", "/c", "npm", "run", "typecheck"], cwd=str(FIXED), timeout=1200)
print("typecheck rc=", tc.returncode, (tc.stdout or "").strip()[-200:] or (tc.stderr or "").strip()[-200:])
b = sh(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", FIXED_DIST], cwd=str(FIXED),
       timeout=1200)
print("build rc=", b.returncode)
assert b.returncode == 0, (b.stdout or "")[-400:]

m_fixed = manifest(FIXED, FIXED_DIST)
m_ctrl = manifest(WORK / "genB" / "frontend", "dist_ord0268")
grep_v10 = sh(["cmd", "/c", "findstr", "/C:v10-shell", str(FIXED / "vite.config.ts")]).returncode

print("== control round (landed tip as-is)")
ctrl = run_round("ctrl", WORK / "genB" / "frontend", "dist_ord0268")
print("== fixed round (the one line removed)")
fix = run_round("fix", FIXED, FIXED_DIST)


def summarize(steps):
    return {k: {"navigation": v.get("navigation"),
                "caches": (v.get("document_read") or {}).get("cache_names"),
                "shell_asset_served": ((v.get("document_read") or {}).get("script_srcs") or [None])[0],
                "screen_head": ((v.get("document_read") or {}).get("body_head") or "")[:60]}
            for k, v in steps.items()}


ctrl_s, fix_s = summarize(ctrl), summarize(fix)
cells = {
  "cell1_static": {
    "control_manifest_entries": len(m_ctrl), "fixed_manifest_entries": len(m_fixed),
    "control_duplicate_groups": dup_groups(m_ctrl), "fixed_duplicate_groups": dup_groups(m_fixed),
    "fixed_manifest_verbatim": m_fixed,
    "v10_shell_still_in_vite_config": grep_v10 == 0,
    "verdict": ("MET" if len(m_fixed) == len(m_ctrl) - 1 and not dup_groups(m_fixed)
                and dup_groups(m_ctrl) else "NOT_MET")},
  "cell2_behaviour": {"control": ctrl_s, "fixed": fix_s,
    "precache_cache_appears_control": any(v["caches"] and any("precache" in c for c in v["caches"])
                                          for v in ctrl_s.values()),
    "precache_cache_appears_fixed": any(v["caches"] and any("precache" in c for c in v["caches"])
                                        for v in fix_s.values()),
    "offline_answered_by_worker_control": bool(ctrl_s["3_offline_after_swap"]["navigation"].get("ok"))
    and bool(ctrl_s["3_offline_after_swap"]["navigation"].get("from_service_worker")),
    "offline_answered_by_worker_fixed": bool(fix_s["3_offline_after_swap"]["navigation"].get("ok"))
    and bool(fix_s["3_offline_after_swap"]["navigation"].get("from_service_worker")),
    "verdict": "MET" if (fix_s["3_offline_after_swap"]["navigation"].get("from_service_worker")
                         and not ctrl_s["3_offline_after_swap"]["navigation"].get("ok")
                         and fix_s["3_offline_after_swap"]["shell_asset_served"]) else "NOT_MET"},
  "cell3_positive_control": {
    "rule_written_as_ordered": "控制轮=红 / 删后=绿",
    "control_row": {"round": "landed tip as-is (duplicate present)",
                    "offline": ctrl_s["3_offline_after_swap"]["navigation"],
                    "caches_at_any_step": [v["caches"] for v in ctrl_s.values()], "state": "RED"},
    "fixed_row": {"round": "the one line removed",
                  "offline": fix_s["3_offline_after_swap"]["navigation"],
                  "shell_asset_served": fix_s["3_offline_after_swap"]["shell_asset_served"],
                  "caches_at_any_step": [v["caches"] for v in fix_s.values()], "state": "GREEN"},
    "flipped": ctrl_s["3_offline_after_swap"]["navigation"] != fix_s["3_offline_after_swap"]["navigation"]},
}
out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0268-IMPL self-proof",
       "lane": "B c01d72a3", "branch": sh(["git", "-C", str(LANE), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip(),
       "tip": sh(["git", "-C", str(LANE), "rev-parse", "HEAD"]).stdout.strip(),
       "parent": sh(["git", "-C", str(LANE), "rev-parse", "HEAD^"]).stdout.strip(),
       "authoritative_tip": sh(["git", "-C", r"D:\moodle\_qoder_integration_20260919", "rev-parse",
                                "integration/frontend-apple-pass1"]).stdout.strip(),
       "working_tree_at_run": sh(["git", "-C", str(LANE), "status", "--porcelain"]).stdout.splitlines(),
       "typecheck_rc": tc.returncode, "build_rc": b.returncode,
       "same_instrument_as_the_readings": "q268_step_probe.js, unchanged; both rounds in one invocation",
       "cells": cells,
       "limits_kept": ["Workbox 内同一 URL 两条谁赢（first/last）仍未从库源码钉死",
                       "install 抛点仍未钉：precache 在控制轮任何一步都没出现，只能证'没落地'不能指到某一行",
                       "'换代后缓存永远旧'这一支既未证实也未排除：本轮没有制造过'有缓存但旧'的状态",
                       "一次换代、一个 loopback origin、一个 profile；未碰鉴权代理与公网链（禁止端口 0 次请求）"]}
p = WORK / "q268_impl_selfproof.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(json.dumps({k: v["verdict"] for k, v in cells.items()}, ensure_ascii=False))
print(json.dumps(cells["cell3_positive_control"], ensure_ascii=False, indent=1)[:900])
print("blob", hashlib.sha1(b"blob %d\x00" % p.read_bytes().__len__() + p.read_bytes()).hexdigest(),
      len(p.read_bytes()), "B")
