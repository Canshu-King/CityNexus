# -*- coding: utf-8 -*-
"""Why the r2 census ruler's arm-A coordinates run ahead of the file: measured, not asserted.

Two hypotheses were tested against the ruler's own source (`strip_comments` at
live_checks/bilingual_pair_census_r2.py:52):
  H1 backslash escapes decoded into newlines -- refuted, the count above every row was zero.
  H2 every `/*` block-comment opener emits one extra newline into the masked text, while the
     comment's own interior newlines are kept too -- so each opener adds one phantom line.
The ruler locates matches in the masked text and reports that position, so its coordinates carry
the phantom lines with them.  Its *counts* per arm stay right; its *line numbers* do not.
"""
import re
import subprocess
import sys

REF = sys.argv[1] if len(sys.argv) > 1 else "67bb07473cb939d440c4e9a480e622c43586da44"
PATH = "frontend/src/features/execution/LiveRecovery.tsx"
CENSUS = "review/验路工-0576/rest_liverecovery_r3.txt"

PAIRS = [
    (77, "暂时无法获取这段路线的可靠通行时间"),
    (82, "附近没有可以替换这处行程"),
    (87, "没能确定这次变化影响"),
    (92, "这一段属于你已确认不能动"),
    (97, "暂时无法自动调整这段行程"),
    (314, "服务器摘要：这台设备还没读到"),
    (345, "已知晓，仍待处理"),
    (380, "已确认的预订和到达"),
    (383, "注意：部分已确认内容会受影响"),
    (417, "应用中…"),
    (427, "只调整今天：已记录"),
    (463, "刚才的行程变化已经处理好"),
]

blob = subprocess.run(["git", "show", "%s:%s" % (REF, PATH)], stdout=subprocess.PIPE)
if blob.returncode != 0:
    raise SystemExit("SHOW_FAIL %s:%s" % (REF, PATH))
lines = blob.stdout.decode("utf-8", "replace").split("\n")

esc = re.compile(r"\\[nrt]")
rows = []
for cens_line, needle in PAIRS:
    real = next((i for i, ln in enumerate(lines, start=1) if needle in ln), None)
    if real is None:
        raise SystemExit("ABORT needle absent from the blob: %s" % needle[:20])
    above = lines[: real - 1]
    h1 = sum(len(esc.findall(l)) for l in above)
    h2 = sum(l.count("/*") for l in above)
    rows.append((cens_line, real, cens_line - real, h1, h2, needle))
    print("census=%d real=%d delta=%d | H1_escapes=%d H2_block_openers=%d | %s" % (
        cens_line, real, cens_line - real, h1, h2, needle[:16]))

n = len(rows)
fit_h1 = sum(1 for r in rows if r[2] == r[3])
fit_h2 = sum(1 for r in rows if r[2] == r[4])
print("rows=%d H1_matches=%d H2_matches=%d" % (n, fit_h1, fit_h2))
if fit_h2 != n:
    print("NOT_EXPLAINED do not publish a cause")
    sys.exit(4)
print("MEASURED cause: strip_comments adds one newline per `/*` opener, so the ruler's arm-A line "
      "number equals the real line plus the block-comment openers above it")
print("USE census artifacts for counts only; take coordinates from the blob itself")
