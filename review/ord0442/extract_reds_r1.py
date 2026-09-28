#!/usr/bin/env python3
"""ORD-0442 -- pull the named reds out of the commander's suite log, portably.

The log is read from the published blob (so the nodeids are the ones the commander actually ran), and
the Windows path separators are normalised to forward slashes because that is what pytest takes on the
command line here. `os.sep` is used rather than a literal backslash so this file survives being pasted
through a shell, which is how the first attempt died.
"""
from __future__ import annotations

import io
import os
import sys

SEP = chr(92)


def main() -> int:
    log_path, out_path = sys.argv[1], sys.argv[2]
    text = io.open(log_path, encoding="utf-8", errors="replace").read()
    ids = []
    for line in text.splitlines():
        if not line.startswith("FAILED "):
            continue
        node = line[len("FAILED "):].strip().replace(SEP, "/")
        ids.append(node)
    io.open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(ids) + "\n")
    tail = [l for l in text.splitlines() if "passed" in l and "failed" in l]
    print("extracted", len(ids))
    print("summary_line", tail[-1] if tail else "NONE")
    print("path_sep", repr(SEP), "os.sep", repr(os.sep))
    for n in ids:
        print("  ", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
