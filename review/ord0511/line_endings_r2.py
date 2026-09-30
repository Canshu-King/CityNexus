"""ORD-0511: set each file's ending back to what THAT FILE carries at the base, per file not per dir.

The previous take assumed the frontend area was CRLF and converted every file I touched.  Measured at
the base commit the tree actually holds two styles side by side in one directory --
`frontend/src/features/stay/StayExplorer.tsx` is all CRLF while its sibling
`frontend/src/features/stay/HotelsPanel.tsx` is all LF -- so the rule has to be read per file, and the
registry line I added was never mixed in the first place.

Content is untouched: the LF/CRLF-normalised bytes are compared before and after for each file.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

WT = Path("D:/moodle/_qoder_n2b_ord0466_20260929/wt")
BASE = "be0ffee216c7d24e48652427d290da848a9195cf"
CRLF = b"\r\n"
FILES = [
    "backend/app/main.py",
    "frontend/src/app/v8PanelRegistry.tsx",
    "frontend/src/features/stay/StayExplorer.tsx",
    "frontend/src/features/stay/stayGenerationDoor.ts",
]


def git_show(rel: str) -> bytes:
    return subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=WT, capture_output=True).stdout


def endings(blob: bytes) -> tuple[int, int]:
    total = blob.count(b"\n")
    crlf = blob.count(CRLF)
    return crlf, total - crlf


out = []
for rel in FILES:
    path = WT / rel
    current = path.read_bytes()
    content = current.replace(CRLF, b"\n")
    base = git_show(rel)
    if base:
        target = "CRLF" if endings(base)[0] > endings(base)[1] else "LF"
        source = "the base commit's own bytes"
    else:
        # a new file in this order: match the file it sits next to, which is LF
        sibling = git_show("frontend/src/features/stay/HotelsPanel.tsx")
        target = "CRLF" if endings(sibling)[0] > endings(sibling)[1] else "LF"
        source = "its sibling HotelsPanel.tsx (no base for a new file)"
    wanted = content.replace(b"\n", CRLF) if target == "CRLF" else content
    if wanted != current:
        path.write_bytes(wanted)
    after = path.read_bytes()
    crlf, lf = endings(after)
    out.append(
        f"{rel}: style from {source} -> {target}; now crlf={crlf} lf_only={lf}; "
        f"content_unchanged={after.replace(CRLF, chr(10).encode()) == content}"
    )
    if base:
        bc, bl = endings(base)
        out.append(f"    base at {BASE[:8]}: crlf={bc} lf_only={bl}")

report = "\n".join(out)
Path("D:/moodle/_qoder_n2b_ord0511_20260930/line_endings_r2.txt").write_text(report, encoding="utf-8")
print(report)
