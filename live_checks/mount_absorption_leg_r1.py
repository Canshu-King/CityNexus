# -*- coding: utf-8 -*-
"""ORD-0592 mount: put the absorption leg into the landing loop as one more per-round call.

Safety shape learned the hard way on this project (the loop is alive and lands code every round):
  * nothing is written unless --apply is passed; the default writes a preview file and compiles it;
  * the anchor must match EXACTLY once, otherwise abort;
  * the inserted text CONTAINS the anchor, so the adopt-join leg it sits after can never be eaten;
  * byte identity is proved: mounted.replace(insertion, "", 1) == original;
  * --apply keeps a timestamped backup and py_compiles the result before it reports success;
  * the loop is not restarted here -- restarting it is the commander's call, and a bad edit kills five
    legs at once, so this file only ever edits the text.
"""
import argparse
import io
import os
import py_compile
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET = os.environ.get(
    "CNX_MOUNT_LOOP",
    r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_auto_land_loop_r1.py")

ANCHOR = (u'            except Exception as exc:\n'
          u'                log("round %d adopt-join crashed: %r" % (i, exc))\n')

DELTA = (
    u'            # ORD-0592: revolution 吸收面每拍量一次，数落进带日期的状态件；面涨了或退化由这条腿\n'
    u'            # 自己交一块到收件口——冷却与入账自查都装在腿上，所以每轮叫一次不会刷屏，也绝不会\n'
    u'            # 把「取不到数」当成「没问题」。它只观察，不参与落地判定，不动权威线。\n'
    u'            try:\n'
    u'                ab = run([PY, os.path.join(LC, "patrol", "_absorption_leg_r1.py"),\n'
    u'                          "--apply", "--round", str(i)], timeout=900)\n'
    u'                abl = [ln for ln in (ab.stdout or "").splitlines()\n'
    u'                       if ln.startswith(("ABS-ROW", "ABS-LEG", "ABS-QUIET", "ABSORB-COOLED",\n'
    u'                                           u"\u5df2\u4ea4", u"REFUSE", "DRY ROW"))]\n'
    u'                log("round %d absorption %s" % (i, " ;; ".join(abl[-3:])\n'
    u'                                                 or "no absorption line (rc %s)" % ab.returncode))\n'
    u'            except Exception as exc:\n'
    u'                log("round %d absorption crashed: %r" % (i, exc))\n')

INSERTION = ANCHOR + DELTA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write into the live loop file (default: preview only)")
    a = ap.parse_args()
    if not os.path.isfile(TARGET):
        print("ABORT 找不到跑批文件：%s" % TARGET)
        return 3
    old = io.open(TARGET, "r", encoding="utf-8", newline="").read()
    n = old.count(ANCHOR)
    if n != 1:
        print("ABORT 锚点命中 %d 次，不是 1 次 ⇒ 不动（锚在 adopt-join 那条腿的收尾两行）" % n)
        return 4
    if ANCHOR in old and ANCHOR + u"            # ORD-0592" in old:
        print("ALREADY-MOUNTED｜跑批里已经有这条腿了，不重复插")
        return 0
    mounted = old.replace(ANCHOR, INSERTION, 1)
    # INSERTION = ANCHOR + DELTA, so the identity proof is: deleting only the DELTA gives the original
    # back.  (Proofing it against INSERTION instead would delete the anchor too and compare a shorter
    # string against the original -- that equation can never hold; it is what made this file abort first.)
    if mounted.count(DELTA) != 1 or mounted.replace(DELTA, "", 1) != old:
        print("ABORT 字节对拍不等：插掉的份与要加的份不一致 ⇒ 这版会吞掉别的行")
        return 5
    if mounted.count(ANCHOR) != 1:
        print("ABORT 插完之后锚行不在了（命中 %d 次）" % mounted.count(ANCHOR))
        return 5
    before_lines = old.count("\n")
    after_lines = mounted.count("\n")
    preview = TARGET + u".absorption_preview"
    io.open(preview, "w", encoding="utf-8", newline="").write(mounted)
    try:
        py_compile.compile(preview, doraise=True)
    except py_compile.PyCompileError as exc:
        print("ABORT 预览件编译不过：%s" % str(exc)[:300])
        return 6
    print("PREVIEW 可编译｜行数 %d 到 %d（+%d）｜锚行存活=%s｜字节等式=过" % (
        before_lines, after_lines, after_lines - before_lines, mounted.count(ANCHOR) == 1))
    print("PREVIEW 落在 %s" % os.path.basename(preview))
    if not a.apply:
        print("DRY｜未改动跑批本体。要挂上：python mount_absorption_leg_r1.py --apply")
        return 0
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = TARGET + u".bak_absorb_%s" % stamp
    shutil.copyfile(TARGET, bak)
    io.open(TARGET, "w", encoding="utf-8", newline="").write(mounted)
    try:
        py_compile.compile(TARGET, doraise=True)
    except py_compile.PyCompileError as exc:
        shutil.copyfile(bak, TARGET)
        print("ROLLBACK 编译不过，已从备份还原：%s" % str(exc)[:220])
        return 7
    print("MOUNTED｜备份 %s｜现件行数 %d｜这条腿要等跑批重启才带上：在跑的那一进程用的是内存里那份旧码，"
          u"改文件不会让它自己换血（重启由号令者定，我不碰那一枚 pid）" % (os.path.basename(bak), mounted.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
