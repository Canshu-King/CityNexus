"""Freeze verification for the R5 night (run at/after 08:30, before 09:00).

Three checks, no mutation:
  1. remote branch head == local HEAD (nobody pushed past us overnight);
  2. the six classroom deliverables on disk are byte-identical to the pushed
     blobs (nobody touched them in place);
  3. a real open of all six (se_r43_eye_r2.py logic: maximised window,
     PrintWindow) still succeeds - the "opens for the teacher" property.

Writes Evidence/scripts/se_r43_freeze_r1.json and exits non-zero on any
mismatch. Run with the system python that has pywin32+PIL (python, not venv).
"""
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\moodle\CityNexus"
BRANCH = "review/se-coursework-deliverables-r1"
BASE = "deliverables/SoftwareEngineering_2026/Classroom"
FILES = ["Teacher_01_System_Overview.vsdx",
         "Teacher_02_Agent_User_Flow.vsdx",
         "Teacher_01_System_Overview_EN.vsdx",
         "Teacher_02_Agent_User_Flow_EN.vsdx",
         "Teacher_03_Project_Overview_R4.mpp",
         "Teacher_03_Project_Overview_R4_EN.mpp"]
OUT = os.path.join(HERE, "se_r43_freeze_r1.json")
T0 = time.time()


def log(m):
    print("[%5.1fs] %s" % (time.time() - T0, m), flush=True)


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, shell=True,
                      capture_output=True, text=True).stdout.strip()
remote = subprocess.run(["git", "ls-remote", "origin", BRANCH], cwd=REPO,
                        shell=True, capture_output=True, text=True).stdout.split()[0]
pushed_synced = (head == remote)
log("local HEAD %s / remote %s (synced=%s)" % (head[:9], remote[:9], pushed_synced))

files = {}
all_match = True
for rel in FILES:
    blob = subprocess.run(["git", "cat-file", "blob", "HEAD:" + BASE + "/" + rel],
                          cwd=REPO, shell=True, capture_output=True).stdout
    disk = open(os.path.join(REPO, BASE, rel), "rb").read()
    match = sha(blob) == sha(disk)
    all_match = all_match and match
    files[rel] = {"sha16": sha(disk), "matchesHead": match}
    log("%-42s %s %s" % (rel, sha(disk), "OK" if match else "MISMATCH"))

log("invoking se_r43_eye_r2.py for the real-open pass (2 vsdx + 2 mpp windows + "
    "2 mpp)...")
eye = subprocess.run([sys.executable, os.path.join(HERE, "se_r43_eye_r2.py")],
                     cwd=HERE, capture_output=True, text=True)
tail = [l for l in (eye.stdout or "").splitlines() if "EYE PASS" in l]
log("eye: %s" % (tail[-1] if tail else "no verdict line"))
eye_ok = eye.returncode == 0

report = {"localHead": head[:12], "remoteHead": remote[:12],
          "pushedSynced": pushed_synced, "files": files,
          "allFilesMatchHead": all_match, "eyeReturnCode": eye.returncode,
          "eyeVerdict": tail[-1] if tail else "", "ranAt": time.strftime(
              "%Y-%m-%d %H:%M:%S")}
json.dump(report, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
verdict = pushed_synced and all_match and eye_ok
log("FREEZE CHECK %s" % ("OK" if verdict else "REFUSED"))
sys.exit(0 if verdict else 1)
