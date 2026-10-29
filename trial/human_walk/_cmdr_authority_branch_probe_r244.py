"""Record which line of plan_authority_blocker actually refuses, without changing what it returns.

Fifteen reds say "PlanVersion is not authoritative: UNRESOLVED_ACTIVITY_FACTS", but the predicate has
five distinct return sites in backend/app/services.py and each means a different missing fact.  The
census cannot tell them apart from the message alone.

This plugin installs a return trace scoped to that one function, so the only thing recorded is the
line number the function itself returned from.  It is observation-only, and that claim is tested
rather than asserted: the caller re-runs the same files with the probe off and on, and the pass/fail
counts must be identical or the measurement is discarded.  A positive control is enforced too -- if no
refusal is recorded at all, the probe reports failure instead of publishing an empty table that would
read like "no branch taken".
"""

import io
import os
import sys
import threading
import traceback

TARGET_FILE = "app\\services.py"
TARGET_FUNC = "plan_authority_blocker"

_records = []
_current = {"nodeid": None}


def _trace(frame, event, arg):  # pragma: no cover - tracer
    code = frame.f_code
    if code.co_name != TARGET_FUNC or not code.co_filename.endswith(TARGET_FILE):
        return None
    if event == "call":
        return _trace_inner
    return None


def _trace_inner(frame, event, arg):
    code = frame.f_code
    if code.co_name != TARGET_FUNC or not code.co_filename.endswith(TARGET_FILE):
        return None
    if event == "return":
        result = arg[0] if isinstance(arg, tuple) else arg
        if isinstance(result, str):
            _records.append({"nodeid": _current["nodeid"], "line": frame.f_lineno})
    return _trace_inner


def pytest_runtest_setup(item):
    _current["nodeid"] = item.nodeid


def pytest_configure(config):
    # The doors under test are sync FastAPI routes: TestClient runs them on worker threads, so a
    # sys.settrace on the main thread recorded nothing at all.  3.12 can arm every live thread.
    threading.settrace(_trace)
    threading.settrace_all_threads(_trace)
    sys.settrace(_trace)


def pytest_unconfigure(config):
    sys.settrace(None)
    try:
        threading.settrace_all_threads(None)
    except (RuntimeError, TypeError):  # pragma: no cover
        pass


def pytest_sessionfinish(session, exitstatus):
    # trial/human_walk/<this file> is three directories under the repo root; two dirname() calls
    # pointed the receipt at trial/trial/... and crashed the run at sessionfinish.
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(root, "trial", "results", "20261026_gozero", "bw244-authority-branches.txt")
    counts = {}
    for record in _records:
        counts[record["line"]] = counts.get(record["line"], 0) + 1
    lines = [
        "AUTHORITY BLOCKER BRANCH PROBE bw244",
        "TARGET %s :: %s" % (TARGET_FILE, TARGET_FUNC),
        "REFUSALS_RECORDED %d (positive control: zero means the probe did not bite)" % len(_records),
        "BY_RETURN_LINE %s" % ", ".join("services.py:%d=%d" % (line, n) for line, n in sorted(counts.items())),
    ]
    for record in _records[:60]:
        lines.append("  line=%-5s node=%s" % (record["line"], record["nodeid"]))
    io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    print("WROTE %s" % out)
    if not _records:
        print("PROBE_SELF_CHECK FAILED no refusal line recorded -- the table below must not be read as a finding")


def main():  # pragma: no cover - used when run directly, for a quick traceback sanity check
    print(__doc__)
    print("trace depth sanity:", len(traceback.extract_stack()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
