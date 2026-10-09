#!/usr/bin/env python3
"""Publish the 14:36 shift's commander artifacts to the evidence branch, one gated PUT at a time.

Every row is (local file, evidence path).  Nothing here overwrites: `publish_evidence_gated_r1.py`
refuses an existing path unless the bytes are identical (Q57), so re-running after a partial failure
is safe and reports the same blob again.  Rows whose local file is absent are reported MISSING rather
than skipped silently, because a missing reading is a fact about the shift, not a detail.

Deliberately included: the deploy receipt for the REFUSED pre-flight (F_pre NOT_CONFIGURED) next to the
green one, and the wrong-surface capability reading (:4781, eleven 500/text/plain/0 B) next to the
user-surface one (:4782, eleven 200 application/json).  A gate that only publishes its own successes is
not a gate.
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
PUB = os.path.join(ROOT, "publish_evidence_gated_r1.py")
MSG = "commander 1436: ORD-0338 jia + ORD-0351 + ORD-0340 landings, local-store sweep, phone swap"


def blob(path):
    raw = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest(), len(raw)


def pick(pattern):
    fs = sorted(glob.glob(os.path.join(ROOT, pattern)), key=os.path.getmtime)
    return fs[-1].replace(ROOT + os.sep, "").replace("\\", "/") if fs else pattern


def main():
    rows_spec = [
        ("recut_ord0338_1338.json", "evidence/cmdr-recut-ORD-0338-1436/recut_r1.json"),
        ("recut_ord0351_r2_1425.json", "evidence/cmdr-recut-ORD-0351-1436/recut_r2.json"),
        ("recut_ord0340_1425.json", "evidence/cmdr-recut-ORD-0340-1436/recut_r1.json"),
        ("recut_ord0340_r2_1427.json", "evidence/cmdr-recut-ORD-0340-1436/recut_r2.json"),
        ("patrol/land_ord0338_1424.json", "evidence/cmdr-landing-ORD-0338-1424/preflight_r1.json"),
        ("patrol/land_ord0351_1426.json", "evidence/cmdr-landing-ORD-0351-1426/preflight_r1.json"),
        ("patrol/land_ord0340_1428.json", "evidence/cmdr-landing-ORD-0340-1428/preflight_r1.json"),
        ("cmdr_e2e_r1.py", "evidence/cmdr-e2e-runner-1436/cmdr_e2e_r1.py"),
        ("cmdr_local_lane_sweep_r1.py", "evidence/cmdr-local-sweep-1436/cmdr_local_lane_sweep_r1.py"),
        ("patrol/sweep_1406.json", "evidence/cmdr-local-sweep-1436/sweep_r1.json"),
        (pick("e2e_logs/o338clr_436d4a36_1344*.json"), "evidence/cmdr-e2e-ORD-0338-1436/clearance_reading_r1.json"),
        (pick("e2e_logs/o338clr_436d4a36_1344*.log"), "evidence/cmdr-e2e-ORD-0338-1436/clearance_log_r1.txt"),
        (pick("e2e_logs/o338aff_*.json"), "evidence/cmdr-e2e-ORD-0338-1436/affected_candidate_reading_r1.json"),
        (pick("e2e_logs/o338aff_*.log"), "evidence/cmdr-e2e-ORD-0338-1436/affected_candidate_log_r1.txt"),
        (pick("e2e_logs/o338bas_*.json"), "evidence/cmdr-e2e-ORD-0338-1436/affected_base_reading_r1.json"),
        (pick("e2e_logs/o338bas_*.log"), "evidence/cmdr-e2e-ORD-0338-1436/affected_base_log_r1.txt"),
        ("e2e_logs/affected_set_diff_1423.json", "evidence/cmdr-e2e-ORD-0338-1436/affected_set_diff_r1.json"),
        (pick("e2e_logs/o351ver_*.json"), "evidence/cmdr-e2e-ORD-0351-1436/reading_r1.json"),
        (pick("e2e_logs/o351ver_*.log"), "evidence/cmdr-e2e-ORD-0351-1436/log_r1.txt"),
        ("cmdr_backend_named_r2.py", "evidence/cmdr-backend-named-ORD-0340-1436/cmdr_backend_named_r2.py"),
        (pick("patrol/backend_named_ord0340_*.json"), "evidence/cmdr-backend-named-ORD-0340-1436/reading_r1.json"),
        (pick("receipts/deploy_76464263*_143214.json"), "evidence/cmdr-deploy-76464263/deploy_green_r1.json"),
        ("receipts/deploy_refused_preflight_0926_143031.json",
         "evidence/cmdr-deploy-76464263/deploy_refused_preflight_r1.json"),
        ("_build_dbe6d28_info.json", "evidence/cmdr-build-dbe6d28/build_info_r1.json"),
        ("cmdr_capability_read_r1.js", "evidence/cmdr-surface-read-1435/cmdr_capability_read_r1.js"),
        ("cmdr_capability_read_r2.js", "evidence/cmdr-surface-read-1435/cmdr_capability_read_r2.js"),
        ("patrol/capability_read_1433.json", "evidence/cmdr-surface-read-1435/wrong_surface_4781_r1.json"),
        ("patrol/capability_read_1435.json", "evidence/cmdr-surface-read-1435/user_surface_4782_r1.json"),
    ]

    rows = []
    for local, remote in rows_spec:
        p = os.path.join(ROOT, local.replace("/", os.sep))
        if not os.path.isfile(p):
            rows.append({"local": local, "path": remote, "verdict": "MISSING"})
            print("MISSING %s" % local)
            continue
        sh, size = blob(p)
        t0 = time.time()
        r = subprocess.run([sys.executable, PUB, "--local", p, "--path", remote, "--message", MSG],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0
        rows.append({"local": local, "path": remote, "blob": sh, "bytes": size,
                     "rc": r.returncode, "secs": round(time.time() - t0, 1),
                     "tail": out.strip().splitlines()[-2:]})
        print("%-6s %s  %s (%d B) %s" % ("OK" if ok else "FAIL", sh[:12], remote, size,
                                         "" if ok else out.strip().splitlines()[-2:]))
    doc = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": len(rows),
           "n_ok": sum(1 for x in rows if x.get("rc") == 0),
           "n_missing": sum(1 for x in rows if x.get("verdict") == "MISSING"), "rows": rows}
    outp = os.path.join(ROOT, "patrol", "publish_batch_1436.json")
    io.open(outp, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("batch %d/%d ok, missing=%d -> %s" % (doc["n_ok"], doc["n"], doc["n_missing"], outp))
    return 0 if doc["n_ok"] == doc["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
