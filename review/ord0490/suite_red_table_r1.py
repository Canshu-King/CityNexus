"""ORD-0490 -- is the extra red in the whole-suite run mine?  Nine readings, two generations.

The delivery batch reported `12 failed` where the base reports `11`, and the extra one was
`tests/test_qoder_ord224_g3_generation_measurement.py::test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one`.
Correlation across four runs is not attribution, so the fifth and sixth readings below separate
"my tests ran" from "my file exists": the whole suite was run again with my file COLLECTED and its
eleven tests DESELECTED -- same product bytes, same executed test set as the base runs, and my
fixtures never touched the store.

Written from the seven receipts, not typed: every number here is read off the `N failed, M passed`
line of the file named beside it, and the delta is a set difference of the `FAILED` lines.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0490/suite_red_table_r1.py
"""

from __future__ import annotations

import re
from pathlib import Path

RUN = Path("D:/moodle/_qoder_r_ord0465_20260929/run")
OUT = Path("D:/moodle/_qoder_r_ord0465_20260929/wt/review/ord0490/suite_red_table_r1.txt")

#: (generation, label, lane log). The nine runs are two experiments: the first generation asked
#: "is the extra red mine?", the second (the one this order delivers on) asks the same question again
#: after ORD-0475 turned the share-body gate round and the suite's red set dropped to eight.
RUNS = [
    ("dcb90ccc", "base, my file not collected", "suite_baseline_r1.txt"),
    ("dcb90ccc", "base, my file not collected (pass 2)", "suite_baseline_pass2_r1.txt"),
    ("dcb90ccc", "base, my file not collected (pass 3)", "suite_import_only_r1.txt"),
    ("dcb90ccc", "with my 11 tests", "suite_current_r1.txt"),
    ("dcb90ccc", "with my 11 tests (pass 2)", "suite_current_pass2_r1.txt"),
    ("dcb90ccc", "my file collected, its 11 tests DESELECTED", "suite_collected_not_run_r1.txt"),
    ("dcb90ccc", "11 NO-OP tests instead of mine", "suite_noop_probe_r1.txt"),
    ("de341634", "base, my file not collected", "r3_suite_base_r1.txt"),
    ("de341634", "with my 11 tests", "r3_suite_mine_r1.txt"),
]
SUMMARY = re.compile(r"(\d+) failed, (\d+) passed")


def readings(name: str) -> tuple[str, str, set[str]]:
    text = (RUN / name).read_text(encoding="utf-8", errors="replace")
    match = SUMMARY.search(text)
    reds = {line[len("FAILED "):].strip() for line in text.splitlines() if line.startswith("FAILED")}
    if not match:
        raise SystemExit(f"REFUSE: {name} has no `N failed, M passed` line -- that run did not happen")
    return f"{match.group(1)} failed / {match.group(2)} passed", text.strip().splitlines()[-1], reds


def main() -> int:
    lines = ["ORD-0490 whole-suite readings, grouped by the product generation they ran on."]
    for generation in dict.fromkeys(row[0] for row in RUNS):
        rows = [row for row in RUNS if row[0] == generation]
        base_label, _, base_reds = readings(rows[0][2])
        lines += [
            "",
            "=" * 100,
            f"generation {generation} -- baseline red set = {len(base_reds)}",
            "=" * 100,
        ]
        for _, label, receipt in rows:
            summary, _, reds = readings(receipt)
            added = sorted(reds - base_reds)
            dropped = sorted(base_reds - reds)
            delta = "identical set" if not added and not dropped else (
                ("+ " + " , + ".join(item.split("::")[-1] for item in added) if added else "")
                + ("  - " + " , - ".join(item.split("::")[-1] for item in dropped) if dropped else "")
            )
            lines.append(f"{label:<44} {summary:<24} {delta}")
            lines.append(f"{'':<44} {'':<24} log: {receipt}")
    evidence = [
        "ORD-0490 -- the whole-suite readings behind suite_red_table_r1.txt, verbatim.",
        "Each block: the product generation, the lane log, the run's own summary line, its FAILED lines.",
        "",
    ]
    for generation, label, receipt in RUNS:
        text = (RUN / receipt).read_text(encoding="utf-8", errors="replace").splitlines()
        evidence.append(f"=== {generation} :: {label}")
        evidence.append(f"log: {receipt}")
        evidence.append(next(line for line in reversed(text) if " passed" in line))
        evidence.extend(sorted(line[len("FAILED "):].strip() for line in text if line.startswith("FAILED")))
        evidence.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (OUT.parent / "suite_evidence_r1.txt").write_text(
        "\n".join(evidence) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
