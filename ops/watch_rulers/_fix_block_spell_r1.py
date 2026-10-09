# -*- coding: utf-8 -*-
u"""把块里 `NO_CHAIM_FOUND` 改成 `NO_CLAIM_FOUND`（21:23 写错了尺的原话）。

为什么值得单独一个脚本：块里**引用尺的原话**时，拼错那个词是最坏的一种错——
下一班按 `NO_CHAIM_FOUND` 去搜那把尺的源码会**搜不到**，于是以为尺里没这个词。
纪律：引用外部判据的原话，写完必须回读比对（这里 `t.count(原样) == 0` 才算通过）。

安全：只改这一个词，不动块里任何别的东西；改前备份。
"""
import io
import os
import sys

BLOCK = r"D:\moodle\_qoder_ledger_inbox\42d1a6fa_2121.md"
BAD = u"NO_CHAIM_FOUND"
GOOD = u"NO_CLAIM_FOUND"

# 尺源码里的真形必须现读，不许凭记忆
RULER = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\claim_coordinate_check_r7.py"


def main():
    ruler = io.open(RULER, encoding="utf-8", errors="replace").read()
    if GOOD not in ruler:
        print(u"REFUSE：尺源码里没有 %s ⇒ 那是我的记忆错了，不许往块里写这个词" % GOOD)
        return 1
    if BAD in ruler:
        print(u"REFUSE：尺源码里竟有错拼 %s ⇒ 先弄清楚" % BAD)
        return 1
    t = io.open(BLOCK, encoding="utf-8", newline="").read()
    if BAD not in t:
        print(u"块里没有错拼 ⇒ 不用改")
        return 0
    n = t.count(BAD)
    new = t.replace(BAD, GOOD)
    bak = BLOCK + u".bak_spell_2123"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(BLOCK, "w", encoding="utf-8", newline="").write(new)
    back = io.open(BLOCK, encoding="utf-8", errors="replace").read()
    ok = (BAD not in back) and (GOOD in back)
    print(u"已改 %d 处；回读：错拼 %d（应为 0）、正拼出现 %s"
          % (n, back.count(BAD), GOOD in back))
    if not ok:
        print(u"FAIL：回读不对")
        return 1
    # 再取一次尺的退出码表，把退出码四的原话逐字贴出来给下一班对
    i = ruler.find(u"NO_CLAIM_FOUND (not a pass)")
    if i > 0:
        print(u"尺自己的退出码表原文：%s" % ruler[i - 46:i + 40].replace(chr(10), u" "))
    return 0


if __name__ == "__main__":
    sys.exit(main())