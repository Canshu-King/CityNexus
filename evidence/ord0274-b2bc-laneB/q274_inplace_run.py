"""ORD-0274-SW measurement v2: the swap happens UNDERNEATH an open document.

My first run killed the origin between navigations, so the second navigation was a fresh document and it
got the new shell by definition - it could not answer the B2 question. This version keeps ONE process,
ONE port and ONE origin alive the whole time: the page opens against the old generation, then the page
itself asks the origin to start serving the new generation and asks the browser to check for an updated
worker, and I sample the still-open document once a second for 40 s.

What that measures, per reading:
  - does the document change bundle by itself (loads increments + bundle changes) -> product converges
  - or does controllerchange fire while the document keeps executing the old module -> the bail-out
    in main.tsx:1718-1720 is real, and a second navigation is what it costs

No product file is edited here. HJ-P1 remains the verifier of 0274's B cells.
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
PORT = 8452
BASE = f"http://127.0.0.1:{PORT}"
DETACHED = 0x00000008 | 0x00000200
DISTS = {"old": pathlib.Path(os.environ.get("CNX_GEN_OLD_DIR")
                             or r"D:\moodle\_qoder_b_ord0268_20260923\genB\frontend\dist_ord0268"),
         "new": pathlib.Path(os.environ.get("CNX_GEN_NEW_DIR")
                             or r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_ord0267b")}
PROFILE = WORK / "profile_inplace"


def listeners(port):
    o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout
    return sorted({m.group(1) for m in re.finditer(rf"TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(\d+)", o)})


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def probe(phase, window=40):
    out = WORK / f"inplace_{phase}.json"
    out.unlink(missing_ok=True)
    r = subprocess.run(["node", str(SPIKE / "q274_transition_probe.js"), "--base", BASE,
                        "--profile", str(PROFILE), "--out", str(out), "--phase", phase,
                        "--window", str(window)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=460)
    line = ((r.stdout or "").strip().splitlines() or [f"NO OUTPUT rc={r.returncode} {(r.stderr or '')[-220:]}"])[-1]
    print(f"    {line[:210]}")
    return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"missing": True,
                                                                           "stderr": (r.stderr or "")[-300:]}


def module_of(dist):
    html = (dist / "index.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'src="(/assets/index-[A-Za-z0-9_-]+\.js)"', html)
    return m.group(1) if m else None


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PROFILE, ignore_errors=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    (WORK / "inplace_origin.log").unlink(missing_ok=True)
    if listeners(PORT):
        print(f"ABORT: :{PORT} already answers {listeners(PORT)}")
        return 2
    mods = {g: module_of(d) for g, d in DISTS.items()}
    print(f"modules: old={mods['old']} new={mods['new']}")
    if mods["old"] == mods["new"] or not all(mods.values()):
        raise SystemExit("ABORT: the two generations are indistinguishable by module URL")

    origin = subprocess.Popen([PY, str(SPIKE / "q274_gen_origin.py"), "--gen", "old", "--gen2", "new",
                               "--port", str(PORT), "--log", str(WORK / "inplace_origin.log")],
                              env=dict(os.environ) | {"CNX_GEN_OLD_DIR": str(DISTS["old"]),
                                                      "CNX_GEN_NEW_DIR": str(DISTS["new"])},
                              stdout=open(WORK / "inplace_origin.out", "a", encoding="utf-8"),
                              stderr=subprocess.STDOUT, creationflags=DETACHED)
    try:
        for _ in range(30):
            if listeners(PORT):
                break
            time.sleep(1)
        install = probe("install", 8)
        si = install.get("seen") or {}
        if si.get("executing_bundle") != mods["old"]:
            raise SystemExit(f"ABORT: first visit is not running the old bundle ({si.get('executing_bundle')})")
        print(f"    old document open: bundle={si.get('executing_bundle')} controller={si.get('controller_now')}")
        watch = probe("inplace", 40)
        w = watch.get("seen") or {}
        samples = watch.get("samples") or []
        bundles = [s.get("bundle") for s in samples if s.get("bundle")]
        flipped_in_document = bool(bundles) and bundles[-1] == mods["new"]
        loads_first_last = [(samples[0].get("loads"), samples[-1].get("loads"))] if samples else None
        reload_keys = sorted({str(s.get("reload_key")) for s in samples if "reload_key" in s})
        second = None
        if not flipped_in_document:
            print("    the open document did not change by itself; taking one more ordinary navigation")
            second = probe("again", 10)
        navigations = 1 if flipped_in_document else (2 if second else None)
        ev = w.get("events") or []
        out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
               "order": "ORD-0274-SW 前置测量 v2（只读）：换代会自己收敛吗",
               "lane": "B c01d72a3", "mode": "READ-ONLY; no product file edited; no unregister, no cache clear",
               "why_v2": "v1 killed the origin between navigations, so the second navigation was a fresh "
                         "document and could not answer the question; that reading is kept "
                         "(q274sw_transition_measurement.json) and superseded here, not averaged in",
               "surface": {"origin_port": PORT, "one_process_one_port_one_origin": True,
                           "modules": mods,
                           "swap_trigger": "the page itself: GET /__admin/swap then registration.update()",
                           "document_under_test": "the one that was already open before the swap",
                           "never_touched_or_opened": [":4781", ":4782", ":8693", "tunnel", "cnx proxy",
                                                       "_live", "_preview", "HJ-P1 ports 8941/8942"],
                           "demo_reset": 0, "unregister_calls": 0, "cache_clear_calls": 0},
               "install_phase": {"seen": si, "console_errors": install.get("console_errors")},
               "inplace_phase": {"swap_request": watch.get("swap_request"), "samples": samples,
                                 "events": ev, "seen_at_end": w,
                                 "page_errors": watch.get("page_errors")},
               "second_navigation": (second or {}).get("seen"),
               "derived": {"controllerchange_events": len([e for e in ev if e.get("kind") == "controllerchange"]),
                           "distinct_controller_scriptURLs": sorted({str(s.get("controller")) for s in samples}),
                           "document_changed_bundle_without_navigation": flipped_in_document,
                           "load_ids_first_to_last": loads_first_last,
                           "product_reload_marker_values_seen": reload_keys,
                           "registrations_at_end": w.get("registrations"),
                           "bundle_at_end_of_open_document": (bundles[-1] if bundles else None),
                           "bundle_after_second_navigation": ((second or {}).get("seen") or {}).get("executing_bundle"),
                           "navigations_needed_for_convergence": navigations},
               "verdict_for_me": (
                   "OPEN_DOCUMENT_DID_NOT_CONVERGE__A_SECOND_NAVIGATION_IS_REQUIRED"
                   if not flipped_in_document else
                   "OPEN_DOCUMENT_CONVERGED_ON_ITS_OWN"),
               "what_this_is_not": "Not HJ-P1's B2 verdict and not a self-signed derived_result: hers runs "
                                   "the real chain through the tunnel and she owns that cell. This is loopback "
                                   "evidence about the mechanism, so I know what to change before I change it."}
        p = WORK / os.environ.get("CNX_MEASURE_NAME", "q274sw_inplace_measurement.json")
        out["surface"]["generation_dirs"] = {g: str(d) for g, d in DISTS.items()}
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
        print(f"\n  controllerchange={len([e for e in ev if e.get('kind') == 'controllerchange'])} "
              f"scriptURLs={out['derived']['distinct_controller_scriptURLs']} "
              f"loads {loads_first_last} reload_keys={reload_keys}")
        print(f"  open document changed by itself: {flipped_in_document}; "
              f"bundle at end={out['derived']['bundle_at_end_of_open_document']}; "
              f"after 2nd nav={out['derived']['bundle_after_second_navigation']}")
        print("  verdict:", out["verdict_for_me"])
        print("->", p.name)
    finally:
        kill(listeners(PORT) + [origin.pid])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
