#!/usr/bin/env python3
"""ORD-0457 r4 - manifest the r4 evidence dir against the tip it was produced on.

Same job as evidence_manifest_r3.py (blob 381e4e38e31a0d467011e45c02b7055074e23b31 kept untouched),
generalised so the evidence directory, the branch and the tip are arguments instead of constants:
the line moved again while r3 was being written, and a tool that cannot name its own input is how a
stale reading ends up quoted as current evidence.

    python review/ord0457/evidence_manifest_r4.py <worktree> <line-tip> <branch> <evidence-dir> <out-json>
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
LINE_TIP = sys.argv[2]
BRANCH = sys.argv[3]
EV_DIR = sys.argv[4].strip("/")
OUT = Path(sys.argv[5]).resolve()

PRODUCT = [
    "frontend/src/lib/failureAttribution.ts",
    "frontend/src/app/V8Experience.tsx",
    "frontend/src/lib/displayVocabulary.ts",
    "frontend/src/app/v8PanelRegistry.tsx",
]
INSTRUMENTS = [
    "review/ord0457/named_exits_walk_r1.cjs",
    "review/ord0457/named_exit_arms_r1.py",
    "review/ord0457/named_exit_arms_r2.py",
    "review/ord0457/evidence_manifest_r3.py",
    "review/ord0457/evidence_manifest_r4.py",
    "review/ord0457/make_block_r4.py",
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    tip = git("rev-parse", LINE_TIP)
    assert re.fullmatch(r"[0-9a-f]{40}", tip), f"tip did not resolve: {LINE_TIP!r}"
    product = {p: {"worktree_sha1": sha1(ROOT / p), "head_blob": git("rev-parse", f"HEAD:{p}"),
                   "tip_blob": git("rev-parse", f"{tip}:{p}")}
               for p in PRODUCT if (ROOT / p).exists() and git("rev-parse", f"{tip}:{p}")}
    artifacts = {}
    for path in sorted((ROOT / EV_DIR).rglob("*")):
        if path.is_file() and not path.name.endswith(".png"):
            rel = path.relative_to(ROOT).as_posix()
            artifacts[rel] = {"bytes": path.stat().st_size, "sha1": sha1(path)}
    dist_sw = ROOT / "frontend/dist/v10-sw.js"
    payload = {
        "line_tip": tip,
        "branch": BRANCH,
        "branch_head_before_push": git("rev-parse", "HEAD"),
        "my_commits_on_top_of_tip": int(git("rev-list", "--count", f"{tip}..HEAD") or 0),
        "product_files": product,
        "instruments_sha1": {p: sha1(ROOT / p) for p in INSTRUMENTS if (ROOT / p).exists()},
        "served_bundle_v10_sw": {"bytes": dist_sw.stat().st_size, "sha1": sha1(dist_sw)} if dist_sw.exists() else None,
        "artifacts": artifacts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "artifacts"}, ensure_ascii=False, indent=1))
    print(f"artifacts listed: {len(artifacts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
