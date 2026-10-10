"""Why did inbox_check's control block flip to RED at 19:31?

Runs the SAME ruler the write door uses (claim_coordinate_check_r4e.py --text <file> --expect-clean) over a
ladder of already-inserted blocks, oldest first, and prints rc + the ruler's own finding lines.
Read-only: no ledger, no inbox writes.
"""
import io
import os
import subprocess
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
PROC = r"D:\moodle\_qoder_ledger_inbox\_processed"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
RULER = "claim_coordinate_check_r4e.py"


def run(path):
    r = subprocess.run([PY, RULER, "--text", path, "--expect-clean"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600, cwd=LC)
    out = (r.stdout or "").strip().splitlines()
    return r.returncode, r.stderr.strip()[:120], out


names = ["cmdr_1850.md.inserted_185506", "cmdr_1918.md.inserted_191957", "Q_1935.md.inserted_192346",
         "rel_0437.md.inserted_192417", "rel_0338.md.inserted_192417"]
print("[%s] ruler=%s cwd=%s  (--text is the file's own bytes, no ledger write)" % (
    time.strftime("%H:%M:%S"), RULER, LC))
for n in names:
    p = os.path.join(PROC, n)
    if not os.path.exists(p):
        cand = [f for f in os.listdir(PROC) if f.startswith(n.split(".")[0]) and ".inserted_" in f]
        print("  MISSING %s  (nearest in _processed: %s)" % (n, ", ".join(sorted(cand)[-3:])))
        continue
    rc, err, out = run(p)
    print("  rc=%d %-38s size=%d  lines=%d  %s" % (rc, n, os.path.getsize(p), len(out),
          "GREEN" if rc == 0 else "RED"))
    if rc:
        for l in out[:6]:
            print("        | %s" % l[:130])
        if err:
            print("        stderr: %s" % err)
print("\nall-sorted listing of _processed newer than 19:00:")
import glob
for p in sorted(glob.glob(os.path.join(PROC, "*.inserted_19*"))):
    print("  %s  %d B" % (os.path.basename(p), os.path.getsize(p)))
