#!/usr/bin/env python3
"""ORD-0457 r3 - pin every screen reading to the tip it was taken on.

r1 and r2 quoted a tip in prose, so a later reader had to trust that the readings and the tip went
together. This writes the pairing down: the line tip the branch was rebased onto, the product blobs
the walk ran against, and the sha1 of every artifact in the evidence directory. Nothing here judges
anything - it only makes the coordinates machine-checkable.

    python review/ord0457/evidence_manifest_r3.py <worktree> <line-tip> <branch> <out-json>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
LINE_TIP = sys.argv[2]
BRANCH = sys.argv[3]
OUT = Path(sys.argv[4]).resolve()

PRODUCT = [
    "frontend/src/lib/failureAttribution.ts",
    "frontend/src/app/V8Experience.tsx",
    "frontend/src/lib/displayVocabulary.ts",
]
INSTRUMENTS = [
    "review/ord0457/named_exits_walk_r1.cjs",
    "review/ord0457/named_exit_arms_r1.py",
    "review/ord0457/named_exit_arms_r2.py",
]
EVIDENCE_DIR = ROOT / "review/n3_0457_evidence_r1"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    # worktree bytes, not HEAD: the readings were taken from what was on disk.
    product = {p: {"worktree_sha1": sha1(ROOT / p), "head_blob": git("rev-parse", f"HEAD:{p}")} for p in PRODUCT}
    instruments = {p: sha1(ROOT / p) for p in INSTRUMENTS if (ROOT / p).exists()}
    artifacts = {}
    for path in sorted(EVIDENCE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.endswith(".png"):
            continue
        artifacts[rel] = {"bytes": path.stat().st_size, "sha1": sha1(path)}
    dist_sw = ROOT / "frontend/dist/v10-sw.js"
    payload = {
        "line_tip_at_rebase": LINE_TIP,
        "branch": BRANCH,
        "branch_head_before_push": git("rev-parse", "HEAD"),
        "rebase_base_commits_ahead": git("rev-list", "--count", f"{LINE_TIP}..HEAD"),
        "product_files": product,
        "instruments_sha1": instruments,
        "served_bundle_v10_sw": {"bytes": dist_sw.stat().st_size, "sha1": sha1(dist_sw)} if dist_sw.exists() else None,
        "artifacts": artifacts,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "artifacts"}, ensure_ascii=False, indent=1))
    print(f"artifacts listed: {len(artifacts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
