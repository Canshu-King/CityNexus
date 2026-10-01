"""ORD-0505 r3: prove what carried over from r1, and name the one thing deliberately changed.

Two classes, because the two kinds of file answer different questions:

* files this order creates - compared byte for byte after normalising line endings, since nothing
  outside this order can move inside them;
* files this order shares with other lanes - compared by MY added/removed lines, because the file
  itself legitimately differs between the two generations.

One created file is expected to differ: `review/ord0505/mutants_r1.py` was re-rooted in this re-cut -
it named another lane's checkout, so running it would have mutated the wrong tree and still printed
"killed".  The row shows that difference rather than hiding it.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

R1 = "88f7012ccc5715afc3d87db33c79c192a9e475de"
R1_BASE = "7862c6de5565c02c20ec2dccaa9da18960603e06"
R2_BASE = "514b397f96f3b5165b24865f4a544ab6f8020084"

CREATED = [
    "backend/tests/test_qoder_ord0505_journey_abort.py",
    "frontend/src/features/abort/JourneyAbortPanel.tsx",
    "frontend/src/features/abort/journeyAbort.ts",
    "frontend/src/features/abort/journeyAbortCopy.ts",
    "review/ord0505/real_http_abort_readback_r1.py",
    "review/ord0505/mutants_r1.py",
]
SHARED = [
    "backend/app/main.py",
    "backend/app/schemas.py",
    "backend/app/services.py",
    "backend/app/db/models.py",
    "backend/app/db/session.py",
    "backend/db/schema.sql",
    "frontend/src/app/v8PanelRegistry.tsx",
    "contracts/openapi.yaml",
]
DERIVED = ["frontend/src/generated/api.ts"]
# Created by this order, and changed here on purpose (the old text named another lane's checkout).
INTENTIONAL = []


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def delta(a: str, b: str | None, path: str) -> tuple[list[str], list[str]]:
    args = ["diff", a] + ([b] if b else []) + ["--", path]
    text = git(*args).decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    added = [l[1:].rstrip("\r") for l in text if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].rstrip("\r") for l in text if l.startswith("-") and not l.startswith("---")]
    return added, removed


def main() -> int:
    rows = [
        "ORD-0505 r1 -> r2 relay equivalence",
        f"r1: {R1_BASE[:12]}..{R1[:12]}   r2 base: {R2_BASE[:12]}",
        "",
        "A. files this order creates (byte for byte after normalising line endings):",
    ]
    ok = True
    for path in CREATED:
        mine = Path(path).read_bytes().replace(b"\r\n", b"\n")
        theirs = git("show", f"{R1}:{path}").replace(b"\r\n", b"\n")
        same = mine == theirs
        if path not in INTENTIONAL:
            ok &= same
        note = "   <- changed on purpose in this re-cut" if (not same and path in INTENTIONAL) else ""
        rows.append(f"   {path:60s} r2 {sha(mine)}  r1 {sha(theirs)}  identical={same}{note}")

    rows.append("")
    rows.append("B. files shared with other lanes (by MY added/removed lines, not by the file):")
    for path in SHARED:
        a1, d1 = delta(R1_BASE, R1, path)
        a2, d2 = delta(R2_BASE, None, path)
        same = a1 == a2 and d1 == d2
        ok &= same
        rows.append(f"   {path:60s} r2 +{len(a2)}/-{len(d2)}  r1 +{len(a1)}/-{len(d1)}  my_delta_identical={same}")

    rows.append("")
    rows.append("C. derived artifact - NOT relayed by patch, and NOT compared by line delta:")
    for path in DERIVED:
        a1, d1 = delta(R1_BASE, R1, path)
        a2, d2 = delta(R2_BASE, None, path)
        rows.append(
            f"   {path:60s} r2 +{len(a2)}/-{len(d2)}  r1 +{len(a1)}/-{len(d1)}  "
            "delta may differ by design"
        )
        rows.append(
            "     the judgement on a generated file is reproducibility, not equality with an older "
            "generation: see review/ord0505/regen_reproducibility_r3.txt"
        )

    rows.append("")
    rows.append(f"VERDICT (A and B): {'everything carried over unchanged' if ok else 'MISMATCH - see the rows above'}")
    Path("review/ord0505/relay_equivalence_r3.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows[3:]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
