#!/usr/bin/env python3
"""Replica of the ledger door's coordinate bolt, run before submitting a block.

Mirrors `ledger_insert_after_r2.py:58-101`: every well-formed 40-hex in the block must either
`git cat-file -t` in D:/moodle/CityNexus, or be disclosed on its OWN line as a plain content hash /
non-git value (the same phrase patterns) *and* share its paragraph with a value that does resolve.
This is a pre-check only -- it does not insert anything and does not touch the door.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
PAT = re.compile(
    r"sha1\s*[\(（]?\s*(over|of)\s+bytes"
    r"|文件\s*sha1|本机\s*sha1|内容\s*sha1"
    r"|本地字节重算|字节重算的\s*sha"
    r"|从未入\s*git|未入\s*git|不在对象库"
    r"|非\s*blob|不是\s*blob|不可\s*cat-file|故意不可取回",
    re.I,
)
REPO = r"D:/moodle/CityNexus"


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    resolves = {h: subprocess.run(["git", "-C", REPO, "cat-file", "-t", h], capture_output=True, text=True).returncode == 0
                for h in sorted(set(HEX40.findall(raw)))}

    def paragraph(idx: int) -> str:
        lo = hi = idx
        while lo > 0 and lines[lo - 1].strip():
            lo -= 1
        while hi < len(lines) - 1 and lines[hi + 1].strip():
            hi += 1
        return "\n".join(lines[lo:hi + 1])

    bad, ok_resolving, ok_exempt = [], 0, []
    for i, text in enumerate(lines, 1):
        for h in sorted(set(HEX40.findall(text))):
            if resolves[h]:
                ok_resolving += 1
                continue
            declared = bool(PAT.search(text))
            anchored = any(resolves.get(o) for o in HEX40.findall(paragraph(i - 1)) if o != h)
            if declared and anchored:
                ok_exempt.append((i, h))
            else:
                bad.append((i, h, f"declared={declared} anchored={anchored}"))
    print(f"block={path.name} 40hex_total_distinct={len(resolves)} resolving_mentions={ok_resolving} exempt={len(ok_exempt)}")
    for ln, h, why in bad:
        print(f"  line {ln} {h} {why}")
    print("COORDINATE_BOLT=" + ("GREEN" if not bad else "RED"))
    return 0 if not bad else 3


if __name__ == "__main__":
    raise SystemExit(main())
