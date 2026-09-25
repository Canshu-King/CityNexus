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
    "arms_receipt_r5.json": "ord0310-arms-receipt-r5.json",
    "backend_readings.json": "ord0310-backend-readings.json",
    "backend_readings_r2.json": "ord0310-backend-readings-r2.json",
    "backend_readings_r3.json": "ord0310-backend-readings-r3.json",
    "backend_readings_r2.json": "ord0310-backend-readings-r2.json",
    "q38r2-on-receipt.json": "ord0310-q38r2-on-receipt.json",
    "ord0310_keyless_deadline_receipt_r2.json": "ord0310_keyless_deadline_receipt_r2.json",
    "ord0310_keyless_deadline_receipt_r3.json": "ord0310_keyless_deadline_receipt_r3.json",
    "ord0310-q38r2-on-receipt-r2.json": "ord0310-q38r2-on-receipt-r2.json",
    "ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate.out",
    "ord0310-tip-read.out": "ord0310-tip-read.out",
    "ord0310-path-disjointness.tsv": "ord0310-path-disjointness.tsv",
    "r2/ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate-r2.out",
    "r2/ord0310-tip-read.out": "ord0310-tip-read-r2.out",
    "r2/ord0310-path-disjointness.tsv": "ord0310-path-disjointness-r2.tsv",
    "r2/ord0310-mergetree-tip-x-previous-ref.out": "ord0310-mergetree-tip-x-previous-ref.out",
    "r2/ord0310-left-right-count-trap.out": "ord0310-left-right-count-trap.out",
    "r3/ord0310-signal-vs-deadline-proof.out": "ord0310-signal-vs-deadline-proof.out",
    "r3/ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate-r3.out",
    "r3/ord0310-tip-read.out": "ord0310-tip-read-r3.out",
    "r3/ord0310-path-disjointness.tsv": "ord0310-path-disjointness-r3.tsv",
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
    "ord0310-tool-kill-arms-r2.py": "ord0310-tool-kill-arms-r2.py",
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
    "ord0310-readback-r4.json": "ord0310-readback-r4.json",
    "ord0310-tool-readback-r3.py": "ord0310-tool-readback-r3.py",
    "ord0310-publish-log-r2.json": "ord0310-publish-log-r2.json",
    "ord0310-publish-log-r2b.json": "ord0310-publish-log-r2b.json",
    "ord0310-publish-log-r3.json": "ord0310-publish-log-r3.json",
    "ord0310-publish-log-r4.json": "ord0310-publish-log-r4.json",
    "ord0310-publish-log-r7.json": "ord0310-publish-log-r7.json",
    "ord0310-publish-log-r6.json": "ord0310-publish-log-r6.json",
    "ord0310-readback-r5.json": "ord0310-readback-r5.json",
    "ord0310-q43r3-on-post-r3.json": "ord0310-q43r3-on-post-r3.json",
    "ord0310-q43r4b-on-post-r3.json": "ord0310-q43r4b-on-post-r3.json",
    "ord0310-post-body-r3.md": "ord0310-post-body-r3.md",
    "ord0310-ledger-block-r3.md": "ord0310-ledger-block-r3.md",
    "ord0310-q43r3-on-block-r3.json": "ord0310-q43r3-on-block-r3.json",
    "ord0310-q43r4b-on-block-r3.json": "ord0310-q43r4b-on-block-r3.json",
    "ord0310-q38r2-on-receipt-r3.json": "ord0310-q38r2-on-receipt-r3.json",
    "ord0310-backend-readings-r3.json": "ord0310-backend-readings-r3.json",
    "ord0310-arms-receipt-r5.json": "ord0310-arms-receipt-r5.json",
    "ord0310_keyless_deadline_receipt_r3.json": "ord0310_keyless_deadline_receipt_r3.json",
    "ord0310-publish-log-r3b.json": "ord0310-publish-log-r3b.json",
    "ord0310-tool-pub-names-r3.py": "ord0310-tool-pub-names-r3.py",
    "ord0310-tool-make-post-r3.py": "ord0310-tool-make-post-r3.py",
    "ord0310-tool-make-receipt-r3.py": "ord0310-tool-make-receipt-r3.py",
    "ord0310-tool-make-block-r3.py": "ord0310-tool-make-block-r3.py",
    "ord0310-tool-pub-names-r4.py": "ord0310-tool-pub-names-r4.py",
    "ord0310-tool-stage-pub-r4.py": "ord0310-tool-stage-pub-r4.py",
    "ord0310-tool-signal-proof.py": "ord0310-tool-signal-proof.py",
    # the gen-3 erratum round: labels/derivations corrected, no reading re-taken
    "ord0310-erratum-r1.json": "ord0310-erratum-r1.json",
    "ord0310-ledger-block-erratum-r1.md": "ord0310-ledger-block-erratum-r1.md",
    "ord0310-q43r4b-on-block-erratum-r1.json": "ord0310-q43r4b-on-block-erratum-r1.json",
    "ord0310-q43r3-on-block-erratum-r1.json": "ord0310-q43r3-on-block-erratum-r1.json",
    "ord0310_keyless_deadline_receipt_r3b.json": "ord0310_keyless_deadline_receipt_r3b.json",
    "ord0310-q38r2-on-receipt-r3b.json": "ord0310-q38r2-on-receipt-r3b.json",
    "r3b/ord0310-ref-read-r3b.out": "ord0310-ref-read-r3b.out",
    "r3b/ord0310-mergetree-tip-x-candidate.out": "ord0310-mergetree-tip-x-candidate-r3b.out",
    "r4/ord0310-tools-ref-read.out": "ord0310-tools-ref-read.out",
    "ord0310-tool-make-receipt-r4.py": "ord0310-tool-make-receipt-r4.py",
    "ord0310-tool-make-block-r4.py": "ord0310-tool-make-block-r4.py",
    "ord0310-tool-make-post-r4.py": "ord0310-tool-make-post-r4.py",
    "ord0310-tool-make-erratum.py": "ord0310-tool-make-erratum.py",
    "ord0310-tool-pub-names-r5.py": "ord0310-tool-pub-names-r5.py",
    "ord0310-tool-stage-pub-r5.py": "ord0310-tool-stage-pub-r5.py",
    "ord0310-publish-log-r9.json": "ord0310-publish-log-r9.json",
    "ord0310-readback-r6.json": "ord0310-readback-r6.json",
    "ord0310-post-body-r3.md": "ord0310-post-body-r3.md",
}

# per-run gate evidence, one file per arm. The run ids are read out of the arms receipts on disk
# rather than typed here, because a hand-kept list is how a generation's evidence gets cited but
# never staged: the same file that names a citation must be able to name its own publish path.
import glob as _glob  # noqa: E402
import json as _json  # noqa: E402
import os as _os  # noqa: E402

for _receipt in sorted(_glob.glob(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                                "_scratch_0310", "arms_receipt_*.json"))):
    with open(_receipt, encoding="utf-8") as _fh:
        _arms = _json.load(_fh)
    for _run in [_arms["clean_round"]["runId"]] + [_a["attempt"]["runId"] for _a in _arms["arms"]]:
        PUB[f"__ev__{_run}"] = f"ord0310-gate-evidence-{_run}.json"


def published(local: str) -> str:
    if local not in PUB:
        raise SystemExit(f"ABORT: {local} has no published name in review/ord0310_pub_names.py")
    return PUB[local]


def cite(local: str) -> str:
    return f"{DIRNAME}/{PUB[local]}"
