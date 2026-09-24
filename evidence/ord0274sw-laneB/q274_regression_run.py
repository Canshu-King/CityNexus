"""ORD-0274-SW non-regression, loopback equivalents of the A arm and B3.

The commander's pass condition is B2 -> MET *and* the A arm (never-reconnected) and B3 (offline after
convergence) must not regress. HJ-P1 owns those cells on the real chain; what I can do without touching her
surface is reproduce their SHAPE on my own port and show the fix does not break it:

  A-equivalent  a client that only ever saw gen1, then total darkness -> must keep serving gen1
                consistently: no half-generation, no chrome-error, same module before and after.
  B3-equivalent a client that converged to gen2 (using the fix), then total darkness -> must keep serving
                gen2 consistently.

Instruments are the same ones as the convergence run; the only difference is which phases I run and that
the origin is stopped instead of swapped.
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
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PORT = 8453
BASE = f"http://127.0.0.1:{PORT}"
DETACHED = 0x00000008 | 0x00000200
DISTS = {"g1": pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_ord0267b"),     # unfixed landed tip
         "g2": pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_0274sw"),        # the fix
         "g3": pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_0274sw_gen2")}  # next gen


def listeners(port):
    o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", o)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def serve(old, new):
    p = subprocess.Popen([PY, str(SPIKE / "q274_gen_origin.py"), "--gen", "old", "--gen2", "new",
                          "--port", str(PORT), "--log", str(WORK / f"reg_origin_{old}_{new}.log")],
                         env=dict(os.environ) | {"CNX_GEN_OLD_DIR": str(DISTS[old]),
                                                 "CNX_GEN_NEW_DIR": str(DISTS[new])},
                         stdout=open(WORK / f"reg_origin_{old}_{new}.out", "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT, creationflags=DETACHED)
    for _ in range(30):
        if listeners(PORT):
            return p
        time.sleep(1)
    raise SystemExit(f"ABORT: origin ({old}->{new}) never listened on :{PORT}")


def serve_only(gen):
    """No swap target at all - the A arm's world is one generation that then goes dark."""
    p = subprocess.Popen([PY, str(SPIKE / "q274_gen_origin.py"), "--gen", "old", "--gen2", "old",
                          "--port", str(PORT),
                          "--log", str(WORK / f"reg_origin_only_{gen}.log")],
                         env=dict(os.environ) | {"CNX_GEN_OLD_DIR": str(DISTS[gen]),
                                                 "CNX_GEN_NEW_DIR": str(DISTS[gen])},
                         stdout=open(WORK / f"reg_origin_only_{gen}.out", "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT, creationflags=DETACHED)
    for _ in range(30):
        if listeners(PORT):
            return p
        time.sleep(1)
    raise SystemExit(f"ABORT: origin (only {gen}) never listened on :{PORT}")


def probe(profile, phase, window=12):
    out = WORK / f"reg_{profile}_{phase}.json"
    out.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q274_transition_probe.js"), "--base", BASE,
                        "--profile", str(WORK / profile), "--out", str(out), "--phase", phase,
                        "--window", str(window)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1]
    print(f"      {line[:190]}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True}


def seen(p):
    return (p or {}).get("seen") or {}


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    if listeners(PORT):
        print(f"ABORT: :{PORT} answers {listeners(PORT)}")
        return 2
    res = {}

    # ---- A-equivalent: one generation, then darkness
    print("== A-equivalent (never reconnected)")
    shutil.rmtree(WORK / "profile_A", ignore_errors=True)
    (WORK / "profile_A").mkdir(parents=True, exist_ok=True)
    p = serve_only("g1")
    a1 = probe("profile_A", "install", 8)
    kill(listeners(PORT) + [p.pid])
    time.sleep(1)
    a2 = probe("profile_A", "again", 10)
    s1, s2 = seen(a1), seen(a2)
    res["A_equivalent"] = {
        "online": {"bundle": s1.get("executing_bundle"), "controller": s1.get("controller_now"),
                   "registrations": s1.get("registrations")},
        "offline": {"nav": a2.get("seen") and (a2.get("navigation") or None), "bundle": s2.get("executing_bundle"),
                    "controlled": s2.get("controller_now"), "mounted": s2.get("mounted"),
                    "url": s2.get("url"), "navigation": a2.get("navigation")},
        "same_generation_while_offline": bool(s1.get("executing_bundle")) and s1.get("executing_bundle") == s2.get("executing_bundle"),
        "answered_by_shell_offline": bool((a2.get("navigation") or {}).get("ok")),
        "half_generation_mix": sorted({str(x.get("bundle")) for x in (a2.get("samples") or []) if x.get("bundle")})
                               if a2.get("samples") else None}

    # ---- B3-equivalent: converge onto the fix's next generation, then darkness
    print("== B3-equivalent (offline after convergence)")
    shutil.rmtree(WORK / "profile_B3", ignore_errors=True)
    (WORK / "profile_B3").mkdir(parents=True, exist_ok=True)
    p = serve("g2", "g3")   # client starts on the fix, next generation arrives
    b1 = probe("profile_B3", "install", 8)
    b2 = probe("profile_B3", "inplace", 40)
    kill(listeners(PORT) + [p.pid])
    time.sleep(1)
    b3 = probe("profile_B3", "again", 10)
    i, w, o = seen(b1), seen(b2), seen(b3)
    res["B3_equivalent"] = {
        "installed_generation_bundle": i.get("executing_bundle"),
        "after_swap_bundle": w.get("executing_bundle"),
        "converged_within_one_navigation": (w.get("executing_bundle") != i.get("executing_bundle"))
                                           and len(w.get("loads") or []) > 1,
        "product_marker_after_convergence": w.get("product_reload_key"),
        "offline_after_convergence": {"bundle": o.get("executing_bundle"), "controlled": o.get("controller_now"),
                                      "mounted": o.get("mounted"), "navigation": b3.get("navigation")},
        "still_that_generation_offline": bool(w.get("executing_bundle")) and w.get("executing_bundle") == o.get("executing_bundle"),
        "answered_offline": bool((b3.get("navigation") or {}).get("ok"))}

    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0274-SW 候选的本地等价回归（A 臂形状 / B3 形状）",
           "lane": "B c01d72a3", "mode": "READ-ONLY; no product file changed by this script",
           "surface": {"port": PORT, "dists": {g: str(d) for g, d in DISTS.items()},
                       "never_touched_or_opened": [":4781", ":4782", ":8693", "tunnel", "cnx proxy",
                                                   "_live", "_preview", "HJ-P1 ports 8941/8942"],
                       "unregister_calls": 0, "cache_clear_calls": 0, "demo_reset": 0},
           "reading": res,
           "what_this_is_not": "HJ-P1's verdicts. She owns B1/B2/B3 on the real chain and her instruments "
                               "measure the tunnel path; this is a loopback shape check that my change does "
                               "not break the two arms I was told must not regress."}
    p_ = WORK / "q274sw_regression_equivalents.json"
    p_.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("\n  A:", json.dumps(res["A_equivalent"], ensure_ascii=False)[:300])
    print("  B3:", json.dumps(res["B3_equivalent"], ensure_ascii=False)[:300])
    print("->", p_.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
