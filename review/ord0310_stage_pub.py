"""Stage the ORD-0310 delivery set under its published names, then say what each file is.

Nothing is renamed by hand: the set is a list of (published name, source path), so the readback table
and this staging step agree on names by construction.
"""
from __future__ import annotations

import hashlib
import json
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
    ("ord0310_keyless_deadline_receipt_r2.json", SC / "ord0310_keyless_deadline_receipt_r2.json"),
    ("ord0310-arms-receipt-r4.json", SC / "arms_receipt_r4.json"),
    ("ord0310-backend-readings-r2.json", SC / "backend_readings_r2.json"),
    ("ord0310-mergetree-tip-x-candidate-r2.out", SC / "r2" / "ord0310-mergetree-tip-x-candidate.out"),
    ("ord0310-tip-read-r2.out", SC / "r2" / "ord0310-tip-read.out"),
    ("ord0310-path-disjointness-r2.tsv", SC / "r2" / "ord0310-path-disjointness.tsv"),
    ("ord0310-mergetree-tip-x-previous-ref.out", SC / "r2" / "ord0310-mergetree-tip-x-previous-ref.out"),
    ("ord0310-left-right-count-trap.out", SC / "r2" / "ord0310-left-right-count-trap.out"),
    ("ord0310-tool-publish.py", ROOT / "review" / "ord0310_publish.py"),
    ("ord0310-tool-gauge-landed-block-r2.py", ROOT / "review" / "ord0310_gauge_landed_block.py"),
    # Instruments go out once per distinct byte-string. The gen-2 names for the other tools are
    # already on the branch holding the bytes they were named for, so they are deliberately NOT
    # restaged: a changed tool under a published name is either a gate REFUSE or, worse, a rewritten
    # audit instrument. Which name holds the current bytes is decided by comparing the live git blob
    # against the directory listing, not by guessing.
    ("ord0310-tool-make-post-r3.py", ROOT / "review" / "ord0310_make_post.py"),
    ("ord0310-tool-readback-r3.py", ROOT / "review" / "ord0310_readback.py"),
    ("ord0310-q38r2-on-receipt-r2.json", SC / "ord0310-q38r2-on-receipt-r2.json"),
    ("ord0310-q43r4b-on-block-r2.json", SC / "ord0310-q43r4b-on-block-r2.json"),
    ("ord0310-q43r3-on-block-r2.json", SC / "ord0310-q43r3-on-block-r2.json"),
    ("ord0310-ledger-block-r2.md", SC / "ord0310-ledger-block-r2.md"),
    ("ord0310-post-body-r2.md", SC / "ord0310-post-body-r2.md"),
    ("ord0310-q43r4b-on-post-r2.json", SC / "ord0310-q43r4b-on-post-r2.json"),
    ("ord0310-q43r3-on-post-r2.json", SC / "ord0310-q43r3-on-post-r2.json"),
]

# generation 3: measured on the generation the commander landed
R3 = SC / "r3"
SET += [
    ("ord0310_keyless_deadline_receipt_r3.json", SC / "ord0310_keyless_deadline_receipt_r3.json"),
    ("ord0310-arms-receipt-r5.json", SC / "arms_receipt_r5.json"),
    ("ord0310-backend-readings-r3.json", SC / "backend_readings_r3.json"),
    ("ord0310-signal-vs-deadline-proof.out", R3 / "ord0310-signal-vs-deadline-proof.out"),
    ("ord0310-mergetree-tip-x-candidate-r3.out", R3 / "ord0310-mergetree-tip-x-candidate.out"),
    ("ord0310-tip-read-r3.out", R3 / "ord0310-tip-read.out"),
    ("ord0310-path-disjointness-r3.tsv", R3 / "ord0310-path-disjointness.tsv"),
    ("ord0310-q38r2-on-receipt-r3.json", SC / "ord0310-q38r2-on-receipt-r3.json"),
    ("ord0310-q43r4b-on-block-r3.json", SC / "ord0310-q43r4b-on-block-r3.json"),
    ("ord0310-q43r3-on-block-r3.json", SC / "ord0310-q43r3-on-block-r3.json"),
    ("ord0310-ledger-block-r3.md", SC / "ord0310-ledger-block-r3.md"),
    ("ord0310-post-body-r3.md", SC / "ord0310-post-body-r3.md"),
    ("ord0310-q43r4b-on-post-r3.json", SC / "ord0310-q43r4b-on-post-r3.json"),
    ("ord0310-q43r3-on-post-r3.json", SC / "ord0310-q43r3-on-post-r3.json"),
    ("ord0310-readback-r5.json", SC / "ord0310-readback-r5.json"),
    ("ord0310-tool-make-receipt-r3.py", ROOT / "review" / "ord0310_make_receipt.py"),
    ("ord0310-tool-make-block-r3.py", ROOT / "review" / "ord0310_make_block.py"),
    # the arms driver gained the seventh (two-sided signal-vs-deadline) arm, so its current bytes go
    # out under a new name; the gen-2 name keeps the bytes that generation's receipt was built with
    ("ord0310-tool-kill-arms-r2.py", ROOT / "review" / "ord0310_kill_arms.py"),
    ("ord0310-tool-pub-names-r4.py", ROOT / "review" / "ord0310_pub_names.py"),
    ("ord0310-tool-stage-pub-r4.py", ROOT / "review" / "ord0310_stage_pub.py"),
    ("ord0310-tool-signal-proof.py", ROOT / "review" / "ord0310_signal_proof.py"),
]

# the gate's own per-run evidence files are named from the arms receipt, never typed here
_arms = json.loads((SC / "arms_receipt_r5.json").read_text(encoding="utf-8"))
for _rid in [_arms["clean_round"]["runId"]] + [a["attempt"]["runId"] for a in _arms["arms"]]:
    _src = EV / f"keyless_deadline_arms-{_rid}.json"
    if _src.exists():
        SET.append((f"ord0310-gate-evidence-{_rid}.json", _src))
    else:
        print(f"NOTE: no gate evidence file for runId {_rid} ({_src})")

if PUB.exists():
    shutil.rmtree(PUB)
PUB.mkdir(parents=True)


def sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


rows = []
for name, src in SET:
    if not src.exists():
        print(f"SKIP (not produced yet): {name} <- {src}")
        continue
    data = src.read_bytes()
    (PUB / name).write_bytes(data)
    rows.append((name, len(data), sha1(data)))
total = sum(r[1] for r in rows)
print(f"staged {len(rows)} files, {total:,} B into {PUB}")
for name, size, blob in rows:
    print(f"  {name}  {size:,} B  blob {blob}")
