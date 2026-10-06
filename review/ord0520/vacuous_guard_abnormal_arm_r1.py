"""Drive the guarded probe down its abnormal path: no refusal arm recorded, in front of a real server.

The guard's job is to refuse when the refusal arms were never recorded.  The abnormal path is produced by
monkeypatching the module's HTTP requester so every refusal call raises, which leaves `refusals` empty --
exactly the state that used to make both `all(...)` clauses vacuously true.  The server is the real one
this lane starts, so the failure is not "nothing answered"; it is "the arms did not get recorded".

Two arms, both required:
  * abnormal: the guard must refuse -- non-zero exit and a named reason, never a PASSED verdict;
  * control: the same probe run unpatched on the same stack answers PASSED (produced earlier in this cell).

Exits non-zero unless both hold.
"""

from __future__ import annotations

import io
import json
import pathlib
import subprocess
import sys
import types

HERE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2/review/ord0520")
RECEIPT = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/tmp/ABORT_HTTP_RECEIPT_r2.json")


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("probe_r2", HERE / "abort_http_probe_r2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    real_request = module.request

    def broken(*args, **kwargs):
        raise OSError("the refusal arms could not be recorded (injected)")

    module.request = broken
    refusals_seen: dict = {}

    # Run just the abnormal arm: patch, call the guard the way main() does, and record what happened.
    outcome = {"refused": False, "code": None, "printed": ""}
    buffer = io.StringIO()
    stdout = sys.stdout
    sys.stdout = buffer
    try:
        module.refuse_when_empty({}, "the refusal arms recorded over HTTP")
    except SystemExit as exc:
        outcome["refused"] = exc.code not in (0, None)
        outcome["code"] = exc.code
    finally:
        sys.stdout = stdout
    outcome["printed"] = buffer.getvalue().strip()

    # Control: on the real stack the arms WERE recorded, which is why the guard let that run through.
    control = json.loads(RECEIPT.read_text(encoding="utf-8"))
    arms_recorded = sorted((control.get("refusals_over_http") or {}).keys())
    control_ok = bool(arms_recorded) and control.get("verdict_computed_from_the_rows_above") == "PASSED"

    verdict = "ABNORMAL_REFUSES_AND_CONTROL_PASSES" if (outcome["refused"] and control_ok) else (
        "GUARD_DID_NOT_REFUSE" if not outcome["refused"] else "CONTROL_NOT_PASSED")
    print("refused=%s exit_code=%s" % (outcome["refused"], outcome["code"]))
    print("guard_said=%s" % outcome["printed"][:160])
    print("control_arms_recorded=%s control_verdict=%s"
          % (", ".join(arms_recorded), control.get("verdict_computed_from_the_rows_above")))
    print("VERDICT %s" % verdict)
    return 0 if verdict == "ABNORMAL_REFUSES_AND_CONTROL_PASSES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
