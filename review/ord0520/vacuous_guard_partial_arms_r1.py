"""Arms for the third guard: the declared arms must all be recorded, and the real stack must get through.

`vacuous_guard_gap_closed_arm_r1.py` closed the two other guards. This is the third, and its shape is
different again: the HTTP probe declares its refusal arms in one dict (`cases`) and records what came back
in another (`refusals`), so the question is not "non-empty" but "did every declared arm get recorded".

Arms, all driven by importing the instrument and calling its guard:
  * zero of four recorded -> refuse;
  * one, two or three of four -> refuse, and the message must name what is missing;
  * all four recorded -> allowed.

The control that says these guards are not walls: the same instrument, run against a stack this lane
started, records all four and answers PASSED -- the receipt from that run is the control line below.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DECLARED = ["ABORT_ACTOR_NOT_OWNER", "ABORT_JOURNEY_IN_RECYCLE_BIN", "JOURNEY_ALREADY_ABORTED",
            "JOURNEY_NOT_FOUND"]
CONTROL_RECEIPT = HERE / "ABORT_HTTP_RECEIPT_r3.json"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refuses(callable_) -> tuple[bool, str]:
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
    return code not in (0, None), buffer.getvalue().strip()


def main() -> int:
    probe = load("abort_http_probe_r3")
    guard = probe.refuse_unless_all_present
    failures: list[str] = []
    rows: list[dict] = []

    for count, expect_refusal in ((0, True), (1, True), (2, True), (3, True), (4, False)):
        recorded = DECLARED[:count]
        refused, said = refuses(lambda: guard(DECLARED, recorded, "the refusal arms declared and recorded"))
        rows.append({"recorded": count, "refused": refused, "expect_refusal": expect_refusal,
                     "guard_said": said})
        if refused != expect_refusal:
            failures.append("%d of four recorded: refused=%s expected=%s" % (count, refused, expect_refusal))
        # A refusal must name what is missing, or "it refused" is not evidence of anything specific.
        if expect_refusal and refused:
            missing_named = [name for name in DECLARED if name not in recorded and name in said]
            if len(missing_named) != len(DECLARED) - count:
                failures.append("%d of four: refusal named %s, expected the missing ones"
                                % (count, missing_named))

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    control = json.loads(CONTROL_RECEIPT.read_text(encoding="utf-8"))
    control_recorded = sorted((control.get("refusals_over_http") or {}).keys())
    control_ok = control_recorded == sorted(DECLARED) and \
        control.get("verdict_computed_from_the_rows_above") == "PASSED"
    print("control_recorded=%s control_verdict=%s"
          % (", ".join(control_recorded), control.get("verdict_computed_from_the_rows_above")))
    if not control_ok:
        failures.append("the real-stack control did not record all four arms as PASSED")

    print("VERDICT %s" % ("REFUSES_EVERY_PARTIAL_SET_AND_ALLOWS_THE_FULL_ONE" if not failures
                          else "ARM_FAILED"))
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())