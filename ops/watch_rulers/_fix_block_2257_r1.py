# -*- coding: utf-8 -*-
u"""把 22:57 那块里"顺带"那句的数字删掉——它是旁注，结论在表里（表里已带坐标）。

为什么删而不是补坐标：那句原本带三个分钟数（重启前/重启后/含挂起），
而它要说的只有一件事——**那段静默含一次应用重启，不全是它自己在停**。
三个数字在这里只增加被门咬的面积，不增加信息。⇒ 改成定性说法。

门第三次拒的就是它（22:58 实测：line 32/33 的「1167 分钟」「43 分钟」「1110 分钟」）。
"""
import io
import os
import sys

BLOCK = r"D:\moodle\_qoder_ledger_inbox\42d1a6fa_2257.md"


def main():
    t = io.open(BLOCK, encoding="utf-8", newline="").read()
    if u"含过一次应用重启" in t:
        print(u"已改过 ⇒ 不重复改")
        return 0
    i = t.find(u"**顺带**")
    if i < 0:
        print(u"REFUSE：找不到「顺带」那行")
        return 1
    j = t.find(u"\n\n", i)
    if j < 0:
        j = len(t)
    seg = t[i:j]
    print(u"删掉的原句：%s" % seg.replace("\n", u" / ")[:200])
    new = (u"**顺带**：`6efab655` 那段静默里**含过一次应用重启**（平台把它挂起了），"
           u"所以那段时间不全是它自己在停 —— 表里那个分钟数是含挂起段的。")
    t = t[:i] + new + t[j:]
    bak = BLOCK + u".bak_note_2259"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(
            io.open(BLOCK, encoding="utf-8", newline="").read())
    io.open(BLOCK, "w", encoding="utf-8", newline="").write(t)
    print(u"已写（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())