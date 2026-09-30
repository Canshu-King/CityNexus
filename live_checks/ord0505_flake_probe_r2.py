"""ORD-0505 r2: do the two arms that turned red on my candidate belong to this order?

Not answered by shrugging. The candidate's suite red set has two names the base run did not have
(`g3_xproc_http` and `ord0332_error_receipt R4`), and two names went the other way. One of those four
is a receipt-seeding arm, and this order's door raises `HTTPException`s that carry a `reason_code`,
so "it is just flaky" has to be measured rather than asserted.

Three modes, in this order:

1. the four rotating arms alone, on both trees - a name that is red in one tree alone and green in the
   other alone is a real difference;
2. the rotating arms run together with this order's own gate module, on the candidate - if MY module's
   presence is what reddens them, this is where it shows;
3. the rotating arms alone, again, after that - to confirm the tree was not left in a state that
   explains the result.

    python live_checks/ord0505_flake_probe_r2.py <base-backend> <candidate-backend> [repeats]
"""

from __future__ import annotations

import os
import subprocess
import sys

MODULE = "tests/test_qoder_ord0505_journey_abort.py"
ARMS = [
    "tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
    "tests/test_qoder_ord0332_error_receipt.py::test_R4_the_seed_reads_the_call_itself_not_the_moment",
    "tests/test_qoder_catalog_hydration.py::test_an_abandon_from_another_process_resolves_the_terminal_write_as_abandoned",
    "tests/test_qoder_ord197_four_class_receipt.py::test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match",
]


def run(backend: str, targets: list[str]) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    answer = subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=backend, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    lines = [l.strip() for l in (answer.stdout + answer.stderr).splitlines()
             if "passed" in l or "failed" in l or "no tests ran" in l or "not found" in l]
    return answer.returncode, (lines[-1] if lines else "NO SUMMARY")


def main() -> int:
    base, candidate = sys.argv[1], sys.argv[2]
    repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"mode 1 - the rotating arms alone, {repeats}x each tree")
    for label, tree in (("pristine-base", base), ("candidate", candidate)):
        for arm in ARMS:
            reds = 0
            last = ""
            for _ in range(repeats):
                rc, last = run(tree, [arm])
                if "no tests ran" in last or "not found" in last:
                    print(f"  {label:14s} {arm.split('::')[-1][:52]:54s} ABORT: the arm never ran -> {last}")
                    return 2
                reds += rc != 0
            print(f"  {label:14s} {arm.split('::')[-1][:52]:54s} {reds}/{repeats} red alone")

    print("mode 2 - rotating arms + this order's gate module, on the candidate")
    for combo in ([MODULE], ARMS[:2] + [MODULE], ARMS + [MODULE]):
        rc, last = run(candidate, combo)
        names = "+".join(t.split("::")[0].split("/")[-1][:26] for t in combo)
        print(f"  {names[:70]:72s} -> {last}")

    print("mode 3 - rotating arms alone again, on the candidate (state left behind?)")
    for arm in ARMS[:2]:
        rc, last = run(candidate, [arm])
        print(f"  {arm.split('::')[-1][:52]:54s} -> {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
