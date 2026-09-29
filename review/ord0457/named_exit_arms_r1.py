#!/usr/bin/env python3
"""ORD-0457 - do the two new named exits actually carry the reading? (arms, restored by bytes)

Each arm takes one of the two new branches out again, rebuilds, re-runs the screen walk, and records
which named check reddens. Without this, "429 now says 限流" could just as well be a coincidence
between a stub and a sentence.

    python review/ord0457/named_exit_arms_r1.py <worktree> <preview-base> <token> <out-json>
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:49966"
TOKEN = sys.argv[3] if len(sys.argv) > 3 else ""
OUT = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else ROOT / "review/n3_0457_evidence_r1/named_exit_arms_r1.json"
CLASSIFIER = ROOT / "frontend/src/lib/failureAttribution.ts"
VITE = str(ROOT / "frontend/node_modules/vite/bin/vite.js")
WALK = ROOT / "review/ord0457/named_exits_walk_r1.cjs"
WALK_OUT = ROOT / "review/n3_0457_evidence_r1/walk"

ARMS = [
    {
        "name": "B1 the 429 branch is taken out (back to the unnamed catch-all)",
        "find": '    if (status === 429) {',
        "replace": '    if (status === 4299) {',
        "expect": "N1 and N2 must go red",
    },
    {
        "name": "B2 the 409 branch is taken out",
        "find": '    if (status === 409) {',
        "replace": '    if (status === 4099) {',
        "expect": "N3 and N4 must go red",
    },
    {
        "name": "B3 the server's own wait is dropped on its way through the request layer",
        "find": '      typeof body?.error?.retry_after_ms === "number" ? body.error.retry_after_ms : null,',
        "replace": "      null,",
        "expect": "N2 must go red: the wait the screen quotes has to be the one the answer carried",
        "file": ROOT / "frontend/src/app/V8Experience.tsx",
    },
]


def sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1200)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    targets = {Path(a.get("file", CLASSIFIER)) for a in ARMS}
    originals = {p: (p.read_bytes(), sha(p)) for p in targets}
    results = []
    for arm in ARMS:
        path = Path(arm.get("file", CLASSIFIER))
        raw, before = originals[path]
        text = raw.decode("utf-8")
        if arm["find"] not in text:
            results.append({"name": arm["name"], "applied": False,
                            "note": "ANCHOR_NOT_FOUND - the arm never ran and proves nothing"})
            continue
        path.write_bytes(text.replace(arm["find"], arm["replace"], 1).encode("utf-8"))
        built = run(["node", VITE, "build"], ROOT / "frontend")
        walked = run(["node", str(WALK), BASE, TOKEN, str(WALK_OUT), "zh-CN"], ROOT)
        path.write_bytes(raw)
        reds = [m.strip() for m in walked.stdout.splitlines() if m.strip().startswith("RED ")]
        summary = [m for m in walked.stdout.splitlines() if m.startswith("checks=")]
        results.append({
            "name": arm["name"], "expect": arm["expect"], "applied": True,
            "build_rc": built.returncode, "walk_rc": walked.returncode,
            "walk_summary": summary[-1] if summary else None,
            "red_checks": [r[:70] for r in reds],
            "restored_byte_identical": sha(path) == before,
        })
    final_build = run(["node", VITE, "build"], ROOT / "frontend")
    payload = {
        "arms": results,
        "all_arms_applied": all(r.get("applied") for r in results),
        "all_restored": all(r.get("restored_byte_identical") for r in results if r.get("applied")),
        "clean_rebuild_after_restoring": final_build.returncode,
        "every_file_back_at_starting_bytes": all(sha(p) == h for p, (_, h) in originals.items()),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(payload, ensure_ascii=False, indent=1)[:1800])
    return 0 if payload["all_arms_applied"] and payload["all_restored"] and payload[
        "every_file_back_at_starting_bytes"] and final_build.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
