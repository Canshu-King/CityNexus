"""One place that says what each local artifact is called once published.

Two tools need the same answer - the prose generator (so a sentence cites the path an auditor can
actually GET) and the staging step (so it publishes under exactly those names). Naming them in prose
in both places is how a quote and a publish drift apart, so the map lives here.
"""
from __future__ import annotations

DIRNAME = "evidence/ord0288-keyless-deadline"

# local scratch filename -> published filename (generation is part of the name; nothing is overwritten)
PUB = {
    "ord0310_keyless_deadline_receipt_r1.json": "ord0310_keyless_deadline_receipt_r1.json",
    "ord0310_keyless_deadline_receipt_r2.json": "ord0310_keyless_deadline_receipt_r2.json",
    "arms_receipt_r3.json": "ord0310-arms-receipt-r3.json",
    "arms_receipt_r4.json": "ord0310-arms-receipt-r4.json",
    "backend_readings.json": "ord0310-backend-readings.json",
    "backend_readings_r2.json": "ord0310-backend-readings-r2.json",
    "q38r2-on-receipt.json": "ord0310-q38r2-on-receipt.json",
    "ord0310-q38r2-on-receipt-r2.json": "ord0310-q38r2-on-receipt-r2.json",
    "ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate.out",
    "ord0310-tip-read.out": "ord0310-tip-read.out",
    "ord0310-path-disjointness.tsv": "ord0310-path-disjointness.tsv",
    "r2/ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate-r2.out",
    "r2/ord0310-tip-read.out": "ord0310-tip-read-r2.out",
    "r2/ord0310-path-disjointness.tsv": "ord0310-path-disjointness-r2.tsv",
    "r2/ord0310-mergetree-tip-x-previous-ref.out": "ord0310-mergetree-tip-x-previous-ref.out",
    "r2/ord0310-left-right-count-trap.out": "ord0310-left-right-count-trap.out",
    "ord0310-q43r4b-on-block.json": "ord0310-q43r4b-on-block.json",
    "ord0310-q43r3-on-block.json": "ord0310-q43r3-on-block.json",
    "ord0310-q43r4b-on-block-r2.json": "ord0310-q43r4b-on-block-r2.json",
    "ord0310-q43r3-on-block-r2.json": "ord0310-q43r3-on-block-r2.json",
    "ord0310-ledger-block.md": "ord0310-ledger-block.md",
    "ord0310-ledger-block-r2.md": "ord0310-ledger-block-r2.md",
    "ord0310-post-body.md": "ord0310-post-body.md",
    "ord0310-post-body-r2.md": "ord0310-post-body-r2.md",
    "ord0310-q43r4b-on-post.json": "ord0310-q43r4b-on-post.json",
    "ord0310-q43r3-on-post.json": "ord0310-q43r3-on-post.json",
    "ord0310-q43r4b-on-post-r2.json": "ord0310-q43r4b-on-post-r2.json",
    "ord0310-q43r3-on-post-r2.json": "ord0310-q43r3-on-post-r2.json",
    "ord0310-readback-r1.json": "ord0310-readback-r1.json",
    "ord0310-readback-r2.json": "ord0310-readback-r2.json",
    "ord0310-tool-make-receipt.py": "ord0310-tool-make-receipt.py",
    "ord0310-tool-make-block.py": "ord0310-tool-make-block.py",
    "ord0310-tool-make-receipt-r2.py": "ord0310-tool-make-receipt-r2.py",
    "ord0310-tool-make-block-r2.py": "ord0310-tool-make-block-r2.py",
    "ord0310-tool-kill-arms.py": "ord0310-tool-kill-arms.py",
    "ord0310-tool-gauge-landed-block.py": "ord0310-tool-gauge-landed-block.py",
    # the r1 bytes are frozen on the branch, so a changed instrument goes out under a new name
    "ord0310-tool-gauge-landed-block-r2.py": "ord0310-tool-gauge-landed-block-r2.py",
    "ord0310-tool-stage-pub-r2.py": "ord0310-tool-stage-pub-r2.py",
    "ord0310-tool-readback-r2.py": "ord0310-tool-readback-r2.py",
    "ord0310-tool-pub-names.py": "ord0310-tool-pub-names.py",
    "ord0310-tool-pub-names-r2.py": "ord0310-tool-pub-names-r2.py",
    "ord0310-tool-publish.py": "ord0310-tool-publish.py",
    "ord0310-tool-make-post-r2.py": "ord0310-tool-make-post-r2.py",
    "ord0310-tool-stage-pub-r3.py": "ord0310-tool-stage-pub-r3.py",
    "ord0310-readback-r3.json": "ord0310-readback-r3.json",
    "ord0310-publish-log-r2.json": "ord0310-publish-log-r2.json",
}

# per-run gate evidence, one file per arm, both generations (run ids come from the arms receipts)
for _run in ("335277", "335765", "339785", "339864", "339947", "340026", "340105", "340186", "340266"):
    PUB[f"__ev__{_run}"] = f"ord0310-gate-evidence-run{_run}.json"


def published(local: str) -> str:
    if local not in PUB:
        raise SystemExit(f"ABORT: {local} has no published name in review/ord0310_pub_names.py")
    return PUB[local]


def cite(local: str) -> str:
    return f"{DIRNAME}/{PUB[local]}"
