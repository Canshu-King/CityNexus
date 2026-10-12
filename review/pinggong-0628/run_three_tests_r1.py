# -*- coding: utf-8 -*-
"""ORD-0620 第一条的红因图：把那三枚「代表枝作者写的现成测试」逐字节放进现尖树跑一次，
每条红配上它卡在哪儿的现读坐标。跑完必须把工作树清回干净——测试字节只活一拍。

落法照号令者那条：逐字节用代表枝那一枚（blob 对得上才算吸收），不许重写断言凑绿；
本脚本只读只跑，不落任何产品字节。"""
import hashlib
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
BACK = TREE + "/backend"
VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"
OUT = TREE + "/review/pinggong-0628/three_tests_at_tip.txt"
TESTS = ["test_guardian_pulse.py", "test_event_resolution_projection.py",
         "test_r14_terminal_disruption_recovery.py"]
LINES = []


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=1800)


def run(args, cwd=BACK):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1800)


def note(text):
    LINES.append(text)
    print(text)


tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1",
          cwd="D:/moodle/CityNexus").stdout.split("\t")[0].strip()
note("现尖 %s｜代表枝 %s" % (tip, REP))

note("")
note("[一] 三枚测试在尖上与枝上的形状（行枚与 blob 逐枚现读）")
paths = []
for name in TESTS:
    path = "backend/tests/%s" % name
    body = git("show", "%s:%s" % (REP, path)).stdout
    on_tip = git("cat-file", "-e", "%s:%s" % (tip, path)).returncode == 0
    blob = hashlib.sha1(b"blob %d\0" % len(body.encode()) + body.encode()).hexdigest()
    note("   %-44s 枝上 %3d 行｜尖上 %s｜blob %s"
         % (name, body.count("\n"), "已有" if on_tip else "没有", blob[:12]))
    paths.append((name, body))

note("")
note("[二] 尖上四处符号面（每条红的落点，逐枚现读命中数与行号）")
for label, path, needle in (
        ("main 侧入口 pulse_journey", "backend/app/main.py", "def pulse_journey"),
        ("已存在的实现 pulse_journey", "backend/app/agent/autorun.py", "def pulse_journey"),
        ("schema 词表里的 OPPORTUNITY_WINDOW", "backend/app/schemas.py", "OPPORTUNITY_WINDOW"),
        ("配置项 traveler_auth_secret", "backend/app/core/config.py", "traveler_auth_secret"),
        ("建表语句里的 event_type CHECK", "backend/db/schema.sql", "CHECK (event_type IN")):
    body = git("show", "%s:%s" % (tip, path)).stdout
    hits = [str(i) for i, line in enumerate(body.split("\n"), start=1) if needle in line]
    note("   %-34s %s:%s 命中 %d 处%s"
         % (label, path, (hits[0] if hits else "无"), len(hits),
            ("（行 " + ",".join(hits[:4]) + "）") if len(hits) > 1 else ""))

note("")
note("[三] 逐字节放进尖树跑一次（collect 先报条数，再跑）")
for name, body in paths:
    with open(os.path.join(BACK, "tests", name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
args = [VENV, "-m", "pytest"] + ["tests/" + n for n in TESTS]
collect = run(args + ["-q", "--no-header", "--collect-only"])
tail = [l for l in collect.stdout.split("\n") if "test" in l and ("selected" in l or "collected" in l or "error" in l)]
note("   collect 退出码 %d｜尾行 %s" % (collect.returncode, " ".join(tail[-2:]) or "(没抓到条数行)"))
executed = run(args + ["-q", "--no-header", "--tb=line"])
note("   执行退出码 %d" % executed.returncode)
for line in executed.stdout.split("\n"):
    s = line.strip()
    if re.match(r"^(FAILED|[0-9]+ (passed|failed))", s) or "AssertionError" in s or "Error:" in s or "has no attribute" in s or "CHECK constraint" in s or "literal_error" in s:
        note("   " + s[:300])
summary = [l.strip() for l in executed.stdout.split("\n") if re.match(r"^[0-9]+ (passed|failed)", l.strip())
           or " failed" in l and "in " in l]
note("   判语行：%s" % (summary[-1] if summary else "取不到"))

for name in TESTS:
    os.remove(os.path.join(BACK, "tests", name))
dirty = [l for l in git("status", "--porcelain", cwd=TREE).stdout.split("\n")
         if l.strip() and "review/pinggong-0628" not in l]
note("")
note("[四] 跑完工作树：测试字节已删，除本目录读数件外未登记改动 %d 处" % len(dirty))
for l in dirty:
    note("   残留 %s" % l)

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(LINES) + "\n")
print("")
print("读数落 %s（%d 行）" % (OUT, len(LINES)))
