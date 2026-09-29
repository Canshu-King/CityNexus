#!/usr/bin/env python3
"""ORD-0457 r4 - receipts for the two claims the relayed order made about conflicts.

The order said the conflict surface is one file, `frontend/src/app/V8Experience.tsx`, and named a
delivered head. Neither is something I should answer with prose, so this measures it: what actually
moved on the line between my previous base and the current tip, whether any of it is one of my two
product files, what `git merge-tree` predicts read-only, and whether the rebase replays cleanly.

The rebase rc is re-derived by replaying the same inputs into a throwaway ref, so the number in the
receipt comes from a run and not from memory. That ref is deleted again; nothing published moves.

    python review/ord0457/rebase_receipt_r4.py <worktree> <prev-tip> <line-tip> <delivered-head> <out-json>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
PREV = sys.argv[2]
TIP = sys.argv[3]
DELIVERED = sys.argv[4]
OUT = Path(sys.argv[5]).resolve()
MINE = ["frontend/src/app/V8Experience.tsx", "frontend/src/lib/failureAttribution.ts"]
PROBE_REF = "refs/heads/review/N3-ord0457-rebase-probe-r4"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def out(*args: str) -> str:
    return git(*args).stdout.strip()


def resolve(rev: str) -> str:
    v = out("rev-parse", rev)
    assert re.fullmatch(r"[0-9a-f]{40}", v or ""), f"{rev} did not resolve"
    return v


def main() -> int:
    prev, tip, delivered = resolve(PREV), resolve(TIP), resolve(DELIVERED)
    moved = [f for f in out("diff", "--name-only", f"{prev}..{tip}", "--", "frontend/src").splitlines() if f]
    overlap = sorted(set(moved) & set(MINE))
    blobs = {}
    for f in MINE:
        blobs[f] = {"prev_tip_blob": out("rev-parse", f"{prev}:{f}"),
                    "line_tip_blob": out("rev-parse", f"{tip}:{f}"),
                    "my_head_blob": out("rev-parse", f"HEAD:{f}")}
        blobs[f]["unchanged_on_line"] = blobs[f]["prev_tip_blob"] == blobs[f]["line_tip_blob"]

    predicted = git("merge-tree", "--write-tree", tip, delivered)
    rc = predicted.returncode
    tree = predicted.stdout.splitlines()[0] if predicted.stdout.strip() else None
    conflicts = [l for l in predicted.stdout.splitlines()[1:] if "CONFLICT" in l]

    probe = git("checkout", "-q", "-B", re.sub(r"^refs/heads/", "", PROBE_REF), delivered)
    rebased = git("rebase", "--onto", tip, prev, re.sub(r"^refs/heads/", "", PROBE_REF))
    probe_head = out("rev-parse", PROBE_REF) if rebased.returncode == 0 else None
    cleanup = git("update-ref", "-d", PROBE_REF)
    detached = git("checkout", "-q", "review/N3-ord0457-named-failure-exits-r4")

    payload = {
        "prev_base_tip": prev,
        "line_tip": tip,
        "delivered_head": delivered,
        "frontend_src_files_moved_on_line": len(moved),
        "moved_list": moved,
        "overlap_with_my_product_files": overlap,
        "product_blob_pairs": blobs,
        "merge_tree_prediction": {"rc": rc, "tree": tree, "conflict_lines": conflicts,
                                  "meaning": "read-only prediction of tip <- delivered head"},
        "replay_probe": {"rebase_rc": rebased.returncode, "probe_head_after_replay": probe_head,
                         "setup_checkout_rc": probe.returncode, "probe_ref_deleted_rc": cleanup.returncode,
                         "worktree_back_on_branch_rc": detached.returncode,
                         "note": "same inputs as the delivery rebase, replayed into a throwaway ref"},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload["merge_tree_prediction"]["rc"] == 0 and payload["replay_probe"]["rebase_rc"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
