"""ORD-0477: put the generated `listJourneys` fragment into the checked-in client without adopting
someone else's drift.

`frontend/src/generated/api.ts` at the tip is not byte-reproducible from the tip's own contract: a
regeneration from the *unedited* contract also emits a `V13NamedRejection` component the checked-in
file does not carry.  That unfinished regeneration belongs to whoever owns V13NamedRejection, so this
script keeps it out and ships only what ORD-0477 changes.  Every byte that stays is what
openapi-typescript 7.13.0 emitted for the edited contract; nothing here is hand-typed.

Three refusals, all judged before a single byte is written:
  R1  checked-in client vs the base regeneration must differ by exactly one inserted block, and that
      block must be the foreign `V13NamedRejection` component -- otherwise the pre-existing drift is
      bigger than the one this file names and a minimal diff cannot be claimed;
  R2  base regeneration vs the new regeneration must change only inside a window around
      `listJourneys` -- otherwise the contract edit reached something ORD-0477 did not order;
  R3  the file this script offers must differ from the checked-in client only inside that same
      window -- the proof that the foreign block really was kept out.
"""
from __future__ import annotations

import difflib
import pathlib
import sys

RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")
TREE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0477")
CHECKED = TREE / "frontend/src/generated/api.ts"
OUT = RUN / "ord0477_api_final.ts"
REPORT = RUN / "ord0477_api_sync_r1.txt"
WINDOW = 60  # lines around `listJourneys` that an operation-local edit may reach


def lines(path: pathlib.Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def regions(a: list[str], b: list[str]) -> list[tuple[str, int, int, int, int]]:
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((tag, i1, i2, j1, j2))
    return out


base = lines(RUN / "ord0477_api_base.ts")
mine = lines(RUN / "ord0477_api_mine.ts")
checked = lines(CHECKED)

anchor = [i for i, line in enumerate(mine) if line.strip() == "listJourneys: {"]
anchor_base = [i for i, line in enumerate(base) if line.strip() == "listJourneys: {"]
notes: list[str] = [
    f"checked_in={len(checked)} base_gen={len(base)} mine_gen={len(mine)}",
    f"listJourneys anchor lines: mine={anchor} base={anchor_base}",
]
if len(anchor) != 1 or len(anchor_base) != 1:
    REPORT.write_text("REFUSE: the operation anchor is not unique\n" + "\n".join(notes), encoding="utf-8")
    print("REFUSE anchor")
    sys.exit(1)

# ---- R1: the pre-existing drift, located exactly
r1 = regions(checked, base)
foreign_block = None
if len(r1) == 1 and r1[0][0] == "insert":
    _tag, _i1, _i2, j1, j2 = r1[0]
    block = base[j1:j2]
    if any("V13NamedRejection" in line for line in block) and all(
        any(token in line for token in ("V13NamedRejection", "ORD-0467", "@enum", "/**", "*/"))
        for line in block
    ):
        foreign_block = (j1, j2, block)
notes.append("R1 regions=%s foreign_found=%s" % (r1, foreign_block is not None))
if foreign_block is None:
    REPORT.write_text("REFUSE R1\n" + "\n".join(notes), encoding="utf-8")
    print("REFUSE R1")
    sys.exit(1)

# ---- the same block, located in the new regeneration as a contiguous run of its own lines
block = foreign_block[2]
starts = [i for i in range(0, len(mine) - len(block) + 1) if mine[i : i + len(block)] == block]
notes.append("foreign block length=%d starts in mine=%s" % (len(block), starts))
if len(starts) != 1:
    REPORT.write_text(
        "REFUSE: the foreign block is not found exactly once in the new regeneration\n"
        + "\n".join(notes),
        encoding="utf-8",
    )
    print("REFUSE block locate", starts)
    sys.exit(1)
keep = mine[: starts[0]] + mine[starts[0] + len(block) :]
notes.append(
    "dropped foreign block at mine[%d:%d] (%d lines)" % (starts[0], starts[0] + len(block), len(block))
)

# ---- R2 and R3: every change confined to the operation window
def op_anchors(file_lines: list[str]) -> list[int]:
    """Every line that names `listJourneys`: the `paths` entry, its `operations[...]` pointer, and
    the operation's own block.  One order edits all three, and they are 4 000 lines apart."""
    return [i for i, line in enumerate(file_lines) if "listJourneys" in line]


def inside_window(regions_: list[tuple], which: str, a: list[str], b: list[str]) -> bool:
    """Judge each side against *its own* anchors: the foreign block above shifts one file's lines."""
    anchors_a, anchors_b = op_anchors(a), op_anchors(b)
    ok = True
    for tag, i1, i2, j1, j2 in regions_:
        bad_a = [
            i for i in range(i1, max(i2, i1 + 1))
            if not any(abs(i - anchor) <= WINDOW for anchor in anchors_a)
        ]
        bad_b = [
            j for j in range(j1, max(j2, j1 + 1))
            if not any(abs(j - anchor) <= WINDOW for anchor in anchors_b)
        ]
        notes.append(
            f"{which} {tag} a[{i1}:{i2}]@{anchors_a} b[{j1}:{j2}]@{anchors_b} "
            f"outside_a={bad_a} outside_b={bad_b}"
        )
        ok = ok and not bad_a and not bad_b
    return ok

r2 = inside_window(regions(base, mine), "R2", base, mine)
r3 = inside_window(regions(checked, keep), "R3", checked, keep)
notes.append("R2_in_window=%s R3_in_window=%s keep=%d" % (r2, r3, len(keep)))

verdict = "WRITE" if (r2 and r3) else "REFUSE"
REPORT.write_text("\n".join(notes) + "\nverdict=%s\n" % verdict, encoding="utf-8")
print(verdict, "keep_lines", len(keep), "report", REPORT.as_posix())
if verdict == "REFUSE":
    sys.exit(1)
OUT.write_bytes("".join(keep).encode("utf-8"))
print("wrote", OUT.as_posix(), "bytes", OUT.stat().st_size)
