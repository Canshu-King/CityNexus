"""bw296: if no raise carries a message_key, where does the key on screen come from?

bw293 aborted its own payload-shape arm for a good reason: across 1187 HTTPException raises under
backend/app there is not one detail dict carrying a message_key (PLAIN_STRING=1110, UNKNOWN_SHAPE=71,
DICT_NO_MESSAGE_KEY=6, WITH_MESSAGE_KEY=0).  Yet the real 409 receipt in bw285 shows
"message_key":"request.conflict" inside the response body.  So something else writes that key, and the
number of phrases a client can localise is decided there, not at the raise site.

This ruler finds that place: every module under backend/app that mentions message_key, split into
where the key is produced versus where it is only read, plus the mapping table it uses if there is one.
Read-only.
"""

import io
import os
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
APP = os.path.join(ROOT, "backend", "app")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw296-where-the-message-key-comes-from.txt")

WRITE_MARKS = ('"message_key"', "message_key=", "message_key\":", "'message_key'")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    hits = []
    files = 0
    for base, _dirs, names in os.walk(APP):
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            files += 1
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
            for index, row in enumerate(lines, start=1):
                if "message_key" not in row:
                    continue
                role = "writes" if any(mark in row for mark in WRITE_MARKS) else "reads_or_maps"
                hits.append((rel, index, role, row.strip()[:120]))
    written = [h for h in hits if h[2] == "writes"]
    out = [
        "WHERE message_key IS PRODUCED bw296",
        "MODULES SCANNED %d under backend/app; lines mentioning message_key: %d" % (files, len(hits)),
        "PRODUCED (a literal key assigned into a payload) %d lines" % len(written),
    ]
    for rel, line, _role, text in written[:20]:
        out.append("  %s:%d  %s" % (rel, line, text))
    out.append("READ / MAPPED %d lines" % (len(hits) - len(written)))
    for rel, line, _role, text in [h for h in hits if h[2] != "writes"][:20]:
        out.append("  %s:%d  %s" % (rel, line, text))
    out.append("VERDICT %s"
               % ("the key is written somewhere other than the raise site" if written else
                  "no site assigns a message_key at all - the key on screen must come from a "
                  "serializer outside backend/app"))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0 if written else 8


if __name__ == "__main__":
    sys.exit(main())
