import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BLOCK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:/moodle/_qoder_ledger_inbox/双数工_0258.md")
ROOTS = [Path(r"D:/moodle/_qoder_shuangshugong_0558"), Path(r"D:/moodle")]

text = BLOCK.read_text(encoding="utf-8")
anchor = re.compile(r"([A-Za-z0-9_./\-\u4e00-\u9fff]+\.(?:tsx|ts|py|json|txt|md)):(\d+)")

seen = []
bad = []
for index, line in enumerate(text.splitlines(), start=1):
    for match in anchor.finditer(line):
        rel, number = match.group(1), int(match.group(2))
        path = None
        for root in ROOTS:
            candidate = root / rel
            if candidate.exists():
                path = candidate
                break
        if path is None:
            bad.append(("MISSING_FILE", index, rel, number, ""))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if number < 1 or number > len(lines):
            bad.append(("OUT_OF_RANGE", index, rel, number, "file_has={0}".format(len(lines))))
            continue
        seen.append((index, rel, number, lines[number - 1].strip()[:110]))

for record in seen:
    print("block_line={0} {1}:{2} -> {3}".format(record[0], record[1], record[2], record[3]))
print()
print("anchors_resolved={0}".format(len(seen)))
print("anchors_bad={0}".format(len(bad)))
for record in bad:
    print("BAD", record)
