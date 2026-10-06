import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
print("ledger_lines=%d" % len(lines))

HEAD = re.compile(r"^### ")


def block_start(idx):
    for j in range(idx, max(0, idx - 1200), -1):
        if HEAD.match(lines[j]):
            return j
    return max(0, idx - 40)


for tgt in sys.argv[1:]:
    hits = [i for i, l in enumerate(lines) if tgt in l]
    print("==== %s 命中 %d 处" % (tgt, len(hits)))
    for i in hits[-2:]:
        s = block_start(i)
        print("  -- 行 %d，块头：%s" % (i + 1, lines[s][:170]))
        # the paragraph(s) that actually name this lane
        for k in range(s, min(len(lines), i + 14)):
            t = lines[k].strip()
            if not t:
                continue
            if tgt in lines[k] or k == s:
                print("     :%d %s" % (k + 1, t[:900]))
