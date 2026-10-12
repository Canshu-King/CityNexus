# -*- coding: utf-8 -*-
"""ORD-0610 证据在新一代尖上重跑：同一批探针，落 LF 行尾的读数文件（上一批读数件是混合行尾，
害得按 splitlines 计数的校验尺把行号顶偏——这一批起，读数一律只按 \n 分行）。
跑完必须把工作树恢复干净：presence 那两枚字节只在树里活一拍。"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
BACK = TREE + "/backend"
OUTDIR = TREE + "/review/pinggong-0610"
TIP = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.split("\t")[0].strip()
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def save(name, text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    with open(os.path.join(OUTDIR, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("WROTE %s (%d 行)" % (name, len(text.split("\n"))))


print("本轮尖 %s｜来源代 %s" % (TIP, REP))
if len(TIP) != 40:
    sys.exit("ABORT 取不到现尖")

mod = git("show", "%s:backend/app/execution/presence.py" % REP).stdout
test = git("show", "%s:backend/tests/test_grounded_presence.py" % REP).stdout
if not mod or not test:
    sys.exit("ABORT 来源代取不到字节")

before = git("status", "--porcelain", cwd=TREE).stdout
with open(BACK + "/app/execution/presence.py", "w", encoding="utf-8", newline="\n") as h:
    h.write(mod)
with open(BACK + "/tests/test_grounded_presence.py", "w", encoding="utf-8", newline="\n") as h:
    h.write(test)

suite = subprocess.run([VENV, "-m", "pytest", "tests/test_grounded_presence.py", "-q", "--no-header"],
                       cwd=BACK, capture_output=True)
save("r2_suite_on_tip.txt",
     "尖 %s\n来源代 %s\n命令 %s -m pytest tests/test_grounded_presence.py -q --no-header\nrc=%d\n%s\n[stderr]\n%s"
     % (TIP, REP, os.path.basename(VENV), suite.returncode,
        suite.stdout.decode("utf-8", "replace"), suite.stderr.decode("utf-8", "replace")))

probe = subprocess.run([VENV, "-X", "utf8", OUTDIR + "/probe_real_db_r1.py"], cwd=BACK,
                       capture_output=True)
raw = probe.stdout.decode("utf-8", "replace")
with open(OUTDIR + "/r2_real_db_probe.txt", "w", encoding="utf-8", newline="\n") as h:
    h.write("尖 %s\nrc=%d\n%s" % (TIP, probe.returncode, raw))
print("探针回话：")
for row in raw.replace("\r\n", "\n").split("\n"):
    if row.startswith(("A0", "A1", "A2", "A3", "A4")) or "Error" in row or "state=" in row:
        print("   " + row.strip()[:120])

os.remove(BACK + "/app/execution/presence.py")
os.remove(BACK + "/tests/test_grounded_presence.py")
after = git("status", "--porcelain", cwd=TREE).stdout
if after.strip() and after.strip() != before.strip():
    sys.exit("ABORT 探针字节没清干净：\n%s" % after)
print("工作树回到探针前状态：%d 行未登记（与跑前同）" % len(after.splitlines()))
