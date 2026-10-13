# -*- coding: utf-8 -*-
"""ORD-0652 的选料尺：号令者列的那八枚测试，逐枚先验字节（blob 对得上才算同一枚），
再报「尖上有没有」，再逐字节放进尖树跑一次，取 collected 与 failed 两栏。
跑完删干净：测试字节只活一拍，本尺不落任何产品字节。"""
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
BARE = "D:/moodle/CityNexus"
OUT = TREE + "/review/pinggong-0652/eight_tests_baseline.txt"

# 号令者给的（路径, 那一代短号, blob 前十二位）
ITEMS = [
    ("backend/tests/test_r21_autonomous_future_synthesis.py", "1c1fb60fcff7", "7978a53ceec2"),
    ("backend/tests/test_r22_opportunity_capture.py", "78d6532e50c6", "a11c0094e9f0"),
    ("backend/tests/test_agent_runtime_state_epoch.py", "843844c5587d", "0f381e78e9a9"),
    ("backend/tests/test_event_resolution_projection.py", "843844c5587d", "0862062fbf10"),
    ("backend/tests/test_r23_adaptive_traveler_twin.py", "843844c5587d", "44a8b6e0185d"),
    ("backend/tests/test_r24_adaptive_memory.py", "843844c5587d", "42c95beed3b3"),
    ("backend/tests/test_real_city_overpass_union.py", "843844c5587d", "f303fecc371b"),
    ("backend/tests/test_replan_schedule_timezone.py", "843844c5587d", "21eb1450aa17"),
]
LINES = []


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)


def note(t):
    LINES.append(t)
    print(t)


tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1",
          cwd=BARE).stdout.split("\t")[0].strip()
note("现尖 %s（本尺所有「尖上」判断都对着这一代）" % tip)
note("")

results = {}
for path, gen, want_blob in ITEMS:
    name = path.split("/")[-1]
    body = git("show", "%s:%s" % (gen, path)).stdout
    if not body:
        note("%-46s 那一代取不到字节（%s）" % (name, gen))
        results[name] = None
        continue
    raw = git("show", "%s:%s" % (gen, path)).stdout.encode("utf-8", "replace")
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (gen, path)], capture_output=True)
    blob = hashlib.sha1(b"blob %d\0" % len(proc.stdout) + proc.stdout).hexdigest()
    on_tip = git("cat-file", "-e", "%s:%s" % (tip, path)).returncode == 0
    lines = proc.stdout.decode("utf-8", "replace").count("\n")
    tests = len(re.findall(r"^def test_", proc.stdout.decode("utf-8", "replace"), re.M))
    ok = blob.startswith(want_blob)
    note("%-46s blob %s｜对得上号令者那枚=%s｜%d 行、%d 枚用例｜尖上=%s"
         % (name, blob[:12], "是" if ok else "否", lines, tests, "已有" if on_tip else "没有"))
    results[name] = (path, proc.stdout, gen, blob, on_tip)

note("")
note("[跑] 逐枚按原字节放进尖树，各跑一次（collected / failed 两栏）")
for name, data in results.items():
    if data is None:
        continue
    path, raw, gen, blob, on_tip = data
    with open(os.path.join(BACK, "tests", name), "wb") as handle:
        handle.write(raw)
    collect = subprocess.run([VENV, "-m", "pytest", "tests/" + name, "-q", "--no-header",
                              "--collect-only"], cwd=BACK, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=900)
    execd = subprocess.run([VENV, "-m", "pytest", "tests/" + name, "-q", "--no-header", "--tb=line"],
                           cwd=BACK, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1200)
    col = [l.strip() for l in collect.stdout.split("\n") if "collected" in l or "error" in l.lower()]
    summ = [l.strip() for l in execd.stdout.split("\n") if re.match(r"^[0-9]+ (passed|failed)", l.strip())
            or " passed" in l and " in " in l or " failed" in l and " in " in l]
    firsts = [l.strip()[:150] for l in execd.stdout.split("\n")
              if re.match(r"^FAILED|^E ", l.strip())][:2]
    note("   %-46s collect rc=%d｜%s｜执行 rc=%d｜%s"
         % (name, collect.returncode, " ".join(col[-1:]) or "(无条数行)", execd.returncode,
            summ[-1] if summ else "(无判语行)"))
    for f in firsts:
        note("       红的一手：%s" % f)
    os.remove(os.path.join(BACK, "tests", name))

dirty = [l for l in git("status", "--porcelain", cwd=TREE).stdout.split("\n")
         if l.strip() and "review/pinggong-0652" not in l]
note("")
note("[清] 跑完工作树除本目录外未登记改动 %d 处" % len(dirty))
for l in dirty:
    note("   残留 %s" % l)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(LINES) + "\n")
print("")
print("读数落 %s（%d 行）" % (OUT, len(LINES)))
