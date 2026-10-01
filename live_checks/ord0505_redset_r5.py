"""ORD-0505 r5: is my candidate's red set a subset of the base's, judged by test name?

Written as an instrument rather than a paragraph because the claim is arithmetic over two files: a
candidate may be redder or greener than its base on timing-sensitive arms, and the only honest
question is whether any NAME that is red on the candidate is green on the base.

    python live_checks/ord0521_redset_r2.py review/ord0521_suite_base.txt review/ord0521_suite_candidate.txt
"""

from __future__ import annotations

import sys
from pathlib import Path


def reds(path: Path) -> set[str]:
    return {
        line[len("FAILED ") :].strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("FAILED ")
    }


def summary(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return next((line for line in reversed(lines) if " passed," in line), "NO SUMMARY LINE")


def main() -> int:
    base_path, candidate_path = Path(sys.argv[1]), Path(sys.argv[2])
    base, candidate = reds(base_path), reds(candidate_path)
    new = sorted(candidate - base)
    gone = sorted(base - candidate)
    print(f"base      : {summary(base_path)}")
    print(f"candidate : {summary(candidate_path)}")
    print(f"base red names {len(base)}, candidate red names {len(candidate)}")
    if new:
        print(f"NEW REDS ({len(new)}) - these belong to this order:")
        for name in new:
            print(f"  + {name}")
    else:
        print("NEW REDS: none - every red on the candidate is red on the base too")
    if gone:
        print(f"RED ON BASE ONLY ({len(gone)}) - timing-sensitive, moved in the candidate's favour:")
        for name in gone:
            print(f"  - {name}")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
