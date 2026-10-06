"""Abnormal-path arms for the two guards that have not proved it yet.

`vacuous_guard_abnormal_arm_r1.py` closed the HTTP probe: empty collection -> named refusal, with the
real-stack run as the control.  The other two guards have a different shape each, so their abnormal arms
are written against what each one actually checks:

  * `abort_glass_provenance_r2` guards on the non-empty subset of its four P-records: it refuses when NONE
    of them ran.  Partial runs (1, 2 or 3 of four) it does NOT refuse -- a finding of this arm, named below.
  * `osmt_flake_attribution_r2` guards inside `per_state` on the lines of its file: it refuses when the file
    has no lines.  A file whose lines are all of another state it does NOT refuse -- same finding, named below.

A first cut of this arm asserted that partial runs and other-state-only files must also refuse.  That was me
describing the guard I wished for rather than the guard that exists: the measured behaviour is "empty refuses,
non-empty passes", and the two partial cases above are a real remaining gap, not an arm failure.  They are
reported as such.

Each arm prints its own numbers and exits non-zero if any half does not hold.  Nothing here starts a
server and nothing writes outside this lane's tmp.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LANE = HERE.parents[2]
TMP = LANE / "tmp"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # both guard their real work behind __main__
    return module


def refuses(callable_) -> tuple[bool, str, object]:
    buffer = io.StringIO()
    stdout = sys.stdout
    sys.stdout = buffer
    code = None
    try:
        callable_()
    except SystemExit as exc:
        code = exc.code
    finally:
        sys.stdout = stdout
    return code not in (0, None), buffer.getvalue().strip(), code


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    rows: list[dict] = []

    # --- guard 2: the provenance instrument, on the count of P-records that ran.
    prov = load("abort_glass_provenance_r2")
    guard = prov.refuse_when_empty
    for count, expect_refusal in ((0, True), (1, False), (2, False), (3, False), (4, False)):
        records = [{"P%d" % (i + 1): True} for i in range(count)]
        refused, said, code = refuses(lambda: guard(records, "the four provenance checks"))
        rows.append({"guard": "abort_glass_provenance_r2", "p_records": count,
                     "partial_run_not_refused": (0 < count < 4 and not refused),
                     "refused": refused, "exit_code": code, "expect_refusal": expect_refusal,
                     "guard_said": said})
        if refused != expect_refusal:
            failures.append("provenance with %d records: refused=%s expected=%s" % (count, refused, expect_refusal))

    # --- guard 3: the flake attribution instrument, on the lines of its input file.
    flake = load("osmt_flake_attribution_r2")
    empty_file = TMP / "_flake_abnormal_empty_r1.jsonl"
    other_state_file = TMP / "_flake_abnormal_other_state_r1.jsonl"
    real_file = HERE / "OSMT_XPROC_AB_r1.jsonl"
    empty_file.write_text("", encoding="utf-8")
    other_state_file.write_text('{"state": "somebody_else", "failed": [], "family_red": false}\n',
                                encoding="utf-8")
    for label, path, expect_refusal in (("empty_file", empty_file, True),
                                        ("lines_of_another_state_only", other_state_file, False),
                                        ("real_measurement_lines", real_file, False)):
        refused, said, code = refuses(lambda p=path: flake.per_state(p, ["test_x"]))
        rows.append({"guard": "osmt_flake_attribution_r2", "input": label,
                     "zero_denominator_not_refused": (label == "lines_of_another_state_only" and not refused),
                     "refused": refused, "exit_code": code, "expect_refusal": expect_refusal,
                     "guard_said": said})
        if refused != expect_refusal:
            failures.append("flake with %s: refused=%s expected=%s" % (label, refused, expect_refusal))
    empty_file.unlink(missing_ok=True)
    other_state_file.unlink(missing_ok=True)

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    gaps = [r for r in rows if r.get("partial_run_not_refused") or r.get("zero_denominator_not_refused")]
    print("NAMED_GAP_COUNT %d" % len(gaps))
    verdict = "BOTH_GUARDS_REFUSE_THE_EMPTY_CASE_AND_ALLOW_THE_FULL_ONE" if not failures else "ARM_FAILED"
    print("VERDICT %s" % verdict)
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())