"""Diff two copies of the same watch-relay block that stand in the ledger, line by line.

Why: the door's verbatim guard is honest but useless against these, because 13 copies of one notice each
differ somewhere.  Before designing a normaliser I need the actual diff -- which lines move between
rounds, and which of them carry a claim a lane would need to read.
"""
import difflib
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HEAD = "### 落地这一侧没回音·494abfd7·预防工-0557-dict-r2（值守转达）"
wanted = [int(a) for a in sys.argv[1:3]] if len(sys.argv) > 2 else None

lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").split("\n")
blocks = []
cur = None
for index, line in enumerate(lines, start=1):
    if line.startswith("### "):
        if cur:
            blocks.append(cur)
        cur = {"start": index, "heading": line.strip(), "body": []}
    elif cur is not None and line.strip():
        cur["body"].append(line.strip())
if cur:
    blocks.append(cur)

same = [b for b in blocks if b["heading"] == HEAD]
print("copies found:", len(same), "| body lengths:", [len("\n".join(b["body"])) for b in same])
if len(same) < 2:
    raise SystemExit(0)
first, second = (same[wanted[0] - 1], same[wanted[1] - 1]) if wanted else (same[-2], same[-1])
print("comparing copy #%d (ledger line %d) against copy #%d (ledger line %d)" % (
    (wanted or [len(same) - 1, len(same)])[0], first["start"],
    (wanted or [len(same) - 1, len(same)])[1], second["start"]))
for line in difflib.unified_diff(first["body"], second["body"], lineterm="", n=0):
    if line.startswith(("---", "+++", "@@")):
        continue
    print(line[:220])
