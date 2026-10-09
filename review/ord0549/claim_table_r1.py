"""ORD-0549 claim table: for every file in the commander's table, what the ledger itself says owns it.

The inventory answers "is the cell still inline in code"; this answers the other half, "may a lane take
it". Both come from reads: the claim column quotes the ledger line it found with its line number as of
this run, and any branch named inside that quote is resolved against the remote in the same breath.
The ledger is rewritten whole-file by the landing leg, so a quoted line number is a timestamp rather
than an address -- the sentence is what should be trusted.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
from pathlib import Path

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
HERE = Path("D:/moodle/_qoder_lane_heyuegong_20261009")
INVENTORY_JSON = HERE / "ord0549_inventory.json"
INVENTORY_TXT = HERE / "ord0549_inventory.txt"
OUT = HERE / "CLAIM_TABLE_R1.txt"
REPO = "D:/moodle/CityNexus"

CLAIM_MARKERS = ("认领", "有主", "不取", "取的格", "已入线", "在飞", "我先退", "占了", "归柜工")
# The ledger names families with a trailing glob (`refs/heads/review/jiazigong-*`). A glob is not a ref:
# resolving the truncated prefix as a ref reads "NOT-ON-REMOTE" and that is a false reading, so a glob is
# counted against `ls-remote --refs` instead and reported as a count.
BRANCH = re.compile(r"refs/heads/review/[\w./-]+\*?")
ROW_LINE = re.compile(r"^(\S+)\s+(frontend/src/\S+?):\d+ key=")


_remote_listing: list[str] | None = None


def remote_listing() -> list[str]:
    global _remote_listing
    if _remote_listing is None:
        check = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin"],
                               capture_output=True, text=True)
        _remote_listing = [line.split("\t")[-1].strip() for line in (check.stdout or "").splitlines() if "\t" in line]
    return _remote_listing


def resolve_ref(ref: str) -> str:
    listed = remote_listing()
    if ref.endswith("*"):
        prefix = ref[:-1]
        matched = [item for item in listed if item.startswith(prefix)]
        return f"GLOB matched={len(matched)} first={matched[0] if matched else 'none'}"
    exact = [item for item in listed if item == ref]
    if not exact:
        return "NOT-ON-REMOTE (and the full ref listing was read, so this is a real absence)"
    head = subprocess.run(["git", "-C", REPO, "ls-remote", "origin", ref],
                          capture_output=True, text=True).stdout.strip()
    return head.replace("\n", " ")[:78]

ledger = io.open(LEDGER, encoding="utf-8", newline="").read().split("\n")
tip = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))["tip"]

inline_left: dict[str, int] = {}
absorbed: dict[str, int] = {}
for line in INVENTORY_TXT.read_text(encoding="utf-8").splitlines():
    match = ROW_LINE.match(line)
    if not match:
        continue
    verdict, path = match.groups()
    if verdict == "STILL_INLINE":
        inline_left[path] = inline_left.get(path, 0) + 1
    elif verdict.startswith("ABSORBED"):
        absorbed[path] = absorbed.get(path, 0) + 1

out = [
    "ORD-0549 claim table.",
    f"tip={tip}",
    f"ledger_lines_at_this_run={len(ledger)}",
    "A cell still inline in code is not necessarily free: this carries what the ledger itself says owns it.",
    "",
    f"{'inline_left':>11} {'absorbed':>8}  file",
]

for name in sorted(set(inline_left) | set(absorbed)):
    basename = name.rsplit("/", 1)[-1]
    hits = [
        (index + 1, line) for index, line in enumerate(ledger)
        if basename in line and any(marker in line for marker in CLAIM_MARKERS)
    ]
    out.append("")
    out.append(f"{inline_left.get(name, 0):>11} {absorbed.get(name, 0):>8}  {name}")
    if not hits:
        out.append("            ledger_claim_quote = NONE FOUND (no ledger line names this file with claim language)")
    for number, line in hits[:3]:
        out.append(f"            ledger:{number} | {line.strip()[:210]}")
        for ref in dict.fromkeys(BRANCH.findall(line)):
            out.append(f"              ref {ref} -> {resolve_ref(ref)}")

text = "\n".join(out) + "\n"
OUT.write_text(text, encoding="utf-8")
print(f"wrote {OUT} ({len(out)} lines)")
