"""Stage the ORD-0310 delivery set under its published names, then say what each file is.

Nothing is renamed by hand: the set is a list of (published name, source path), so the readback table
and this staging step agree on names by construction.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
PUB = SC / "pub"
EV = ROOT / "review" / "evidence" / "ord0310"

SET = [
    ("ord0310_keyless_deadline_receipt_r1.json", SC / "ord0310_keyless_deadline_receipt_r1.json"),
    ("ord0310-arms-receipt-r3.json", SC / "arms_receipt_r3.json"),
    ("ord0310-backend-readings.json", SC / "backend_readings.json"),
    ("ord0310-gate-evidence-run335277.json", EV / "keyless_deadline_arms-run335277.json"),
    ("ord0310-gate-evidence-run335765.json", EV / "keyless_deadline_arms-run335765.json"),
    ("ord0310-mergetree-tip-x-candidate.out", SC / "ord0310-mergetree-tip-x-candidate.out"),
    ("ord0310-tip-read.out", SC / "ord0310-tip-read.out"),
    ("ord0310-path-disjointness.tsv", SC / "ord0310-path-disjointness.tsv"),
    ("ord0310-q38r2-on-receipt.json", SC / "ord0310-q38r2-on-receipt.json"),
    ("ord0310-q43r4b-on-block.json", SC / "ord0310-q43r4b-on-block.json"),
    ("ord0310-q43r3-on-block.json", SC / "ord0310-q43r3-on-block.json"),
    ("ord0310-ledger-block.md", SC / "ord0310-ledger-block.md"),
    ("ord0310-tool-make-receipt.py", ROOT / "review" / "ord0310_make_receipt.py"),
    ("ord0310-tool-make-block.py", ROOT / "review" / "ord0310_make_block.py"),
    ("ord0310-tool-kill-arms.py", ROOT / "review" / "ord0310_kill_arms.py"),
    ("ord0310-tool-gauge-landed-block.py", ROOT / "review" / "ord0310_gauge_landed_block.py"),
]

if PUB.exists():
    shutil.rmtree(PUB)
PUB.mkdir(parents=True)


def sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


rows = []
for name, src in SET:
    if not src.exists():
        print(f"ABORT: missing source for {name}: {src}")
        sys.exit(2)
    data = src.read_bytes()
    (PUB / name).write_bytes(data)
    rows.append((name, len(data), sha1(data)))
total = sum(r[1] for r in rows)
print(f"staged {len(rows)} files, {total:,} B into {PUB}")
for name, size, blob in rows:
    print(f"  {name}  {size:,} B  blob {blob}")
