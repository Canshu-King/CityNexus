# -*- coding: utf-8 -*-
u"""第四栋楼 · 把值守的尺本体放进权威线上的一条枝，让坐标**可 cat-file 取回**。

图纸（账本 `## ORDERS` 段，23:0x 号令者派单）：
  「把你名下所有尺的读数出处，都改成权威线上真实可取回的那个对象
    （**把尺本体随块推上枝、块里改引枝上的提交**）」

这一格做**前半**：把尺本体落进枝上。后半（块里改引枝上的提交）要等提交哈希出来才有得引。

放什么（不放全盘，只放**读数出处会用到的尺**）：
  · `live_checks/patrol/*.py` —— 巡逻与它的各把尺（含形状闸、末态尺、落地表）
  · `live_checks/claim_coordinate_check_r7.py` —— 那把门
  · `live_checks/*.py`（顶层）—— 交接稿体检、坐标清点等
**不放**：账本副本（`_rem_ledger_*.md`／`_s3_ledger_copy*.md`）、备份件（`*.bak*`）、
每一拍的临时档（`rounds/`）、日志（`*.log`）、账本本体（在 D:/moodle 根下，不是本仓的东西）。

为什么这么切：`rounds/` 有几十个逐拍档、日志每轮追加，把它们提交上去会让这枝
一天涨几十兆，而坐标引用的从来不是它们。

安全：只在**我自己的 worktree** 里 add/commit，不碰 `D:/moodle/CityNexus` 的工作区
（那里有别人 22 条脏行）；不推送——推送等提交哈希出来、坐标改成引它之后再做。
"""
import io
import os
import shutil
import subprocess
import sys
import time

SRC_ROOT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WT = r"D:\moodle\_ruler_coords_wt"
DEST = os.path.join(WT, "ops", "watch_rulers")
BR = "review/ruler-retrievable-coords-r1"

EXCLUDE_EXT = (".log", ".bak", ".pyc")
EXCLUDE_SUB = ("rounds", "__pycache__")


def is_wanted(name):
    if EXCLUDE_SUB[0] in name.split(os.sep):
        return False
    if any(name.endswith(e) for e in EXCLUDE_EXT):
        return False
    if ".bak" in name or name.endswith(".log"):
        return False
    if name.startswith("_rem_ledger") or name.startswith("_s3_ledger_copy") or name == "_ledger_remote.md":
        return False
    return name.endswith(".py") or name.endswith(".md") or name.endswith(".bat")


def sh(args, cwd=WT, t=600):
    r = subprocess.run(args, cwd=cwd, capture_output=True, timeout=t)
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace"), (r.stderr or b"").decode("utf-8", "replace")


def main():
    if not os.path.isdir(WT):
        print(u"REFUSE：worktree 不在 %s" % WT)
        return 1
    rc, out, err = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or out.strip() != BR:
        print(u"REFUSE：worktree 在 %s 这条枝（应为 %s）⇒ 不动" % (out.strip() or "?", BR))
        return 1

    picked = []
    for dirpath, dirnames, filenames in os.walk(SRC_ROOT):
        rel = os.path.relpath(dirpath, SRC_ROOT)
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDE_SUB and d != "__pycache__"]
        if rel.count(os.sep) > 1:        # 只吃 patrol/ 一层与顶层，不往深处扫
            dirnames[:] = []
            continue
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if not is_wanted(fn):
                continue
            r = os.path.relpath(full, SRC_ROOT).replace("\\", "/")
            picked.append((full, r))

    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    for full, rel in picked:
        dst = os.path.join(DEST, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(full, dst)
    print(u"复制 %d 枚尺到 %s" % (len(picked), os.path.relpath(DEST, WT).replace("\\", "/")))

    rc, out, err = sh(["git", "add", "--", os.path.relpath(DEST, WT)])
    if rc != 0:
        print(u"add 失败 rc=%d：%s" % (rc, err[:200]))
        return 1
    rc, out, _ = sh(["git", "status", "--porcelain"])
    n_add = len([l for l in out.splitlines() if l.strip()])
    print(u"git status 脏行 %d 条（应等于复制数，且**不含**别人那 22 条）" % n_add)

    msg = (u"值守的尺本体：坐标要可 cat-file 取回，尺就得先在枝上\n\n"
           u"图纸出自账本 ## ORDERS 段 23:0x 的派单（第四栋 · 42d1a6fa）。\n"
           u"放进来的是巡逻与它的各把尺、那把门（claim_coordinate_check_r7.py）、\n"
           u"以及顶层交接/体检/清点脚本；**不放**账本副本、备份件、逐拍档与日志。\n"
           u"有了这枝，块里就能引 `ops/watch_rulers/...py:行号`——那个行号可 cat-file 取回，\n"
           u"交出去别人自己就能打开看，不再只活在我本机。")
    rc, out, err = sh(["git", "commit", "-m", msg])
    if rc != 0:
        print(u"commit 失败 rc=%d：%s" % (rc, err[:300]))
        return 1
    print(out.strip()[:160])
    rc, sha, _ = sh(["git", "rev-parse", "HEAD"])
    sha = sha.strip()
    print(u"提交 = %s" % sha)
    rc2, tree, _ = sh(["git", "rev-parse", "HEAD^{tree}"])
    print(u"树   = %s" % tree.strip())
    rc3, typ, _ = sh(["git", "cat-file", "-t", sha])
    print(u"cat-file 解析类型 = %s（可取回已证）" % typ.strip())
    rc4, ls, _ = sh(["git", "ls-tree", "-r", "--name-only", "HEAD"])
    print(u"这枝上 %d 条路径" % len([l for l in ls.splitlines() if l.strip()]))
    with io.open(os.path.join(WT, "ops", "watch_rulers", "COMMIT_THIS.txt"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(sha + "\n")
    print(u"提交号也落在枝上（ops/watch_rulers/COMMIT_THIS.txt），块里可直接引这枚路径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())