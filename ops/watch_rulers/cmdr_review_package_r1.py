#!/usr/bin/env python3
"""Build one consolidated review package for the arbiter (GPT) from this shift's real artifacts.

Everything inside is copied from files I actually produced; the manifest carries sha256 + byte size +
source path for every member, and the packer REFUSES if any member contains a credential pattern or the
live preview secret (checked by value, never printed).  Nothing here is a paraphrase of a reading: if a
number appears in the narrative files, it is also present in one of the copied artifacts.
"""
import hashlib
import io
import json
import os
import re
import shutil
import zipfile
from datetime import datetime

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921"
LC = os.path.join(ROOT, "live_checks")
OUT_DIR = os.path.join(LC, "review_pkg_20260926_1600")
ZIP = r"C:/Users/仓鼠王/Desktop/CityNexus_审查包_20260926_1600.zip"
AUTH_FILE = r"D:/moodle/_qoder_preview_20260920/run/preview_auth.txt"

# (source path relative to live_checks or absolute, member name inside the package)
EVIDENCE = [
    ("patrol/land_ord0338_1424.json", "receipts/landing_ORD-0338_r1.json"),
    ("patrol/land_ord0351_1426.json", "receipts/landing_ORD-0351_r1.json"),
    ("patrol/land_ord0340_1428.json", "receipts/landing_ORD-0340_r1.json"),
    ("patrol/land_ord0342_1451.json", "receipts/landing_ORD-0342_r1.json"),
    ("patrol/land_ord0345_1551.json", "receipts/landing_ORD-0345_r1.json"),
    ("receipts/deploy_76464263244b7dbf0510ee616b33b3f1cfe36969_0926_143214.json",
     "receipts/deploy_7646426_GREEN_r1.json"),
    ("receipts/deploy_refused_preflight_0926_143031.json", "receipts/deploy_refused_preflight_r1.json"),
    ("_build_dbe6d28_info.json", "receipts/build_dbe6d28_r1.json"),
    ("recut_ord0338_1338.json", "recuts/ord0338_r1.json"),
    ("recut_ord0351_1346.json", "recuts/ord0351_r1.json"),
    ("recut_ord0351_r2_1425.json", "recuts/ord0351_r2.json"),
    ("recut_ord0340_1425.json", "recuts/ord0340_r1.json"),
    ("recut_ord0340_r2_1427.json", "recuts/ord0340_r2.json"),
    ("recut_ord0342_1448.json", "recuts/ord0342_r1.json"),
    ("recut_ord0349_1346.json", "recuts/ord0349_attempt1_refused_by_my_door.json"),
    ("patrol/recut_ord0340_r1.json", "recuts/ord0340_attempt1_refused_auto_merged.json"),
    ("e2e_logs/affected_set_diff_1423.json", "readings/affected_set_diff_ORD-0338.json"),
    ("e2e_logs/affected_set_diff_0345.json", "readings/affected_set_diff_ORD-0345.json"),
    ("patrol/backend_named_ord0340_76464263.json", "readings/backend_named_ORD-0340.json"),
    ("patrol/capability_read_1433.json", "readings/surface_4781_WRONG_SURFACE_r1.json"),
    ("patrol/capability_read_1435.json", "readings/surface_4782_USER_SURFACE_r1.json"),
    ("patrol/jitter_probe_jia_1515.json", "readings/jitter_probe_on_jia.json"),
    ("patrol/jitter_control_1524.json", "readings/jitter_probe_control.json"),
    ("e2e_logs/o349ver_03d7cc95_145349.json", "readings/ORD-0349_recut_to_tip_reading.json"),
    ("patrol/sweep_1401.json", "patrol/local_sweep_1401.json"),
    ("patrol/sweep_1406.json", "patrol/local_sweep_1406.json"),
    ("patrol/sweep_1536.json", "patrol/local_sweep_1536.json"),
    ("patrol/publish_batch_1436.json", "patrol/publish_batch_1436.json"),
    ("patrol/git_mirror_ledger_1510.json", "patrol/git_mirror_ledger_1510.json"),
    ("e2e_logs/o341r3_7e728268_155315.json", "readings/ORD-0341_r3_verification.json"),
    ("e2e_logs/o341r3_7e728268_155315.log", "logs/ORD-0341_r3_verification.log"),
    ("recut_ord0341_r3_1553.json", "recuts/ord0341_r3.json"),
    (os.path.join(ROOT, "HANDOFF_20260926_1200.md"), "handoff/HANDOFF_20260926_1200.md"),
    ("_note_1436_body.txt", "handoff/note_to_owner_1436.txt"),
]
LOGS = [
    ("e2e_logs/o338clr_436d4a36_134402.log", "logs/ORD-0338_clearance_spec.log"),
    ("e2e_logs/o338aff_436d4a36_134457.log", "logs/ORD-0338_affected_candidate.log"),
]
INSTRUMENTS = [
    ("cmdr_e2e_r1.py", "instruments/cmdr_e2e_r1.py"),
    ("cmdr_local_lane_sweep_r1.py", "instruments/cmdr_local_lane_sweep_r1.py"),
    ("cmdr_backend_named_r2.py", "instruments/cmdr_backend_named_r2.py"),
    ("cmdr_git_mirror_r1.py", "instruments/cmdr_git_mirror_r1.py"),
    ("cmdr_recut_r1.py", "instruments/cmdr_recut_r1.py"),
    ("preflight_and_land_r1.py", "instruments/preflight_and_land_r1.py"),
    ("cmdr_capability_read_r2.js", "instruments/cmdr_capability_read_r2.js"),
    ("cmdr_jitter_probe_r1.js", "instruments/cmdr_jitter_probe_r1.js"),
    ("claim_coordinate_check_r4e.py", "instruments/claim_coordinate_check_r4e.py"),
    ("cmdr_exposure_arm_selftest_r1.py", "instruments/cmdr_exposure_arm_selftest_r1.py"),
]
LANE_BLOCKS = [
    (r"D:/moodle/_qoder_ledger_inbox/_processed/d-e345b9d6_1603.md.inserted_153829",
     "lane_blocks/D_1603_UNCHANGED.md"),
    (r"D:/moodle/_qoder_ledger_inbox/n1-1408.md.inserted_manually", "lane_blocks/N1_1408_UNCHANGED.md"),
    (r"D:/moodle/_qoder_ledger_inbox/_processed/b-c01d72a3_1603.md.inserted_161540",
     "lane_blocks/B_1603_UNCHANGED.md"),
    (r"D:/moodle/_qoder_ledger_inbox/_processed/S4-ast-taint_1510.md.inserted_153802",
     "lane_blocks/S4_1510_UNCHANGED.md"),
    (r"D:/moodle/_qoder_ledger_inbox/S2-hermes_1415.md.refused_superseded_by_1603",
     "lane_blocks/S2_1415_refused_by_Q43.md"),
    (r"D:/moodle/_qoder_ledger_inbox/_processed/S2-hermes_1603.md.inserted_161535",
     "lane_blocks/S2_1603_UNCHANGED.md"),
    (r"D:/moodle/_qoder_ledger_inbox/_processed/e-d2305848_1630.md.inserted_161545",
     "lane_blocks/E_1630_UNCHANGED.md"),
]
MY_BLOCKS = [("blk_1442.md", "commander_blocks/CMDR_1442.md")]
FORBID = [re.compile(p, re.I) for p in (
    r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"Authorization:\s*(Basic|Bearer|token)\s+\S", r"cnx-preview-session::",
    r"(api[_-]?key|secret|token)[\"\']?\s*[:=]\s*[\"\'][A-Za-z0-9_\-]{16,}")]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def secret_values():
    try:
        raw = io.open(AUTH_FILE, encoding="utf-8").read().strip().split("\t")
        return [v for v in raw if len(v) >= 6]
    except Exception:
        return []


