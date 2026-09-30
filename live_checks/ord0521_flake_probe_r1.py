"""ORD-0521 flake probe: how often does the one arm my generation adds go red on BOTH trees?

The candidate's suite red set is the base's 11 names plus `test_qoder_g3_xproc_http.py::
test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation` in one run and plus
`test_qoder_ord224_g3_generation_measurement.py::test_shape_a_...` in another.  Those two arms spawn
uvicorn workers and measure generations under a terminal job, so before attributing anything I count
how often each one fails when run alone, on the pristine base worktree and on my tree, in the same
command run.

Usage (from either tree's `backend/` is irrelevant - it takes both paths):

    python live_checks/ord0521_flake_probe_r1.py <base-backend> <candidate-backend> [repeats]
"""

from __future__ import annotations

import subprocess
import sys

ARMS = [
    "tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
    "tests/test_qoder_ord224_g3_generation_measurement.py::test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one",
]


def run(backend: str, nodeid: str) -> str:
    answer = subprocess.run(
        [sys.executable, "-m", "pytest", nodeid, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=backend,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = [line for line in answer.stdout.splitlines() if "passed" in line or "failed" in line]
    return tail[-1] if tail else "NO SUMMARY"


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    base, candidate = sys.argv[1], sys.argv[2]
    repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    for nodeid in ARMS:
        for label, tree in (("pristine-base", base), ("candidate", candidate)):
            outcomes = [run(tree, nodeid) for _ in range(repeats)]
            reds = sum("failed" in line for line in outcomes)
            print(f"{nodeid.split('::')[-1][:44]:46s} {label:14s} {reds}/{repeats} isolated reds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
