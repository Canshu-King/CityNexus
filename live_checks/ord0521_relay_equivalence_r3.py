"""ORD-0521 r3: what carried over from r2, named per file and per class.

The sequencer refused r2 because three of the files this order touches - `backend/app/main.py`,
`contracts/openapi.yaml`, `frontend/src/generated/api.ts` - had different bytes on the tip than on
r2's base (ORD-0522's 9071608a moved inside them).  Nothing about this order changed, and this
driver is what proves that claim instead of asserting it:

* A - files this order creates: compared byte for byte against the r2 ref;
* B - files this order shares with other lanes: compared by MY added/removed lines, because the file
  itself legitimately differs between generations;
* C - the generated client: a derived artifact, judged by reproducibility (see
  `review/ord0521/regen_reproducibility_r3.txt`), not by equality with an older generation.

    python live_checks/ord0521_relay_equivalence_r3.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

R2 = "0f92c63e458e93eaedcd57856220c342452186f1"
R2_BASE = "7862c6de5565c02c20ec2dccaa9da18960603e06"
R3_BASE = "2f0568e05fb2540266b8e4fdbafb1e03d25a29c7"

CREATED = [
    "backend/app/demo_scene.py",
    "backend/tests/test_qoder_ord0521_empty_store_scene_door.py",
    "live_checks/ord0521_empty_store_walk_r1.py",
    "live_checks/ord0521_mutant_driver_r1.py",
    "live_checks/ord0521_flake_probe_r1.py",
]
SHARED = ["backend/app/main.py", "backend/app/services.py", "contracts/openapi.yaml"]
DERIVED = ["frontend/src/generated/api.ts"]


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
        "ORD-0521 r2 -> r3 relay equivalence",
        f"r2: {R2_BASE[:12]}..{R2[:12]}   r3 base: {R3_BASE[:12]}",
        "",
        "A. files this order creates (byte for byte after normalising line endings):",
    ]
    ok = True
    for path in CREATED:
        mine = Path(path).read_bytes().replace(b"\r\n", b"\n")
        theirs = git("show", f"{R2}:{path}").replace(b"\r\n", b"\n")
        same = mine == theirs
        ok &= same
        rows.append(f"   {path:60s} r3 {sha(mine)}  r2 {sha(theirs)}  identical={same}")

    rows.append("")
    rows.append("B. files shared with other lanes (by MY added/removed lines, not by the file):")
    for path in SHARED:
        a2, d2 = delta(R2_BASE, R2, path)
        a3, d3 = delta(R3_BASE, None, path)
        same = a2 == a3 and d2 == d3
        ok &= same
        rows.append(f"   {path:60s} r3 +{len(a3)}/-{len(d3)}  r2 +{len(a2)}/-{len(d2)}  my_delta_identical={same}")

    rows.append("")
    rows.append("C. derived artifact, judged by reproducibility:")
    for path in DERIVED:
        a2, d2 = delta(R2_BASE, R2, path)
        a3, d3 = delta(R3_BASE, None, path)
        rows.append(f"   {path:60s} r3 +{len(a3)}/-{len(d3)}  r2 +{len(a2)}/-{len(d2)}  see regen_reproducibility_r3.txt")

    rows.append("")
    rows.append(f"VERDICT (A and B): {'everything carried over unchanged' if ok else 'MISMATCH - see the rows above'}")
    Path("review/ord0521/relay_equivalence_r3.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows[4:]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
