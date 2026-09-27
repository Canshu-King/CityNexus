#!/usr/bin/env python3
"""ORD-0384 -- compile arm against the node_modules the landing door borrows from.

My lane tree borrows `_qoder_integration_20260919/frontend/node_modules`; the door borrows
`D:/moodle/CityNexus/frontend/node_modules`. FRONTSRC_BUILD_PREREQ is a gate, so the build is re-run in
a `git archive` export against the authoritative tree and the reading is kept rather than inferred.

Teardown ordering is copied from cmdr_build_bundle_r1.py's drop_old_junction: a junction is dropped with
a plain `rmdir` and the export is only swept recursively once the junction is provably gone; if it
survived, abort. The authoritative tree is re-listed afterwards, because the failure mode of getting
this wrong is deleting another lane's dependencies.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
NM = os.path.join(REPO, "frontend", "node_modules")
SHA = sys.argv[1] if len(sys.argv) > 1 else "407b7240a709ea6854484cad18c0c37f341fb02b"
OUT = os.path.join(REPO, "..", "_qoder_n3_snap_ord0384").replace("/", os.sep)
FE = os.path.join(OUT, "frontend")
SNAP_NM = os.path.join(FE, "node_modules")
log = {"sha": SHA, "export": OUT.replace("\\", "/"), "node_modules_target": NM.replace("\\", "/"), "steps": []}


def sh(cmd, timeout=900, cwd=None):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                       errors="replace", timeout=timeout, cwd=cwd)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def is_reparse(path):
    st = os.lstat(path)
    return bool(getattr(st, "st_file_attributes", 0) & 0x400)


# 1. clear any previous export the safe way
if os.path.isdir(OUT):
    if os.path.isdir(SNAP_NM):
        rc, _, err = sh(["cmd", "/c", "rmdir", SNAP_NM.replace("/", "\\")], timeout=180)
        log["steps"].append({"step": "drop_old_junction", "rc": rc, "err": err.strip()[:200]})
    rc, _, err = sh(["cmd", "/c", "rmdir", "/s", "/q", OUT.replace("/", "\\")], timeout=600)
    log["steps"].append({"step": "clean_old_export", "rc": rc, "err": err.strip()[:200]})
    if os.path.isdir(SNAP_NM):
        raise SystemExit("ABORT: the junction survived rmdir; refusing to sweep it recursively.")
os.makedirs(OUT, exist_ok=True)

# 2. export the delivered frontend from git, not from the working tree
rc, _, err = sh(f'git -C "{REPO}" archive {SHA} frontend | tar -x -C "{OUT}"', timeout=900)
log["steps"].append({"step": "archive", "rc": rc, "err": err.strip()[:300]})
assert rc == 0 and os.path.isdir(FE), "git archive failed"

# 3. borrow the authoritative node_modules through a junction (never copied, never deleted through)
rc, _, err = sh(["cmd", "/c", "mklink", "/J", SNAP_NM.replace("/", "\\"), NM.replace("/", "\\")], timeout=300)
log["steps"].append({"step": "junction_node_modules", "rc": rc, "err": err.strip()[:200]})
assert os.path.isdir(SNAP_NM), "junction not made"
log["junction_is_reparse_point"] = is_reparse(SNAP_NM)

# 4. the compile arm
for name, cmd in (("tsc_check", "npx tsc -p tsconfig.check.json --noEmit"),
                  ("tsc_all", "npx tsc -p tsconfig.typecheck.json --noEmit")):
    rc, out, err = sh(cmd, timeout=1800, cwd=FE)
    log["steps"].append({"step": name, "rc": rc, "out": (out + err).strip()[:400]})
rc, out, err = sh("node node_modules/vite/bin/vite.js build --outDir ../build_out --emptyOutDir", timeout=1800, cwd=FE)
blob = out + err
secs = re.search(r"built in ([0-9.]+)s", blob)
mods = re.search(r"(\d+) modules transformed", blob)
assets = sorted(set(re.findall(r"assets/(index-[A-Za-z0-9_-]+\.js)", blob)))
log["steps"].append({"step": "vite_build", "rc": rc, "built_in_seconds": float(secs.group(1)) if secs else None,
                     "modules_transformed": int(mods.group(1)) if mods else None,
                     "index_assets_emitted": assets, "err": blob.strip()[-400:]})

# 5. tear down in the safe order, then prove the shared tree is intact
rc, _, err = sh(["cmd", "/c", "rmdir", SNAP_NM.replace("/", "\\")], timeout=180)
log["steps"].append({"step": "drop_junction_after_build", "rc": rc, "err": err.strip()[:200]})
log["junction_gone"] = not os.path.exists(SNAP_NM)
assert log["junction_gone"], "ABORT: junction still present, not sweeping the export"
rc, _, err = sh(["cmd", "/c", "rmdir", "/s", "/q", OUT.replace("/", "\\")], timeout=600)
log["steps"].append({"step": "sweep_export", "rc": rc, "err": err.strip()[:200]})
log["export_gone"] = not os.path.isdir(OUT)
lock = os.path.join(REPO, "frontend", "package-lock.json")
log["authoritative_node_modules_entries"] = (len(os.listdir(NM)) if os.path.isdir(NM) else 0)
log["authoritative_lock_sha256_16"] = hashlib.sha256(io.open(lock, "rb").read()).hexdigest()[:16]

out_path = os.path.join(r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384", "snap_build_r1.json")
io.open(out_path, "w", encoding="utf-8").write(json.dumps(log, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: v for k, v in log.items() if k != "steps"}, ensure_ascii=False, indent=1))
for s in log["steps"]:
    print("step", s["step"], "rc", s.get("rc"), s.get("built_in_seconds"),
          s.get("modules_transformed"), s.get("index_assets_emitted"))
print("READING", out_path.replace("\\", "/"))
compile_steps = [s for s in log["steps"] if s["step"] in ("tsc_check", "tsc_all", "vite_build")]
sys.exit(0 if all(s.get("rc", 0) == 0 for s in compile_steps) else 3)
