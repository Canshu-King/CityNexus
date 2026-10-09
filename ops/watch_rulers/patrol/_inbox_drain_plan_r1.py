# -*- coding: utf-8 -*-
r"""收件口「下一跳能吞多少」的预演（只读，不跑门）。

为什么不直接跑门的 DRY：门自带 selftest 会往收件口根目录写 `selftest_9999.md` / `nope.md`
两枚探针，而 `selftest_9999.md` **恰好过命名闸**（`^[A-Za-z0-9._-]+_[0-9]{4}\.md$`）。
号令者的笔此刻在跑（名册 0 分前），我要是并发跑门，他那一次 `--apply` 就可能把我探针里那句
`### SELFTEST lane good_block` 当成真块插进账本。所以这里**不执行门**，只 import 门自己的函数
（`title_key` / `dedupe` / `candidate_files` / `shape_problem`）来复算它的判据，坐标闸单独调
`claim_coordinate_check_r7.py --text`（它只在给 `--out` 时才写文件，本件不传）。
所有结论一律写「预测」：门的 DRY 模式不评估这两闸，我的复算不等于门会这么做。
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
CHK = os.path.join(LC, "claim_coordinate_check_r7.py")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
            http_proxy="", https_proxy="")

sys.path.insert(0, LC)  # 门自己的 import 需要 live_checks 在路径上
spec = importlib.util.spec_from_file_location("door", os.path.join(LC, "ledger_inbox_apply_r2.py"))
door = importlib.util.module_from_spec(spec)
spec.loader.exec_module(door)

root = sorted([os.path.join(INBOX, f) for f in os.listdir(INBOX) if f.endswith(".md")],
              key=lambda x: os.path.getmtime(x))
print("收件口根目录 %d 枚（现读 %s）" % (len(root), time.strftime("%H:%M:%S")))

by_title = {}
for p in root:
    fl = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    first = fl[0].strip() if fl else ""
    by_title.setdefault(door.title_key(first), []).append(p)
print()
print("一、门自己的 title_key 分组（同组=同一块的多次投稿，只有一枚会被插，其余记 superseded）：")
for k, g in sorted(by_title.items(), key=lambda kv: -len(kv[1])):
    if len(g) > 1:
        names = sorted(os.path.basename(x) for x in g)
        print("   同块 %d 枚：%s ⇒ 门按文件名排序保留 **%s**（不是按 mtime！）" % (len(g), names, names[-1]))
        print("      块头：%s" % k[:90])
dup_groups = [g for g in by_title.values() if len(g) > 1]

print()
print("二、逐枚预测（闸一=名形 :81；闸二=坐标尺 r7）：")
n_pass, n_refused, n_skip = [], [], []
for p in root:
    name = os.path.basename(p)
    sp = None
    try:
        sp = door.shape_problem(name)
    except TypeError:
        sp = door.shape_problem(io.open(p, encoding="utf-8", errors="replace").read(), name)
    except Exception as ex:
        sp = "shape_problem 调用形不对：%s" % type(ex).__name__
    if sp:
        n_skip.append(name)
        print("   %-24s 闸一 SKIP｜%s" % (name, str(sp)[:70]))
        continue
    # 门的真判据是 r7 带 --expect-clean（不带这面旗时它只报数、恒 rc=0，
    # 我第一版就栽在这里，把被拒的块判成「可插」——假绿）。第二枚 bolt 另扫逐字 40 位可否解析。
    q = subprocess.run([PYEXE, CHK, "--text", p, "--expect-clean"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=600)
    out = (q.stdout or "").strip()
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    unres = []
    for h in set(re.findall(r"\b[0-9a-f]{40}\b", txt)):
        c = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "cat-file", "-t", h],
                           capture_output=True, text=True, env=ENV, timeout=120)
        if c.returncode:
            unres.append(h)
    if unres:
        print("   %-24s 第二 bolt 预测红：%d 枚 40 位本机不可解析 %s（我不 fetch 共享仓，所以这一判只保守偏红）"
              % (os.path.basename(p), len(unres), [x[:12] for x in unres]))
    if q.returncode == 0 and not unres:
        n_pass.append(name)
        print("   %-24s 闸一过｜闸二 rc=0 ⇒ 预测可插" % name)
    else:
        n_refused.append(name)
        bad = [l for l in out.split(chr(10)) if l.strip()][:3]
        print("   %-24s 闸一过｜闸二 rc=%d ⇒ 预测被拒" % (name, q.returncode))
        for l in bad:
            print("        ! " + l[:130])

print()
print("三、一次 `--apply` 的预演读数：可插 %d 枚 %s｜预测被拒 %d 枚 %s｜名不合被静默 SKIP %d 枚 %s"
      % (len(n_pass), n_pass, len(n_refused), n_refused, len(n_skip), n_skip))
print("   同块多枚的组数：%d（若 >0，注意上面那条「按文件名不按 mtime」）" % len(dup_groups))
print()
print("边界：不执行门、0 写账本、0 代插、0 改车道文件；两闸都是**复算预测**，门的 DRY 不跑这两闸。")
