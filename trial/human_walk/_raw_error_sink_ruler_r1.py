"""Ruler: a refused request must never be printed to a screen verbatim.

Section 85/§87 measured "CityNexus API 409: /journeys/<uuid>/agent/goal-tasks/<uuid>/resume" reaching a
traveller.  The fix routed every such mouth through `travelerErrorMessage`, so this ruler keeps them
closed: any `error.message` that flows straight into a screen setter (or out of a message-picking
helper) is red.  It checks itself against a negative control first, because a ruler that cannot fail
is decoration.
"""
import pathlib
import re
import subprocess
import sys

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
SRC = ROOT + "/frontend/src"

SINKS = [
    r"set[A-Za-z]*Error\(\s*error instanceof Error \? error\.message",
    r"setMessage\(\s*error instanceof Error && error\.message \? error\.message",
    r"return error instanceof Error && error\.message \? error\.message",
    r"return error instanceof Error \? error\.message",
    r":\s*error instanceof Error \? error\.message\s*:",
]
ALLOWED = re.compile(r"travelerErrorMessage\(")


def scan(text: str) -> list[int]:
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOWED.search(line):
            continue
        if any(re.search(pattern, line) for pattern in SINKS):
            hits.append(number)
    return hits


def main() -> int:
    files = [str(path) for path in sorted(pathlib.Path(SRC).rglob("*.ts*"))
             if path.suffix in (".ts", ".tsx") and "error.message" in path.read_text(encoding="utf-8", errors="replace")]
    offenders: list[str] = []
    for path in files:
        hits = scan(pathlib.Path(path).read_text(encoding="utf-8", errors="replace"))
        if hits:
            offenders.append(path.replace(SRC + "/", "") + ":" + ",".join(str(n) for n in hits))
    negative = "\n".join([
        '      setRequestError(error instanceof Error ? error.message : "任务未能启动。");',
        '    return error instanceof Error && error.message ? error.message : retry;',
    ])
    if len(scan(negative)) != 2:
        print("SELFTEST_RED: the ruler cannot see its own negative control")
        return 2
    positive = '      setRequestError(travelerErrorMessage(error, "任务这次没能启动，可以刷新后再试。"));'
    if scan(positive):
        print("SELFTEST_RED: the shared helper is being reported as a leak")
        return 3
    print("SELFTEST_OK negative=2 positive=0")
    if offenders:
        print("RAW_ERROR_SINKS", len(offenders))
        for item in offenders:
            print("  " + item)
        return 1
    if not files:
        print("SELFTEST_RED: the ruler saw zero files, which is not a pass")
        return 4
    print("RAW_ERROR_SINKS 0 files_checked=" + str(len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
