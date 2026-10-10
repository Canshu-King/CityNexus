# -*- coding: utf-8 -*-
u"""第四栋楼 · 第二格：把上面那枚混了产物的提交**撤回**，重做一棵只含尺的。

**我犯的错（写在这里，下一班别重犯）**：第一版 `_push_rulers_r1.py` 只按"后缀是
.py/.md/.bat"挑文件，没按**目录**挑 ⇒ 把 `snap_ord0*` 七个快照目录（700 枚）和
`_s3_scratch` 的 6.7 MB 账本快照一起拷了进去。提交 `02d63fda58a2` 因此不纯。
（更大的那批 `_build_*`／`_serve_*`／`_verify_http_*` 是拷贝到一半发现的，
它们在**工作树**里但没进 add，所以没进提交——纯属运气，不是设计。）

`live_checks/` 底下实测有 **几十 GB** 的构建产物目录（`_tip_f1decd85` 单个 510 MB、
七个 `_build_*` 各 373 MB），那是**产物**，不是尺。⇒ 必须**按目录白名单**放，不是按后缀。

这一格做三件事：
  ① 撤回上一枚提交（`git reset --soft HEAD~1`，不动工作树、不 force、不动远端）；
  ② 按白名单重建：`patrol/*.py|md|bat` ＋ 顶层 `.py`（含那把门、交接稿体检、坐标清点）；
  ③ 提交后**验纯度**：提交里一条 `_build_`／`_serve_`／`snap_` 都没有。

**边界**：只在 `D:\moodle\_ruler_coords_wt`（我自己的 worktree）里动；
`D:\moodle\CityNexus` 那 22 条别人的脏行一个不碰；不推送（等坐标改完再推）。
"""
import io
import os
import shutil
import subprocess
import sys

SRC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WT = r"D:\moodle\_ruler_coords_wt"
DEST = os.path.join(WT, "ops", "watch_rulers")
BR = "review/ruler-retrievable-coords-r1"

# 白名单：**只有这三个来源**，其余一律不进
ALLOW_TOP_FILES = True          # live_checks/ 顶层的 .py（含 claim_coordinate_check_r7.py）
ALLOW_SUBDIRS = ("patrol",)      # 只这一层子目录
SKIP_NAME_PARTS = (".bak", "rounds", "__pycache__")
KEEP_EXT = (".py", ".md", ".bat")


def sh(args, t=900):
    r = subprocess.run(args, cwd=WT, capture_output=True, timeout=t)
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace"), (r.stderr or b"").decode("utf-8", "replace")


def wanted(fn):
    if not fn.endswith(KEEP_EXT):
        return False
    return not any(p in fn for p in SKIP_NAME_PARTS)


def collect():
    out = []
    for fn in sorted(os.listdir(SRC)):
        p = os.path.join(SRC, fn)
        if os.path.isfile(p) and ALLOW_TOP_FILES and wanted(fn):
            out.append((p, fn))
    for sub in ALLOW_SUBDIRS:
        base = os.path.join(SRC, sub)
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            dn[:] = [d for d in dn if d not in ("rounds", "__pycache__")]
            for fn in sorted(fns):
                if not wanted(fn):
                    continue
                full = os.path.join(dp, fn)
                out.append((full, os.path.relpath(full, SRC).replace("\\", "/")))
    return out


def main():
    rc, out, _ = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if out.strip() != BR:
        print(u"REFUSE：worktree 在 %s 这条枝（应为 %s）" % (out.strip() or "?", BR))
        return 1

    # ① 撤回上一枚
    rc0, out0, _ = sh(["git", "rev-parse", "HEAD"])
    rc, out, err = sh(["git", "reset", "--soft", "HEAD~1"])
    print(u"① reset --soft rc=%d（撤的是 %s）%s" % (rc, out0.strip()[:12],
                                                "" if rc == 0 else err[:160]))

    # ② 重建工作树里那份拷贝
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    picked = collect()
    for full, rel in picked:
        dst = os.path.join(DEST, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(full, dst)
    print(u"② 白名单挑到 %d 枚（来源只有：%s ＋顶层 .py）"
          % (len(picked), u"、".join(ALLOW_SUBDIRS)))

    rc, out, err = sh(["git", "add", "--", os.path.relpath(DEST, WT)])
    if rc != 0:
        print(u"add 失败：%s" % err[:200])
        return 1

    msg = (u"值守的尺本体（纯尺：只有 patrol/ 一层与顶层脚本，无产物目录）\n\n"
           u"图纸出自账本 ## ORDERS 段 23:0x 的派单（第四栋 · 42d1a6fa）：坐标要可 cat-file 取回，\n"
           u"尺就得先在枝上。有了这枝，块里能引 ops/watch_rulers/<脚本>.py:行号，\n"
           u"那个行号别人自己就能打开看，不再只活在我本机。\n\n"
           u"上一版（02d63fda58a2）混进了 snap_ord0* 快照目录与账本快照，已撤回重做。\n"
           u"live_checks/ 底下实测有几十 GB 的 _build_*/_serve_*/_verify_http_* 产物目录，\n"
           u"按后缀挑会误捞 ⇒ 这一版按目录白名单挑。")
    rc, out, err = sh(["git", "commit", "-m", msg])
    if rc != 0:
        print(u"commit 失败：%s" % err[:300])
        return 1
    rc, sha, _ = sh(["git", "rev-parse", "HEAD"])
    sha = sha.strip()

    # ③ 纯度验
    rc, names, _ = sh(["git", "ls-tree", "-r", "--name-only", "HEAD", "ops/watch_rulers"])
    names = [n for n in names.splitlines() if n.strip()]
    bad = [n for n in names if any(k in n for k in
                                  ("_build_", "_serve_", "_verify_http", "_stack_src",
                                   "snap_ord", "_s3_scratch", "_sweep_scratch", "node_modules"))]
    rc, typ, _ = sh(["git", "cat-file", "-t", sha])
    rc2, tree, _ = sh(["git", "rev-parse", "HEAD^{tree}"])
    print(u"③ 纯度：提交里 %d 条路径，带产物/快照目录名的 **%d** 条（应为 0）"
          % (len(names), len(bad)))
    if bad:
        for n in bad[:10]:
            print(u"   混进：%s" % n)
    print(u"提交 = %s" % sha)
    print(u"树   = %s" % tree.strip())
    print(u"cat-file 类型 = %s ⇒ 可取回已证" % typ.strip())
    with io.open(os.path.join(DEST, "COMMIT_THIS.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(sha + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())