# -*- coding: utf-8 -*-
"""把已入账那块里每一枚 `路径:行号` 现读一遍。行按 "\\n" 切——与 grep -n、编辑器、GitHub 同一个形；
上一版按 splitlines() 切，在混合行尾的读数件上把行号整体顶偏，那是尺的错不是读数的错。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BLOCK = "D:/moodle/_qoder_ledger_inbox/_processed/pinggong_0035.md.inserted_003419"
REPO = "D:/moodle/_qoder_integration_20260919"
HEAD = "ebe51ee63efdf56596bc07fa2939c90f984808af"
TIP = "8940570c022950b705cc3b37139d1b8f7052c42a"
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"
COORD = re.compile(r"[A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:py|tsx|ts|txt|md|json|sql|log):[0-9]+")


def lines_of(ref, path):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)], capture_output=True)
    if proc.returncode:
        return None
    return proc.stdout.decode("utf-8", "replace").split("\n")


def ledger_lines():
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:CITYNEXUS_AGENT_CONTROL.md" % HEAD],
                          capture_output=True)
    if proc.returncode:
        proc = subprocess.run(["git", "-C", REPO, "show", "%s:CITYNEXUS_AGENT_CONTROL.md" % TIP],
                              capture_output=True)
    if proc.returncode:
        return open("D:/moodle/CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8",
                    errors="replace").read().split("\n")
    return proc.stdout.decode("utf-8", "replace").split("\n")


text = open(BLOCK, encoding="utf-8").read()
branch_body = None
for hit in sorted(set(COORD.findall(text))):
    path, number = hit.rsplit(":", 1)
    number = int(number)
    if path.startswith("review/pinggong-0610/"):
        body = lines_of(HEAD, path)
    elif path.startswith("CITYNEXUS_AGENT_CONTROL"):
        body = ledger_lines()
    elif path.startswith("backend/app/execution/") and path.split("/")[-1] in (
            "presence.py", "readiness.py", "group_presence.py"):
        body = lines_of(REP, path)
        note = "〔枝内那一代〕"
    else:
        body = lines_of(HEAD, path)
    if body is None:
        print("%-68s 取不到文件" % hit)
        continue
    if number > len(body):
        print("%-68s 越界（该文件 %d 行）" % (hit, len(body)))
        continue
    print("%-68s %s %s" % (hit, ("〔代表枝那代〕" if "execution" in path and body is lines_of(REP, path) else ""),
                          body[number - 1].strip()[:100]))
