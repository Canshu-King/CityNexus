"""Run one of my offline instruments with a hard watchdog so a HANG names its own line.

Why: after tightening the publisher's secret scan, `test_ord0275_publisher_guard_r3.py` stopped making
progress - no crash, no traceback, just a silent process.  "It hung" is not a finding; the stack trace of
the blocked frame is.  `dump_traceback_later(..., exit=True)` prints it and kills the run.
"""
import faulthandler
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = sys.argv[1] if len(sys.argv) > 1 else "test_ord0275_publisher_guard_r3.py"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 45
path = os.path.join(HERE, TARGET)
src = io.open(path, encoding="utf-8").read()

faulthandler.enable()
faulthandler.dump_traceback_later(LIMIT, exit=True)
print(f"[watchdog] {TARGET}: dumping the blocked frame after {LIMIT}s of no exit")
try:
    exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
finally:
    faulthandler.cancel_dump_traceback_later()
    print("[watchdog] finished before the deadline")
