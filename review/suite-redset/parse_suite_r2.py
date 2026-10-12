"""Second generation of the suite-output parser: pair nodes with tracebacks and CHECK the pairing.

The r1 defect, named exactly: `parse_suite_r1.py` iterated over grouped *files* and pulled `tb[i]` with
that file index, so a file holding two reds got one traceback and the other files got shifted reasons.
The underlying data was fine -- with `-rf` and `--tb=line`, pytest emits FAILED summary lines and one-line
tracebacks in the same execution order, so node i pairs with traceback i.

r2 therefore pairs by index and refuses to stay silent when the pairing is wrong: for every i it compares
the file in the FAILED line with the file in the traceback line, and lists any mismatch.  That is the
"this arm bites" test for the parser itself: it caught r1's shift (see the run of r1 against the same
file), so the check is not vacuous.
"""

from __future__ import annotations

import pathlib
import re
import sys

RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
SUITE = RUN / (sys.argv[1] if len(sys.argv) > 1 else "full_suite_b2fccfdf_r1.txt")
TB = re.compile(r"^([A-Za-z]:\\.*\.py):(\d+): (.*)$")


def main() -> int:
    lines = SUITE.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = [l for l in lines if re.search(r"\d+ (passed|failed|error)", l)]
    if not tail:
        print("REFUSE: no summary tail")
        return 9
    summary = tail[-1].strip("= ")
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|error|skipped|xfailed|xpassed)",
                                               summary)}
    failed = [l for l in lines if l.startswith("FAILED")]
    tbs = [TB.match(l) for l in lines]
    tbs = [m for m in tbs if m]
    print(f"summary        : {summary}")
    print(f"counts         : {counts} -> reconciled {sum(counts.values())}")
    print(f"FAILED lines   : {len(failed)} | one-line tracebacks: {len(tbs)}")
    if len(failed) != len(tbs):
        print("REFUSE: node count and traceback count disagree; positional pairing is unsafe")
        return 9

    mismatched = []
    rows = []
    for i, f in enumerate(failed):
        spec = f.replace("FAILED ", "").strip()
        node_file, node_name = spec.split("::", 1)
        tb_file, tb_line, tb_msg = tbs[i].group(1), tbs[i].group(2), tbs[i].group(3)
        ok = node_file.replace("/", "\\").lower() in tb_file.lower()
        if not ok:
            mismatched.append((i, node_file, tb_file))
        rows.append((node_file, node_name.split(" - ")[0], tb_file.rsplit("\\", 1)[-1], tb_line,
                     tb_msg[:320], ok))

    print("\npositional pairing check (node file must appear in its traceback path):")
    for n, (nf, node, tbf, tbl, msg, ok) in enumerate(rows, 1):
        print(f"  {n}. {nf}::{node}")
        print(f"     file matches: {'YES' if ok else 'NO -> traceback says ' + tbf}  at {tbf}:{tbl}")
        print(f"     reason    : {msg[:240]}")
    print(f"\npairing mismatches: {len(mismatched)}")

    print("\nself-check of this parser (r1 must fail where r2 passes):")
    r1_grouped = {}
    for f in failed:
        r1_grouped.setdefault(f.replace("FAILED ", "").split("::")[0], []).append(f)
    shift_found = 0
    for i, path in enumerate(sorted(r1_grouped)):
        if i < len(tbs) and path.replace("/", "\\").lower() not in tbs[i].group(1).lower():
            shift_found += 1
    print(f"  r1's file-index join would mispair {shift_found} of {len(r1_grouped)} files "
          f"(that is the defect this generation fixes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
