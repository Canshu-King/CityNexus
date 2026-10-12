# -*- coding: utf-8 -*-
"""自证仪表改动：把批六第一次 ABORT 的成因数出来给对门看。
  旧断言 = 「这枚中文串在整枚文件里不许再出现」——它会把成对语区表里的另一枚串（含同一串字当子串）也算进去；
  新断言 = 「这枚中文串不许再出现在任何内联双语三元式里」。
两把各数一次，报数与坐标。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
CAND = sys.argv[1]
F = "frontend/src/features/agent/CopilotDock.tsx"
LIT_TARGET = "受保护承诺"
CJK = re.compile(r"[\u3400-\u9fff]")
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)

text = subprocess.check_output(["git", "show", "%s:%s" % (CAND, F)],
                               cwd=REPO).decode("utf-8", "replace")
lines = text.split("\n")
substr_lines = [index + 1 for index, line in enumerate(lines) if LIT_TARGET in line]
tern_hits = [m.group(0) for m in TERN.finditer(text)
             if LIT_TARGET in (m.group(1)[1:-1], m.group(2)[1:-1])]
exact_lines = [index + 1 for index, line in enumerate(lines)
               if re.search(r'"\s*"?\s*' + re.escape(LIT_TARGET) + r'\s*"', line) is False
               and line.strip().startswith('"%s"' % LIT_TARGET) is False
               and ('"%s"' % LIT_TARGET) in line]

print("CAND %s FILE %s" % (CAND[:12], F))
print("OLD_ASSERT_substring_lines %d lines %s" % (len(substr_lines), substr_lines))
print("NEW_ASSERT_ternary_hits %d" % len(tern_hits))
for line in substr_lines:
    print("  SUBSTR_LINE %d\t%s" % (line, lines[line - 1].strip()[:90]))
