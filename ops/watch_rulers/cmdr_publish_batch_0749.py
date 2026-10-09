"""Publish this shift's commander artifacts to the evidence branch, one gated PUT at a time.

Every row is (local file, evidence path).  Nothing here overwrites: `publish_evidence_gated_r1.py`
refuses an existing path unless the bytes are identical (Q57), so re-running this script after a
partial failure is safe and reports the same blob again.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
PUB = os.path.join(ROOT, "publish_evidence_gated_r1.py")

ROWS = [
    ("patrol/recut_ord0323_r1.json", "evidence/cmdr-recut-tool-0738/ord0323_recut_r1.json"),
    ("patrol/recut_ord0339_r2.json", "evidence/cmdr-recut-tool-0738/ord0339_recut_r2.json"),
    ("evidence/cmdr-recut-tool/selftest_r3.json", "evidence/cmdr-recut-tool-0738/selftest_r3.json"),
    ("cmdr_recut_r1.py", "evidence/cmdr-recut-tool-0738/cmdr_recut_r1.py"),
    ("cmdr_recut_selftest_r1.py", "evidence/cmdr-recut-tool-0738/cmdr_recut_selftest_r1.py"),
    ("patrol/land_ord0323_r1.json", "evidence/cmdr-landing-ORD-0323-0741/preflight_r1.json"),
    ("patrol/land_ord0339_r1.json", "evidence/cmdr-landing-ORD-0339-0742/preflight_r1.json"),
    ("_build_ord0323_0339_info.json", "evidence/cmdr-build-ord0323-0339/build_info_r1.json"),
    ("cmdr_build_bundle_r1.py", "evidence/cmdr-build-ord0323-0339/cmdr_build_bundle_r1.py"),
    ("cmdr_render_check_r1.py", "evidence/cmdr-render-check-0747/cmdr_render_check_r1.py"),
    ("evidence_local/render_c740f45d/render_r1.json",
     "evidence/cmdr-render-check-0747/render_reading_c740f45d_r1.json"),
    ("evidence_local/render_c740f45d/render_0_-check.png",
     "evidence/cmdr-render-check-0747/render_c740f45d_390x844_r1.png"),
    ("patrol/r6_tip_c740f45d.json", "evidence/cmdr-q64-census-0749/r6_tree_tip_c740f45d.json"),
]

DEPLOY = sorted(f for f in os.listdir(os.path.join(ROOT, "receipts"))
                if f.startswith("deploy_c740f45d") and f.endswith(".json"))
if DEPLOY:
    ROWS.insert(7, ("receipts/" + DEPLOY[-1], "evidence/cmdr-deploy-c740f45d/deploy_r1.json"))


def blob(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest(), len(raw)


def main():
    rows = []
    for local, remote in ROWS:
        p = os.path.join(ROOT, local.replace("/", os.sep))
        if not os.path.isfile(p):
            rows.append({"local": local, "verdict": "MISSING"})
            print("MISSING %s" % local)
            continue
        sh, size = blob(p)
        t0 = time.time()
        r = subprocess.run([sys.executable, PUB, "--local", p, "--path", remote,
                            "--message", "commander 0749: ORD-0323/0339 landings, bundle swap, "
                                         "render check, Q64 census"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0
        rows.append({"local": local, "path": remote, "blob": sh, "bytes": size,
                     "rc": r.returncode, "secs": round(time.time() - t0, 1),
                     "tail": out.strip().splitlines()[-3:]})
        print("%-6s %s  %s (%d B) %s" % ("OK" if ok else "FAIL", sh[:12], remote, size,
                                         "" if ok else out.strip().splitlines()[-2:]))
    doc = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": len(rows),
           "n_ok": sum(1 for x in rows if x.get("rc") == 0), "rows": rows}
    out = os.path.join(ROOT, "patrol", "publish_batch_0749.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("batch %d/%d ok -> %s" % (doc["n_ok"], doc["n"], out))
    return 0 if doc["n_ok"] == doc["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
