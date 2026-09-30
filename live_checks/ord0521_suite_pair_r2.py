"""ORD-0521 r2: run the backend suite on both generations, one at a time, and file the receipts.

Sequential on purpose. The two arms that move between runs (`g3_xproc_http`, `ord224 shape_a`) are
timing-sensitive, and two suites sharing the box would confound exactly the comparison this writes.

    python live_checks/ord0521_suite_pair_r2.py <base-backend> <candidate-backend> <out-dir>
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PY = sys.executable
NODES = ["tests", "--continue-on-collection-errors", "-q", "--no-header", "-p", "no:cacheprovider"]


def run(backend: str, args: list[str], out: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    answer = subprocess.run([PY, "-m", "pytest", *args], cwd=backend, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", env=env)
    out.write_text(answer.stdout + answer.stderr, encoding="utf-8", newline="\n")
    tail = [line for line in (answer.stdout + answer.stderr).splitlines() if "collected" in line or " failed," in line or " passed," in line]
    return tail[-1] if tail else "NO SUMMARY"


def main() -> int:
    base, candidate, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    print("base collect    :", run(base, ["tests", "--collect-only", "-q", "--no-header",
                                          "--continue-on-collection-errors"], out / "ord0521_collect_base.txt"))
    print("base suite      :", run(base, NODES, out / "ord0521_suite_base.txt"))
    print("cand collect    :", run(candidate, ["tests", "--collect-only", "-q", "--no-header",
                                               "--continue-on-collection-errors"], out / "ord0521_collect_candidate.txt"))
    print("cand suite      :", run(candidate, NODES, out / "ord0521_suite_candidate.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
