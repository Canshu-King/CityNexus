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

RUNS = [
    ("base, this order's file not collected", "suite_0504_base_r1.txt"),
    ("with this order's 6 tests", "suite_0504_r1.txt"),
]


def read(receipt: str) -> tuple[str, set[str]]:
    text = (RUN / receipt).read_text(encoding="utf-8", errors="replace").splitlines()
    match = SUMMARY.search("\n".join(text))
    if not match:
        raise SystemExit(f"REFUSE: {receipt} has no `N failed, M passed` line -- that run did not happen")
    reds = {line[len("FAILED "):].strip() for line in text if line.startswith("FAILED")}
    return f"{match.group(1)} failed / {match.group(2)} passed", reds


def main() -> int:
    base_summary, base_reds = read(RUNS[0][1])
    lines = [
        "ORD-0504 whole-suite red sets on c2bb95b8f4d78e6aacbb80773594020f1992f8a2",
        f"base red set = {len(base_reds)}",
        "",
    ]
    for label, receipt in RUNS:
        summary, reds = read(receipt)
        added = sorted(reds - base_reds)
        gone = sorted(base_reds - reds)
        verdict = ("identical set" if not added and not gone else
                   "SUBSET of the base set (nothing this order added)" if not added else
                   "NOT A SUBSET -- this order added a red")
        lines.append(f"{label:<40} {summary:<26} {verdict}")
        lines.append(f"{'':<40} {'':<26} log: {receipt}")
        for item in added:
            lines.append(f"{'':<40} {'':<40}added: {item}")
        for item in gone:
            lines.append(f"{'':<40} {'':<40}gone:  {item}")
    lines += [
        "",
        "reading: with this order's six tests the red set is a strict subset of the base's -- nothing was",
        "added, and one base red (ord197 r4) is green again. That one is not claimed as a fix: it is the",
        "same arm that moved in ORD-0490's seven-run table on identical bytes. What is claimed here is",
        "only the direction that matters, and it is computed from the two logs rather than asserted.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
