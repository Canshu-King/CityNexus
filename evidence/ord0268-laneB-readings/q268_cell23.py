"""ORD-0268 cells 2 and 3: force one real "offline + generation swap" under a live SW, then run the
same sequence against a build whose duplicate manifest line was removed (the killer).

Everything happens in scratch exports (`git archive` trees under my own order dir). No tracked tree, no
branch, no product commit. The killer edit is a copy of the export with one vite.config line removed --
that is what "把 additionalManifestEntries 那行删掉" asks for, and it must not be done in the repo.
"""
from __future__ import annotations

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
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
NM = pathlib.Path(r"D:\moodle\_qoder_integration_20260919\frontend\node_modules")
PREVIEW_PORT = 4441
DIST = "dist_ord0268"
DETACHED = 0x00000008 | 0x00000200
STEP_TIMEOUT = 90


def sh(args, cwd=None, timeout=1200):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def listeners(port):
    out = sh(["netstat", "-ano"]).stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out) if int(m.group(1)) == port})


def up_ok():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PREVIEW_PORT}/", timeout=4) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def preview_from(frontend: pathlib.Path):
    if listeners(PREVIEW_PORT):
        kill_preview()
    env = dict(os.environ) | {"CITYNEXUS_BACKEND_PORT": "8441", "PYTHONIOENCODING": "utf-8"}
    log = open(WORK / f"preview_{frontend.parent.name}.log", "a", encoding="utf-8")
    proc = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", DIST,
                             "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
                            cwd=str(frontend), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=DETACHED)
    for _ in range(40):
        if up_ok():
            return proc
        time.sleep(1)
    raise SystemExit(f"preview from {frontend} never answered")


def kill_preview():
    for pid in listeners(PREVIEW_PORT):
        sh(["taskkill", "/PID", str(pid), "/F"])
    time.sleep(1)


def step(profile: pathlib.Path, name: str) -> dict:
    out = WORK / f"q268_step_{name}.json"
    r = sh(["node", str(SPIKE / "q268_step_probe.js"), "--base", f"http://127.0.0.1:{PREVIEW_PORT}",
            "--out", str(out), "--step", name, "--profile", str(profile)], timeout=STEP_TIMEOUT * 3)
    print("  " + (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else f"  {name}: NO OUTPUT rc={r.returncode}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True, "stderr": r.stderr[-300:]}


def run_sequence(tag: str, gen_b_frontend: pathlib.Path) -> dict:
    profile = WORK / f"profile_{tag}"
    shutil.rmtree(profile, ignore_errors=True)
    steps = {}
    a = preview_from(WORK / "genA" / "frontend")
    steps["1_online_genA"] = step(profile, "online_a")
    kill_preview()
    b = preview_from(gen_b_frontend)
    steps["2_online_genB_swap"] = step(profile, "online_b")
    kill_preview()
    steps["3_offline_after_swap"] = step(profile, "offline")
    kill_preview()
    return steps


def manifest_of(frontend: pathlib.Path) -> list[dict]:
    src = (frontend / DIST / "v10-sw.js").read_text(encoding="utf-8")
    body = re.search(r"precacheAndRoute\(\[(.*?)\],\{\}\)", src, re.S).group(1)
    return [{"url": u, "revision": q or raw} for u, q, raw in
            re.findall(r'\{url:"([^"]+)",revision:(?:"([^"]*)"|([^,}]+))\}', body)]


# ---- killer build: same export, the duplicate line gone
killer = WORK / "genB_killer" / "frontend"
if not (killer / DIST / "v10-sw.js").exists():
    shutil.rmtree(killer.parent, ignore_errors=True)
    shutil.copytree(WORK / "genB" / "frontend", killer,
                    ignore=shutil.ignore_patterns("node_modules", "dist_*"))
    cfg = killer / "vite.config.ts"
    t = cfg.read_text(encoding="utf-8")
    line = next(ln for ln in t.splitlines() if "additionalManifestEntries" in ln)
    cfg.write_text(t.replace(line, "// killer for ORD-0268 cell 3: additionalManifestEntries removed\n"),
                   encoding="utf-8", newline="\n")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(killer / "node_modules"), str(NM)], capture_output=True)
    r = sh(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", DIST], cwd=str(killer), timeout=1200)
    assert r.returncode == 0, (r.stdout or "")[-300:] + (r.stderr or "")[-300:]

m_main = manifest_of(WORK / "genB" / "frontend")
m_killer = manifest_of(killer)
dup = lambda m: sorted({e["url"] for e in m if "/" + e["url"].lstrip("/") in
                        {"/" + x["url"].lstrip("/") for x in m if x["url"] != "/" + x["url"].lstrip("/")}})

res = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0268 cells 2 + 3",
       "lane": "B c01d72a3", "scratch_only": "all builds are git-archive exports; no tracked tree edited",
       "cell2_inputs": {"genA_dist_scripts": sorted(re.findall(r"assets/[\w.-]+\.js",
                            (WORK / "genA" / "frontend" / DIST / "index.html").read_text(encoding="utf-8"))),
                        "genB_dist_scripts": sorted(re.findall(r"assets/[\w.-]+\.js",
                             (WORK / "genB" / "frontend" / DIST / "index.html").read_text(encoding="utf-8"))),
                        "manifest_entries_normal_build": len(m_main),
                        "manifest_entries_killer_build": len(m_killer),
                        "duplicate_urls_normal": dup(m_main), "duplicate_urls_killer": dup(m_killer),
                        "killer_removed_line": line.strip()},
       "sequence_normal": run_sequence("normal", WORK / "genB" / "frontend"),
       "sequence_killer": run_sequence("killer", killer)}

n_off = res["sequence_normal"]["3_offline_after_swap"]
k_off = res["sequence_killer"]["3_offline_after_swap"]
same = json.dumps(n_off.get("navigation")) == json.dumps(k_off.get("navigation"))
res["cell3_killer_verdict"] = {
    "rule": "the killer must flip cell 2's conclusion; if it does not, cell 2 proves nothing about the "
            "double entry",
    "normal_offline_navigation": n_off.get("navigation"),
    "killer_offline_navigation": k_off.get("navigation"),
    "conclusion_identical": same,
    "verdict": "KILLER DID NOT FLIP -> cell 2 does not attribute the outcome to the double entry"
    if same else "KILLER FLIPPED IT -> the double entry is operative"}
p = WORK / "q268_cell23.json"
p.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(json.dumps(res["cell2_inputs"], ensure_ascii=False, indent=1)[:900])
print("cell3:", json.dumps(res["cell3_killer_verdict"], ensure_ascii=False)[:600])
print("->", p)
