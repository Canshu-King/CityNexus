"""ORD-0267 step 2 driver: three cold starts, three answers from the same instrument.

arm clean      every asset 200            -> the control: what a whole install looks like
arm css_fails  one precached .css -> 500   -> the interesting one: the shell arrives, one member does not
arm sw_fails   /v10-sw.js -> 500           -> the worker never registers at all

For each arm: install the site cold, read what the precache actually holds against the worker's OWN
manifest, then remove the origin and ask what an ordinary offline navigation renders. No product file is
touched; every process is mine on port 8446 and stopped by name afterwards.
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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
OUT = WORK / "genB_baseline"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PORT = 8446
BASE = f"http://127.0.0.1:{PORT}"
DETACHED = 0x00000008 | 0x00000200
ALL_ARMS = [("clean", "none"), ("css_fails", "css"), ("sw_fails", "sw"),
            ("nonmember_fails", "nonmember")]
ONLY = [a for a in sys.argv[1:] if not a.startswith("-")]
ARMS = [a for a in ALL_ARMS if not ONLY or a[0] in ONLY]


def _entries(facts):
    c = facts.get("caches")
    if not isinstance(c, dict):
        return None
    for name, val in c.items():
        if name.startswith("workbox-precache") and isinstance(val, dict):
            return val.get("entries")
    return None


def listeners(port):
    o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", o)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def spawn_origin(hint):
    log = OUT / f"partial_origin_{hint}.log"
    log.unlink(missing_ok=True)
    p = subprocess.Popen([PY, str(SPIKE / "q267b_partial_origin.py")],
                         env=dict(os.environ) | {"CNX_PARTIAL_PORT": str(PORT), "CNX_BROKEN_HINT": hint},
                         stdout=open(OUT / f"partial_origin_{hint}.out", "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT, creationflags=DETACHED)
    for _ in range(30):
        if listeners(PORT):
            return p, log
        time.sleep(1)
    raise SystemExit(f"ABORT: partial origin ({hint}) never listened on :{PORT}")


def probe(phase, profile, out):
    out.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q267b_probe.js"), "--base", BASE, "--profile", str(profile),
                        "--out", str(out), "--phase", phase],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-260:]}"])[-1]
    print("   ", line[:230])
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True,
                                                                            "stderr": (r.stderr or "")[-300:]}


def origin_summary(log):
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()] if log.exists() else []
    bad = [r for r in rows if r["code"] != 200]
    return {"requests": len(rows), "non_200": bad[:8], "non_200_count": len(bad),
            "paths_500": sorted({r["path"] for r in bad if r["code"] == 500})}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if listeners(PORT):
        print(f"ABORT: :{PORT} already answers {listeners(PORT)}")
        return 2
    res = {}
    for name, hint in ARMS:
        print(f"== {name} (failing={hint})")
        prof = WORK / f"profile_{name}"
        shutil.rmtree(prof, ignore_errors=True)
        prof.mkdir(parents=True, exist_ok=True)
        origin, log = spawn_origin(hint)
        install = probe("install", prof, OUT / f"probe_{name}_install.json")
        served = origin_summary(log)
        print("    origin during install:", json.dumps(served, ensure_ascii=False)[:180])
        kill(listeners(PORT) + [origin.pid])
        time.sleep(1)
        offline = probe("offline", prof, OUT / f"probe_{name}_offline.json")
        f_i, f_o = install.get("facts") or {}, offline.get("facts") or {}
        res[name] = {"install": {"nav": install.get("navigation"), "controlled": f_i.get("controlled"),
                                 "controller": f_i.get("controller_script"),
                                 "registrations": f_i.get("registrations"),
                                 "manifest_count": install.get("manifest_count"),
                                 "cached_count": install.get("cached_count"),
                                 "missing_from_cache": install.get("missing_from_cache"),
                                 "cache_names": (list((f_i.get("caches") or {}).keys())
                                                 if isinstance(f_i.get("caches"), dict) else None),
                                 "precache_entries": _entries(f_i),
                                 "worker_source": f_i.get("worker_source"),
                                 "page_errors": install.get("page_errors"),
                                 "console_errors": (install.get("console_errors") or [])[:4],
                                 "non_200_responses": (install.get("non_200_responses") or [])[:6],
                                 "origin_served": served},
                    "offline": {"nav": offline.get("navigation"), "url": f_o.get("url"),
                                "controlled": f_o.get("controlled"), "mounted": f_o.get("app_mounted"),
                                "leaf_count": f_o.get("leaf_count"),
                                "rendered_head": (f_o.get("rendered_head") or "")[:170],
                                "requests_failed": (offline.get("requests_failed") or [])[:6],
                                "non_200": (offline.get("non_200_responses") or [])[:6],
                                "asset_probe": offline.get("offline_asset_probe"),
                                "cache_names": list((f_o.get("caches") or {}).keys()) if isinstance(f_o.get("caches"), dict) else None}}
        print("    install:", json.dumps({k: res[name]["install"][k] for k in
                                         ("controlled", "manifest_count", "cached_count", "missing_from_cache")},
                                         ensure_ascii=False)[:220])
        print("    offline:", json.dumps({k: res[name]["offline"][k] for k in
                                          ("nav", "controlled", "mounted", "rendered_head")},
                                          ensure_ascii=False)[:260])
    kill(listeners(PORT))
    prior_path = OUT / "ord0267b_cold_bootstrap.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.exists() else {}
    arms_now = dict(prior.get("arms") or {})
    arms_now.update(res)
    corrections = list(prior.get("arm_corrections") or [])
    if "nonmember_fails" in res:
        corrections.append({
            "arm": "nonmember_fails",
            "what_was_wrong": "my member comparison used the leading-slash form (`/assets/x.js`) against the "
                              "worker's own list (`assets/x.js`), so nothing matched and the arm 500-ed a REAL "
                              "member (the main chunk). That reading is superseded, not averaged in.",
            "now": "compared after stripping the leading slash; the picked path is printed by the origin at "
                   "startup together with the member list it read"})
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0267 定形重取 · 第 2 步：冷启完整性（四臂）",
           "lane": "B c01d72a3", "mode": "READ-ONLY; no product byte changed",
           "surface": {"origin_and_shell": BASE, "served_from": "dist_ord0267b (tip c79e2b4f)",
                       "one_fresh_profile_per_arm": True, "loopback_only": True,
                       "never_touched_or_opened": [":4781", ":4782", ":8693", "tunnel", "cnx proxy",
                                                   "_live", "_preview"],
                       "demo_reset": 0},
           "arms": arms_now,
           "arm_corrections": corrections,
           "re_ran_only": [a[0] for a in ARMS] if len(ARMS)<len(ALL_ARMS) else None}
    p = OUT / "ord0267b_cold_bootstrap.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("->", p.relative_to(WORK))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
