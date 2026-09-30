"""ORD-0504 -- did my six tests add a red to the whole backend suite?  Two runs, compared by a script.

Same discipline ORD-0490 delivered with: a claim about the red set is a set relation, so it is computed
from the two logs' `FAILED` lines rather than asserted in prose. The base run ignores this order's file,
so the only difference between the two runs is whether six tests executed.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/suite_red_set_r1.py
"""

from __future__ import annotations

import re
from pathlib import Path

RUN = Path("D:/moodle/_qoder_r_ord0465_20260929/run")
OUT = Path("D:/moodle/_qoder_r_ord0465_20260929/wt/review/ord0504/suite_red_set_r1.txt")
SUMMARY = re.compile(r"(\d+) failed, (\d+) passed")

#: (generation, label, lane log). Two generations because the authoritative line moved while this
#: order was being written, and the readings that ship are the ones taken on the tip being delivered to.
RUNS = [
    ("c2bb95b8", "base, my file not collected", "suite_0504_base_r1.txt"),
    ("c2bb95b8", "with my 6 tests", "suite_0504_r1.txt"),
    ("59b7bc00", "base, my file not collected (pass 1)", "r7_suite_base_r1.txt"),
    ("59b7bc00", "base, my file not collected (pass 2)", "r7_suite_base_pass2_r1.txt"),
    ("59b7bc00", "with my 6 tests (pass 1)", "r7_suite_mine_r1.txt"),
    ("59b7bc00", "with my 6 tests (pass 2)", "r7_suite_mine_pass2_r1.txt"),
    ("7862c6de", "base, my file not collected", "r8_suite_base_r1.txt"),
    ("7862c6de", "with my 6 tests (pass 1)", "r8_suite_mine_r1.txt"),
    ("7862c6de", "with my 6 tests (pass 2)", "r8_suite_mine_pass2_r1.txt"),
]
SUMMARY = re.compile(r"(\d+) failed, (\d+) passed")


def read(receipt: str) -> tuple[str, set[str]]:
    text = (RUN / receipt).read_text(encoding="utf-8", errors="replace").splitlines()
    match = SUMMARY.search("\n".join(text))
    if not match:
        raise SystemExit(f"REFUSE: {receipt} has no `N failed, M passed` line -- that run did not happen")
    reds = {line[len("FAILED "):].strip() for line in text if line.startswith("FAILED")}
    return f"{match.group(1)} failed / {match.group(2)} passed", reds


def main() -> int:
    lines = ["ORD-0504 whole-suite red sets, grouped by the generation they ran on."]
    for generation in dict.fromkeys(row[0] for row in RUNS):
        rows = [row for row in RUNS if row[0] == generation]
        _, base_reds = read(rows[0][2])
        lines += ["", "=" * 96, f"generation {generation} -- base red set = {len(base_reds)}", "=" * 96]
        for _, label, receipt in rows:
            summary, reds = read(receipt)
            added = sorted(reds - base_reds)
            gone = sorted(base_reds - reds)
            verdict = ("identical set" if not added and not gone else
                       "SUBSET of the base set" if not added else
                       "NOT A SUBSET -- one arm is not in the base set (see the reading below: the next "
                       "pass on identical bytes is)")
            lines.append(f"{label:<40} {summary:<26} {verdict}")
            lines.append(f"{'':<40} {'':<26} log: {receipt}")
            for item in added:
                lines.append(f"{'':<40} {'':<40}added: {item}")
            for item in gone:
                lines.append(f"{'':<40} {'':<40}gone:  {item}")
    lines += [
        "",
        "reading, and it is not the comfortable one. On the generation this order delivers to (7862c6de) the",
        "same bytes with my six tests produced 13 failed once and 11 failed the next time; the 11 set is a",
        "strict subset of the base's 12. On the previous generation the same thing happened in the other",
        "direction (13 then 11 with my file, 11 twice without it). Across all seven runs not one of this",
        "order's six tests appears in a red list -- they are all in the pass counts. So the delta is not",
        "attributable to ORD-0504, and equally this lane will not write 'no new red': the suite's red set",
        "floats between 11 and 13 on identical bytes, and the arms that move (catalog_hydration's abandon",
        "arm, g3_xproc, ord197 r3/r4, ord224 shape-A) are the worker-and-timing family catalogued in",
        "review/ord0490/suite_red_table_r1.txt. Nothing this order changed touches a table those arms read.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
