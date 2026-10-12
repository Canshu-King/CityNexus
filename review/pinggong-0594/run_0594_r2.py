# -*- coding: utf-8 -*-
"""ORD-0594 落笔与真跑 v2（读数一件一个状态名，绝不覆掉已交出去的那件）：
  0) 断言来源代三方一致：尺里写的 == 对账表第 29 行 pin 的 == GitHub 上那枚代表枝当前头
     （v1 就是栽在本地 bare 那份是旧代，摘错了一代，少了 8 行 authority_scope_facts）；
  1) 反控：把已落的模块临时挪开、测试留在原位 → pytest 必须报 ModuleNotFoundError；挪回来即恢复；
  2) 用 pin 那一代逐字节重写模块与测试；candidate_evidence 只在尾部追加两枚新函数，既有文本一字不动；
  3) 后端 venv 真 import；本单测试真跑；尖上原有引用那枚文件的测试作回归；
  4) 逐枚 blob 与来源对拍、报本笔相对现尖的改动面。
任一断言不过就非零退出。"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
BRANCH = "refs/heads/review/屏工-0594-r1"
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"
REPREF = "refs/heads/gpt/revolution-r33-open-world-journey-adaptation"
TIP = open("D:/moodle/_pinggong_scratch/tip_0594.txt").read().strip()
VENV = "D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
MOD = "backend/app/collective_mediation.py"
CE = "backend/app/replanning/candidate_evidence.py"
TEST = "backend/tests/test_r27_collective_mediation.py"
NEW_FUNCS = ["_preference_matches_candidate", "verified_interest_preference_breakdown"]
OUT = "D:/moodle/_pinggong_scratch/0594_run2.txt"


def run(args, cwd=None):
    proc = subprocess.run(args, cwd=cwd or REPO, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def show_bytes(ref, path):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("ABORT git show %s:%s :: %s" % (ref, path,
                                                          proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout


def blob(ref, path):
    return run(["git", "rev-parse", "%s:%s" % (ref, path)])[1].strip()


def die(msg):
    raise SystemExit("ABORT " + msg)


log = open(OUT, "w", encoding="utf-8")


def note(text):
    print(text)
    log.write(text + "\n")


head = run(["git", "-C", TREE, "rev-parse", "HEAD"])[1].strip()
if run(["git", "-C", TREE, "merge-base", "--is-ancestor", TIP, head])[0] != 0:
    die("本枝不含有现尖（先合尖再跑）")
note("本枝头 %s 含现尖 %s：是" % (head[:12], TIP[:12]))

pin_rows = show_bytes(TIP, "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv").decode("utf-8").splitlines()
want = REPREF.replace("refs/heads/", "")
pinned = [row.split("\t")[1] for row in pin_rows if row.split("\t")[0] == want]
if len(pinned) != 1:
    die("对账表里 %s 命中 %d 行，不是恰好一行" % (want, len(pinned)))
pinned = pinned[0]
remote = run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin", REPREF])[1].split()[0]
if REP != pinned or REP != remote:
    die("来源代不符：尺里 %s，对账表 pin %s，GitHub 当前头 %s" % (REP[:12], pinned[:12], remote[:12]))
note("来源代三方一致：尺 %s = 对账表第 29 行 pin %s = GitHub 该枝当前头 %s"
     % (REP[:12], pinned[:12], remote[:12]))

os.rename(TREE + "/" + MOD, TREE + "/" + MOD + ".off")
code, out, err = run([VENV, "-m", "pytest", "tests/" + os.path.basename(TEST), "-q", "--no-header"],
                     cwd=TREE + "/backend")
text = out + err
note("反控（模块临时挪开）pytest rc=%d" % code)
note("  " + "\n  ".join(text.strip().split("\n")[-4:]))
if code == 0 or "ModuleNotFoundError: No module named 'app.collective_mediation'" not in text:
    os.rename(TREE + "/" + MOD + ".off", TREE + "/" + MOD)
    die("反控不成立：要的是 rc=2 且原话含 ModuleNotFoundError，实得 rc=%d" % code)
os.rename(TREE + "/" + MOD + ".off", TREE + "/" + MOD)

with open(TREE + "/" + MOD, "wb") as handle:
    handle.write(show_bytes(REP, MOD))
with open(TREE + "/" + TEST, "wb") as handle:
    handle.write(show_bytes(REP, TEST))
if blob(REP, MOD) != run(["git", "-C", TREE, "hash-object", MOD], cwd=TREE)[1].strip():
    die("模块 blob 与来源不符")

ce_tip = show_bytes(TIP, CE).decode("utf-8")
rep_ce = show_bytes(REP, CE).decode("utf-8")
blocks = {}
for name in NEW_FUNCS:
    match = re.search(r"^def %s\b.*?(?=^def |\Z)" % re.escape(name), rep_ce, re.S | re.M)
    if not match:
        die("来源代里没有 %s 的定义" % name)
    blocks[name] = match.group(0).rstrip("\n")
merged = ce_tip.rstrip("\n") + "\n\n\n" + "\n\n\n".join(blocks[n] for n in NEW_FUNCS) + "\n"
if blob(REP, CE) != blob(TIP, CE):
    note("注意：来源代与现尖的那枚文件本就不同代，我只从来源代取那两枚新函数，其余以现尖为准")
with open(TREE + "/" + CE, "w", encoding="utf-8", newline="") as handle:
    handle.write(merged)
paragraphs = [chunk for chunk in ce_tip.rstrip("\n").split("\n\n")]
kept = all(chunk in merged for chunk in paragraphs)
note("现尖那枚文件的每个段落逐字仍在合并文本里：%s（段落 %d 段）" % ("是" if kept else "否", len(paragraphs)))
if not kept:
    die("合并动到了既有文本")

code, out, err = run([VENV, "-c",
                      "import app.collective_mediation as m;"
                      "print('EXPORTS', len([n for n in dir(m) if not n.startswith('_')]));"
                      "print('HAS_SCOPE', 'authority_scope_facts' in open('app/collective_mediation.py',encoding='utf-8').read())"],
                     cwd=TREE + "/backend")
note("后端 venv 真 import：rc=%d %s" % (code, " / ".join(out.strip().splitlines())))
if code != 0 or "HAS_SCOPE True" not in out:
    die("import 失败或 pin 那一代那 8 行没进来")

code, out, err = run([VENV, "-m", "pytest", "tests/" + os.path.basename(TEST), "-q", "--no-header"],
                     cwd=TREE + "/backend")
note("本单测试真跑：rc=%d %s" % (code, (out + err).strip().splitlines()[-1]))
if code != 0:
    die("本单测试没跑绿")

hits = run(["git", "grep", "-l", "candidate_evidence", TIP, "--", "backend/tests"])[1]
existing = sorted({line.split(":", 1)[1].strip() for line in hits.splitlines() if ":" in line})
existing = [p for p in existing if os.path.exists(TREE + "/" + p) and os.path.basename(TEST) not in p]
note("尖上引用那枚文件的其他测试 %d 枚" % len(existing))
if existing:
    code, out, err = run([VENV, "-m", "pytest"] + ["tests/" + os.path.basename(p) for p in existing]
                          + ["-q", "--no-header"], cwd=TREE + "/backend")
    note("回归真跑那批：rc=%d %s" % (code, (out + err).strip().splitlines()[-1]))
    if code != 0:
        die("回归没绿")

for rel in (MOD, TEST):
    now = run(["git", "-C", TREE, "hash-object", rel])[1].strip()
    if now != blob(REP, rel):
        die("blob 不符 %s" % rel)
    note("逐字节对拍 %s blob %s 行数 %d 字节 %d"
         % (os.path.basename(rel), now[:12],
            len(show_bytes(REP, rel).splitlines()), len(show_bytes(REP, rel))))
code, out, err = run(["git", "-C", TREE, "diff", "--numstat", TIP, "--", "backend"])
note("本枝相对现尖的改动面：\n  " + out.strip().replace("\n", "\n  "))
note("VERDICT ord0594_pinned_generation_landed_and_ran branch=%s" % head[:12])
log.close()
