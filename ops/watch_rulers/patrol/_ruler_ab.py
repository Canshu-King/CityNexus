"""A/B the two doors' Q43 arms: r4e (what lanes are told to run) vs r7 (what ledger_insert_after_r2 actually calls).

Both writers carry the same second bolt (coordinate must cat-file, or the line declares non-retrievability and
the paragraph holds a resolvable coordinate), so the bolt verdict is shared; the Q43 verdict is per-ruler.
Read-only. Prints both verdicts for the same bytes, and only claims skew when BOTH arms produced a reading.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
R4E = "claim_coordinate_check_r4e.py"
R7 = "claim_coordinate_check_r7.py"
sys.path.insert(0, os.path.join(LC, "patrol"))
import bolt_replica as BR


def run(ruler, path):
    r = subprocess.run([PY, ruler, "--text", path, "--expect-clean"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=LC, timeout=900)
    out = (r.stdout or "").strip().splitlines()
    m = re.search(r"Q43_GATE_(GREEN|RED)", " ".join(out))
    n = len([l for l in out if re.match(r"^\s*line \d+ ", l)])
    err = "" if r.returncode in (0, 3) else ((r.stderr or "").strip().splitlines() or ["?"])[-1][:120]
    return r.returncode, ("Q43_GATE_" + m.group(1)) if m else ("rc=%d no-overall-line" % r.returncode), n, err


def sha1(p):
    import hashlib
    return hashlib.sha1(io.open(p, "rb").read()).hexdigest()


rows = []
for p in sorted(glob.glob(os.path.join(INBOX, "*.md"))):
    rows.append(("root", p))
for n in ("rel_0338.md.inserted_192412", "rel_0437.md.inserted_192417", "0383_1838.md.inserted_185321"):
    p = os.path.join(PROC, n)
    if os.path.exists(p):
        rows.append(("inserted1924", p))
print("[%s] rulers: r4e sha1=%s  r7 sha1=%s" % (
    time.strftime("%H:%M:%S"),
    sha1(os.path.join(LC, R4E))[:12], sha1(os.path.join(LC, R7))[:12]))
print("%-13s %-28s %-9s %-5s %-9s %-5s %s" % ("where", "block", "r4e", "f4e", "r7", "f7", "second-bolt"))
skew = 0
for where, p in rows:
    rc4, t4, n4, e4 = run(R4E, p)
    rc7, t7, n7, e7 = run(R7, p)
    try:
        _q, ab, carried, _n = BR.evaluate(p)
    except Exception as ex:
        ab = [("ERR", "", "", "")]
        print("bolt error", ex)
    both_read = (not e4) and (not e7)
    is_skew = both_read and (rc4 == 0) != (rc7 == 0)
    if is_skew:
        skew += 1
    print("%-13s %-28s %-9s %-5d %-9s %-5d abort=%d carried=%d %s" % (
        where, os.path.basename(p)[:28], "GREEN" if rc4 == 0 else "RED", n4,
        "GREEN" if rc7 == 0 else "RED", n7, len(ab), len(carried),
        ("<== 两枚尺判得不一样" if is_skew else ("(r7 无 overall 行: %s)" % e7 if e7 else ""))))
print("\nSUMMARY rows=%d  ruler-skew=%d  at %s" % (len(rows), skew, time.strftime("%H:%M:%S")))
print("若 skew>0：车道被要求跑的尺与写盘门实际跑的尺不同代，同一批字节两边判得不一样——这不是车道的问题。")
