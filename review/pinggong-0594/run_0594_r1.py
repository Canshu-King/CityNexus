# -*- coding: utf-8 -*-
"""ORD-0594 落笔与真跑（一条命令可重跑，读数逐件落盘）：
  1) 反控在前：只把测试放进现尖树、模块还不存在 → pytest 必须报模块取不到；
  2) 落三件事：collective_mediation.py 逐字节、candidate_evidence.py 只追加两枚新函数
     （尖上原有的 verified_interest_preference_fit 一字不动）、测试一枚；
  3) 后端 venv 真 import 这枚模块，打出它导出的名字数；
  4) pytest 真跑那枚测试，再跑尖上原有那批用到 candidate_evidence 的测试作回归；
  5) 逐枚 blob 与来源枝对拍、报本笔改动面。
任一断言不过就非零退出，不把"没数到"读成"没有缺陷"。"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
REP = "1725a449a50898e1c63889f0e7c0a81f347a7a1f"
TIP = open("D:/moodle/_pinggong_scratch/tip_0594.txt").read().strip()
VENV = "D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
MOD = "backend/app/collective_mediation.py"
CE = "backend/app/replanning/candidate_evidence.py"
TEST = "backend/tests/test_r27_collective_mediation.py"
NEW_FUNCS = ["_preference_matches_candidate", "verified_interest_preference_breakdown"]


def run(args, cwd=None):
    proc = subprocess.run(args, cwd=cwd or REPO, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def show_bytes(ref, path):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("ABORT git show %s:%s :: %s" % (ref, path, proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout


def die(msg):
    raise SystemExit("ABORT " + msg)


log = open("D:/moodle/_pinggong_scratch/0594_run.txt", "w", encoding="utf-8")


def note(text):
    print(text)
    log.write(text + "\n")


def tree_blob(rel):
    return run(["git", "-C", TREE, "hash-object", rel])[1].strip()


if run(["git", "-C", TREE, "rev-parse", "HEAD"])[1].strip() != TIP:
    die("工作树不在现尖那一代")

with open(TREE + "/" + TEST, "wb") as handle:
    handle.write(show_bytes(REP, TEST))
code, out, err = run([VENV, "-m", "pytest", "tests/" + os.path.basename(TEST), "-q", "--no-header"],
                     cwd=TREE + "/backend")
note("反控甲（只有测试、模块未落）pytest rc=%d" % code)
note("  " + "\n  ".join((out + err).strip().split("\n")[-6:]))
text = out + err
if code == 0 or "ModuleNotFoundError: No module named 'app.collective_mediation'" not in text:
    die("反控甲不成立：要的是「测试在、模块缺」那条真实报错（rc=2 + ModuleNotFoundError），实得 rc=%d" % code)
os.remove(TREE + "/" + TEST)

with open(TREE + "/" + MOD, "wb") as handle:
    handle.write(show_bytes(REP, MOD))
with open(TREE + "/" + TEST, "wb") as handle:
    handle.write(show_bytes(REP, TEST))

ce_tip = show_bytes(TIP, CE).decode("utf-8")
rep_ce = show_bytes(REP, CE).decode("utf-8")
blocks = {}
for name in NEW_FUNCS:
    match = re.search(r"^def %s\b.*?(?=^def |\Z)" % re.escape(name), rep_ce, re.S | re.M)
    if not match:
        die("代表枝里找不到 %s 的定义" % name)
    blocks[name] = match.group(0).rstrip("\n")
merged = ce_tip.rstrip("\n") + "\n\n\n" + "\n\n\n".join(blocks[n] for n in NEW_FUNCS) + "\n"
with open(TREE + "/" + CE, "w", encoding="utf-8", newline="") as handle:
    handle.write(merged)

kept = all(block in merged for block in ce_tip.strip().split("\n\n"))
note("尖上那枚文件的每个原段落仍在合并文本里：%s" % ("是" if kept else "否"))
if not kept:
    die("合并动到了既有文本")

code, out, err = run([VENV, "-c",
                      "import app.collective_mediation as m;"
                      "print('EXPORTS', len([n for n in dir(m) if not n.startswith('_')]))"],
                     cwd=TREE + "/backend")
note("真 import：rc=%d %s" % (code, out.strip() or err.strip()[:200]))
if code != 0:
    die("后端 venv 真 import 失败")

code, out, err = run([VENV, "-m", "pytest", "tests/" + os.path.basename(TEST), "-q", "--no-header"],
                     cwd=TREE + "/backend")
note("真跑本单测试：rc=%d" % code)
note("  " + "\n  ".join((out + err).strip().split("\n")[-6:]))
if code != 0:
    die("本单测试没跑绿，不落")

hits = run(["git", "-C", REPO, "grep", "-l", "candidate_evidence", TIP, "--", "backend/tests"])[1]
existing = sorted({line.split(":", 1)[1].strip() for line in hits.splitlines() if ":" in line})
existing = [p for p in existing if os.path.exists(TREE + "/" + p) and "test_r27_collective_mediation" not in p]
note("尖上原有引用到 candidate_evidence 的测试 %d 枚" % len(existing))
if existing:
    code, out, err = run([VENV, "-m", "pytest"] + ["tests/" + os.path.basename(p) for p in existing]
                          + ["-q", "--no-header"], cwd=TREE + "/backend")
    note("回归跑那批：rc=%d" % code)
    note("  " + "\n  ".join((out + err).strip().split("\n")[-6:]))
    if code != 0:
        die("回归没绿，不落")

for rel in (MOD, TEST):
    src = run(["git", "-C", REPO, "rev-parse", "%s:%s" % (REP, rel)])[1].strip()
    now = tree_blob(rel)
    if src != now:
        die("blob 与来源不符：%s src=%s now=%s" % (rel, src[:10], now[:10]))
note("逐枚 blob 与来源枝对拍：%s 两枚一致" % "与".join(os.path.basename(p) for p in (MOD, TEST)))
code, out, err = run(["git", "-C", TREE, "diff", "--numstat", TIP, "--", "backend"])
note("本笔改动面：")
note("  " + out.strip().replace("\n", "\n  "))
note("VERDICT ord0594_landed_and_ran")
log.close()
