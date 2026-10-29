"""Point the just-appended 14.9 correction at the real lines: the regex moved when comments were added."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"
PAIRS = [
    ("_cmdr_cited_artifact_audit_r179.py:22", "_cmdr_cited_artifact_audit_r179.py:27"),
    ("（同文件 :28）", "（同文件 :35）"),
]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
text = io.open(REPORT, encoding="utf-8", newline="").read()
for old, new in PAIRS:
    if text.count(old) != 1:
        print("ABORT %r hits=%d" % (old, text.count(old)))
        raise SystemExit(5)
    text = text.replace(old, new, 1)
io.open(REPORT, "w", encoding="utf-8", newline="").write(text)
check = io.open(REPORT, encoding="utf-8", newline="").read()
print("RETARGETED wrong=%d right=%d" % (
    check.count("_r179.py:22") + check.count("（同文件 :28）"),
    check.count("_r179.py:27") + check.count("（同文件 :35）"),
))
