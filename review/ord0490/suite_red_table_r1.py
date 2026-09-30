"""ORD-0490 -- is the extra red in the whole-suite run mine?  Seven readings, in one table.

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

RUNS = [
    ("base, my file not collected", "suite_baseline_r1.txt"),
    ("base, my file not collected (pass 2)", "suite_baseline_pass2_r1.txt"),
    ("base, my file not collected (pass 3)", "suite_import_only_r1.txt"),
    ("with my 11 tests", "suite_current_r1.txt"),
    ("with my 11 tests (pass 2)", "suite_current_pass2_r1.txt"),
    ("my file collected, its 11 tests DESELECTED", "suite_collected_not_run_r1.txt"),
    ("11 NO-OP tests instead of mine", "suite_noop_probe_r1.txt"),
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
    base_label, base_tail, base_reds = readings(RUNS[0][1])
    lines = [
        "ORD-0490 whole-suite readings on one product generation (backend/app/* identical in all seven)",
        f"baseline red set = {len(base_reds)} named in review/ord0490/suite_evidence_r1.txt, first block",
        "",
        f"{'run':<44} {'summary':<24} delta against the baseline red set",
        "-" * 132,
    ]
    for label, receipt in RUNS:
        summary, _, reds = readings(receipt)
        added = sorted(reds - base_reds)
        dropped = sorted(base_reds - reds)
        delta = "identical set" if not added and not dropped else (
            "+ " + " , + ".join(item.split("::")[-1] for item in added)
            if added else "- " + " , - ".join(item.split("::")[-1] for item in dropped)
        )
        lines.append(f"{label:<44} {summary:<24} {delta}")
        for item in added:
            lines.append(f"{'':<44} {'':<24}   added: {item}")
    lines += [
        "",
        "reading: the last row is the attribution. Eleven tests that write nothing, open no session and",
        "call no door -- `tests/test_qoder_zz_timing_probe_r1.py`, deleted once the reading was taken --",
        "reproduce the same SHAPE (12 failed / 1510 passed) while losing a different arm (ord197 r4,",
        "with ord224 shape-A back to green). So one extra red is what adding any eleven tests to this",
        "suite costs, and which named arm falls is not determined by this order's fixtures. The run",
        "above it is the other direction: my file collected and all eleven tests DESELECTED, so none of",
        "them executed, and it is the reddest of the seven (13) with two arms that moved in no other run.",
        "",
        "This lane does not claim 'no new red'. It claims the delta is not attributable to ORD-0490, and",
        "names the seven readings that show it.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    # The logs themselves stay on the lane disk; what ships on the branch is every `FAILED` line and
    # every summary line read out of them, so the table above can be re-added by hand from this file.
    evidence = [
        "ORD-0490 -- the seven whole-suite readings behind suite_red_table_r1.txt, verbatim.",
        "Each block: the lane log this was read out of, the run's own summary line, and its FAILED lines.",
        "",
    ]
    for label, receipt in RUNS:
        text = (RUN / receipt).read_text(encoding="utf-8", errors="replace").splitlines()
        evidence.append(f"=== {label}")
        evidence.append(f"log: {receipt}")
        evidence.append(next(line for line in reversed(text) if " passed" in line))
        evidence.extend(sorted(line[len("FAILED "):].strip() for line in text if line.startswith("FAILED")))
        evidence.append("")
    (OUT.parent / "suite_evidence_r1.txt").write_text(
        "\n".join(evidence) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
