"""ORD-0500 r16: re-count the backend suite after the dictionary rows were deleted, and make it re-runnable.

`--collect-only` is the counter that catches "a deletion un-wired a whole suite": this lane once shipped
a rename that left the backend suite collecting zero tests, which is indistinguishable from a green run
unless somebody counts the denominator.  It is a separate instrument, so a re-cut can re-run it and the
receipt carries the interpreter, the command and the exit code next to the count.

Writes evidence/pytest_collectonly_<COLLECT_OUT or r14>.json.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
BACKEND = os.path.join(WT, "backend")
EV = os.path.join(LANE, "evidence")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"


def main():
    if not os.path.exists(PY):
        raise SystemExit("ABORT_NO_VENV_PYTHON " + PY)
    p = subprocess.run([PY, "-m", "pytest", "--collect-only", "-q"], cwd=BACKEND,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    out = p.stdout.decode("utf-8", "replace")
    lines = [l for l in out.strip().splitlines() if l.strip()]
    tail = lines[-1] if lines else ""
    m = re.search(r"(\d+)\s+tests?\s+collected", tail)
    if p.returncode and not m:
        raise SystemExit("ABORT_COLLECT_FAILED rc=%s tail=%s" % (p.returncode, tail[:200]))
    if not m:
        raise SystemExit("ABORT_NO_COLLECTED_COUNT tail=%s" % tail[:200])
    ver = subprocess.run([PY, "-V"], stdout=subprocess.PIPE, timeout=120).stdout.decode().strip()
    rc = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], stdout=subprocess.PIPE,
                        timeout=120).stdout.decode().strip()
    data = {"tool": os.environ.get("COLLECT_TOOL") or "pytest_collectonly_r14",
            "cmd": "python -m pytest --collect-only -q (cwd wt22/backend)",
            "interpreter": ver, "worktree_head": rc, "line": tail,
            "collected": int(m.group(1)), "exit": p.returncode,
            "took_local": datetime.now().astimezone().isoformat(timespec="seconds")}
    dest = os.path.join(EV, os.environ.get("COLLECT_OUT") or "pytest_collectonly_r14.json")
    json.dump(data, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"collected": data["collected"], "exit": data["exit"],
                      "head": rc[:12], "receipt": os.path.basename(dest)}, ensure_ascii=False))
    return 0 if p.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
