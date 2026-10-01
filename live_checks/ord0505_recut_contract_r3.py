"""ORD-0505 r3 recut instrument: re-lay the three contracts/openapi.yaml hunks on a newer tip.

`git apply` fails on this file because other lanes added paths and schemas in the same neighbourhood,
so the context lines my r1 hunk carried no longer sit where they did.  Nothing about MY entry changed,
so the r1 diff is split by hunk and each piece is placed by the anchor it hangs off rather than by a
line number:

1. the `/journeys/{journey_id}/abort` operation - inserted as the sibling right after `/undelete`,
   which is where it sat in r1;
2. the `JourneyAbortRequest` schema - inserted immediately before `JourneyPatch`;
3. the two `cancelled_*` properties - appended to the `Journey` schema's property list, after
   `current_activity_id`.

Every anchor is asserted unique before anything is written, and the total added-line count is checked
against the r1 diff, so a silently dropped piece cannot pass this driver.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = "7862c6de5565c02c20ec2dccaa9da18960603e06"
R1 = "88f7012ccc5715afc3d87db33c79c192a9e475de"
TARGET = Path("contracts/openapi.yaml")


def r1_hunks() -> list[list[str]]:
    diff = subprocess.run(
        ["git", "diff", BASE, R1, "--", str(TARGET)],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.replace("\r\n", "\n").split("\n")
    hunks: list[list[str]] = []
    current: list[str] | None = None
    for line in diff:
        if line.startswith("@@"):
            if current:
                hunks.append(current)
            current = []
            continue
        if current is not None and line.startswith("+") and not line.startswith("+++"):
            current.append(line[1:].rstrip("\r"))
    if current:
        hunks.append(current)
    return hunks


def find(hunks: list[list[str]], needle: str, label: str) -> list[str]:
    hits = [h for h in hunks if any(needle in line for line in h)]
    if len(hits) != 1:
        raise SystemExit(f"ABORT {label}: {needle!r} found in {len(hits)} r1 hunks, expected 1")
    return hits[0]


def insert_after(lines: list[str], anchor: str, block: list[str], label: str, inside: str | None = None) -> None:
    hits = [i for i, line in enumerate(lines) if line == anchor]
    if inside is not None:
        # The same property line can exist in a sibling schema (`Journey` and `JourneyTwin` both
        # carry `current_activity_id` on this generation), so the owning schema name decides.
        header = f"    {inside}:"
        owners = [i for i, line in enumerate(lines) if line == header]
        if len(owners) != 1:
            raise SystemExit(f"ABORT {label}: schema header {header!r} matched {len(owners)} lines")
        following = [i for i in range(owners[0] + 1, len(lines)) if lines[i].startswith("    ") and lines[i].rstrip().endswith(":") and not lines[i].startswith("     ")]
        end = following[0] if following else len(lines)
        hits = [i for i in hits if owners[0] < i < end]
    if len(hits) != 1:
        raise SystemExit(f"ABORT {label}: anchor {anchor!r} matched {len(hits)} lines, expected 1")
    lines[hits[0] + 1 : hits[0] + 1] = block


def insert_before(lines: list[str], anchor: str, block: list[str], label: str) -> None:
    hits = [i for i, line in enumerate(lines) if line == anchor]
    if len(hits) != 1:
        raise SystemExit(f"ABORT {label}: anchor {anchor!r} matched {len(hits)} lines, expected 1")
    lines[hits[0] : hits[0]] = block


def main() -> int:
    hunks = r1_hunks()
    operation = find(hunks, "/journeys/{journey_id}/abort:", "hunk 1")
    request = find(hunks, "JourneyAbortRequest:", "hunk 2")
    props = find(hunks, "cancelled_reason: {type:", "hunk 3")

    with open(TARGET, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    lines = raw.replace("\r\n", "\n").split("\n")
    before = len(lines)

    # 1. the operation goes in as the sibling right after the `/undelete` entry's own block
    undelete = [i for i, line in enumerate(lines) if line == "  /journeys/{journey_id}/undelete:"]
    if len(undelete) != 1:
        raise SystemExit(f"ABORT hunk 1: /undelete matched {len(undelete)} paths")
    siblings = [i for i in range(undelete[0] + 1, len(lines)) if lines[i].startswith("  /")]
    if not siblings:
        raise SystemExit("ABORT hunk 1: no sibling path after /undelete")
    lines[siblings[0] : siblings[0]] = operation

    # 2. the request schema sits immediately before JourneyPatch, as it did in r1
    insert_before(lines, "    JourneyPatch:", request, "hunk 2")

    # 3. the two cancelled_* properties extend the Journey schema's property list
    insert_after(
        lines,
        "        current_activity_id: {type: [string, 'null'], format: uuid}",
        props,
        "hunk 3",
        inside="Journey",
    )

    grew = len(lines) - before
    expected = len(operation) + len(request) + len(props)
    if grew != expected:
        raise SystemExit(f"ABORT arithmetic: wrote {grew} lines, r1 hunks carry {expected}")
    with open(TARGET, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines))
    print(f"relaid {len(operation)} + {len(request)} + {len(props)} = {grew} contract lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
