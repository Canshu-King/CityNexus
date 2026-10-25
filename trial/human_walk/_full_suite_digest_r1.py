"""Summarize a pytest run log without re-running anything.

Reads the final summary line and every FAILED/ERROR short-summary line, then
groups them by test file so a 2,000-test log can be compared by shape rather
than by eyeballing the progress dots.
"""
from __future__ import annotations

import collections
import re
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/仓鼠王/AppData/Local/Temp/full54.log"
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as error:
        print("READ_ERROR", error)
        return 1
    summaries = re.findall(r"^=+ (.*?) =+$", text, re.M)
    print("SUMMARY", summaries[-1] if summaries else "MISSING")
    failures = re.findall(r"^(FAILED|ERROR) (\S+)", text, re.M)
    print("FAILED_LINES", len(failures))
    grouped = collections.Counter()
    for kind, node in failures:
        grouped[(kind, node.split("::")[0])] += 1
    for (kind, file), count in grouped.most_common(60):
        print("%-6s %4d  %s" % (kind, count, file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
