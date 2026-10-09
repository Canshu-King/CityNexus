#!/usr/bin/env python3
"""Publish this batch of commander artifacts through the GIT write path.

The Contents-API PUT started answering `401 Bad credentials` at 15:07 while its GET still answered 200,
so the write channel in use here is `cmdr_git_mirror_r1.py` (SSH over 443).  Every row still has to come
back BYTE-IDENTICAL from a fresh fetch of the branch, and Q57 still applies: an existing evidence path
whose bytes differ is a refusal, not a rewrite.

Rows are (local file, evidence path).  Nothing here deletes or overwrites a published path.
"""
import glob
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
MIR = os.path.join(ROOT, "cmdr_git_mirror_r1.py")
MSG = "commander 1558: ORD-0342/0345/0341 landings, affected-set diffs, jitter probes, git write path"


def one(local, remote):
    p = os.path.join(ROOT, local.replace("/", os.sep))
    if not os.path.isfile(p):
        return {"local": local, "path": remote, "verdict": "MISSING"}
    r = subprocess.run([sys.executable, MIR, "--file", p,
                        "--repo-path", remote, "--branch", "commander/control",
                        "--message", MSG],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    row = {"local": local, "path": remote, "rc": r.returncode, "tail": out.strip().splitlines()[-2:]}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                j = json.loads(line)
                row.update({"blob": j.get("readback_blob"), "bytes": j.get("readback_size"),
                            "commit": j.get("pushed_commit"), "byte_equal": j.get("byte_equal")})
            except Exception:
                pass
    row["verdict"] = "OK" if row.get("byte_equal") else ("ALREADY" if r.returncode == 0 else "FAIL")
    print("%-8s %-62s %s" % (row["verdict"], remote, (row.get("blob") or "")[:12]))
    return row


def main():
    rows_spec = [
        ("patrol/land_ord0342_1451.json", "evidence/cmdr-landing-ORD-0342-1451/preflight_r1.json"),
        ("patrol/land_ord0345_1551.json", "evidence/cmdr-landing-ORD-0345-1551/preflight_r1.json"),
        ("patrol/land_ord0341_1555.json", "evidence/cmdr-landing-ORD-0341-1555/preflight_r1.json"),
        ("recut_ord0342_1448.json", "evidence/cmdr-recut-ORD-0342-1558/recut_r1.json"),
        ("recut_ord0341_r3_1553.json", "evidence/cmdr-recut-ORD-0341-1558/recut_r3.json"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o342ver_*.json"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0342-1558/reading_r1.json"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o342ver_*.log"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0342-1558/log_r1.txt"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o345aff_*.json"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0345-1558/affected_reading_r1.json"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o345aff_*.log"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0345-1558/affected_log_r1.txt"),
        ("e2e_logs/affected_set_diff_0345.json", "evidence/cmdr-e2e-ORD-0345-1558/affected_set_diff_r1.json"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o341r3_*.json"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0341-1558/reading_r1.json"),
        (os.path.relpath(sorted(glob.glob("e2e_logs/o341r3_*.log"))[-1], ROOT).replace("\\", "/"),
         "evidence/cmdr-e2e-ORD-0341-1558/log_r1.txt"),
        ("cmdr_jitter_probe_r1.js", "evidence/cmdr-jitter-probe-1558/cmdr_jitter_probe_r1.js"),
        ("receipts/" + os.path.basename(sorted(glob.glob("receipts/deploy_7e72826*.json"))[-1]),
         "evidence/cmdr-deploy-7e728263/deploy_green_r1.json"),
        ("_build_7e72826_info.json", "evidence/cmdr-build-7e728263/build_info_r1.json"),
        ("cmdr_git_mirror_r1.py", "evidence/cmdr-git-write-1558/cmdr_git_mirror_r1.py"),
        ("cmdr_capability_read_r2.js", "evidence/cmdr-surface-read-1435/cmdr_capability_read_r2_fixed.js"),
    ]
    rows = [one(l, r) for l, r in rows_spec]
    doc = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": len(rows),
           "n_ok": sum(1 for x in rows if x["verdict"] in ("OK", "ALREADY")), "rows": rows}
    outp = os.path.join(ROOT, "patrol", "publish_batch_1558.json")
    with open(outp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("batch %d/%d ok -> %s" % (doc["n_ok"], doc["n"], outp))
    return 0 if doc["n_ok"] == doc["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