def scan(raw, name, secrets, hits):
    text = raw.decode("utf-8", "replace")
    for rx in FORBID:
        for m in list(rx.finditer(text))[:2]:
            hits.append({"file": name, "pattern": rx.pattern[:40], "at": m.start()})
    for s in secrets:
        if s in text:
            hits.append({"file": name, "pattern": "LIVE_PREVIEW_SECRET_PRESENT", "at": text.find(s)})
    return hits


def main():
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)
    secrets = secret_values()
    manifest, hits = [], []

    def add(raw, member):
        scan(raw, member, secrets, hits)
        p = os.path.join(OUT_DIR, member.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "wb").write(raw)
        manifest.append({"member": member, "bytes": len(raw), "sha256": sha256(raw)})

    def add_src(src, member):
        path = src if os.path.isabs(src) else os.path.join(LC, src.replace("/", os.sep))
        if not os.path.isfile(path):
            manifest.append({"member": member, "missing": True, "source": path.replace("\\", "/")})
            return
        raw = io.open(path, "rb").read()
        add(raw, member)
        manifest[-1]["source"] = path.replace("\\", "/")
        manifest[-1]["source_sha256"] = sha256(raw)

    for group in (EVIDENCE, LOGS, INSTRUMENTS, LANE_BLOCKS, MY_BLOCKS):
        for src, member in group:
            add_src(src, member)

    # the narrative files live in pkgdocs_1600 so they survive the OUT_DIR rebuild; they are copied in
    # and scanned like every other member.
    docs = os.path.join(LC, "pkgdocs_1600")
    for fn in sorted(os.listdir(docs)) if os.path.isdir(docs) else []:
        p = os.path.join(docs, fn)
        if os.path.isfile(p) and fn.endswith(".md"):
            add_src(p, fn)

    missing = [m["member"] for m in manifest if m.get("missing")]
    if hits:
        print("REFUSED_CREDENTIAL_SCAN — %d hit(s); package not written" % len(hits))
        for h in hits[:8]:
            print("  %s in %s" % (h["pattern"], h["file"]))
        return 8
    doc = {"built_local": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
           "members": len([m for m in manifest if not m.get("missing")]),
           "missing": missing, "credential_hits": 0,
           "secret_scan_patterns": [p.pattern for p in FORBID],
           "files": manifest}
    raw = json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8")
    io.open(os.path.join(OUT_DIR, "MANIFEST.json"), "wb").write(raw)

    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, files in os.walk(OUT_DIR):
            for fn in sorted(files):
                full = os.path.join(folder, fn)
                z.write(full, os.path.relpath(full, OUT_DIR).replace("\\", "/"))
    zraw = io.open(ZIP, "rb").read()
    print(json.dumps({"zip": ZIP.replace("\\", "/"), "zip_bytes": len(zraw),
                      "zip_sha256": sha256(zraw), "members": doc["members"],
                      "missing": missing, "credential_hits": 0}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
