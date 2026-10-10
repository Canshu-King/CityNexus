# -*- coding: utf-8 -*-
u"""交接稿：① 去掉清单里 11 处「（不在这个目录）」误注；② 补今晚新增的四件。

误注是什么：清单里那 11 条写「patrol/xxx（**不在这个目录**）」，其实它们**就在 patrol/ 下**。
那是我写清单时按"记忆里的路径"写、没回读文件系统的产物——正是交接稿自己第 五·四十八 节记的
「负结论必须先列实物」同一形制。只删这个括号，不动路径本身（路径逐枚验过）。

新四件（19:1x 落的）：
  _patrol_loop_r1.py                 巡检跑批本体（每 12 分自己跑一次并存档，自停闸到 11:05）
  _start_patrol_loop_r1.py           真 detached 起法（DETACHED_PROCESS 单独给）
  _patch_loop_needseyes_r1.py / _patch_judge_numcmp_r2.py  跑批加「待看档」的两步补丁
  _patrol_loop_needseyes_selftest_r1.py  待看判据六臂自测（真档绿/四种红/去重）
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
PATROL = os.path.join(HERE, "patrol")

BOGUS = u"（**不在这个目录**）"

NEW_ITEMS = [
    u"- `patrol/_patrol_loop_r1.py` → 新增（巡检跑批：每 N 分钟自己跑一次巡逻并存档；"
    u"单实例锁＋档名带 pid＋自停闸 past_stop()；每拍还把结论判红写 `rounds/_needs_eyes.log`）",
    u"- `patrol/_start_patrol_loop_r1.py` → 新增（真 detached 起法；`DETACHED_PROCESS` **单独给**，"
    u"与 `CREATE_NEW_PROCESS_GROUP` 并用会 WinError 87）",
    u"- `patrol/_patch_loop_needseyes_r1.py` → 新增（跑批主循环接上判红＋写待看档；用行号定位，绕开锚匹配）",
    u"- `patrol/_patch_judge_numcmp_r2.py` → 新增（judge() 改抽数字比较：圈号按序号推码位，不靠空格）",
    u"- `patrol/_patrol_loop_needseyes_selftest_r1.py` → 新增（待看判据六臂自测：真档绿｜结论变红｜"
    u"该敲非零红｜栈塌红｜空文本红｜去重连绿不重写）",
]


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    before = t.count(BOGUS)
    if before != 11:
        print(u"REFUSE：误注 %d 处，预期 11 ⇒ 不动" % before)
        return 1
    t = t.replace(BOGUS, u"")

    # 补新四件：插在清单最后一条之后（以 _patch_keepalive_blindretry 那行为锚）
    anchor = u"- `patrol/_patch_keepalive_blindretry_r1.py`"
    i = t.find(anchor)
    if i < 0:
        print(u"REFUSE：找不到清单末条锚")
        return 1
    j = t.find(u"\n", i)
    add = u"\n" + u"\n".join(NEW_ITEMS)
    if t.count(u"_patrol_loop_needseyes_selftest_r1.py"):
        print(u"已补过 ⇒ 不重复补")
        return 0
    t = t[:j] + add + t[j:]

    # 逐枚验路径真在
    miss = []
    for m in re.finditer(r"^- `(patrol/[^`]+)`", t, re.M):
        if not os.path.exists(os.path.join(HERE, m.group(1))):
            miss.append(m.group(1))
    if miss:
        print(u"REFUSE：清单里这些路径不存在，未写盘：%s" % miss)
        return 1

    io.open(HAND, "w", encoding="utf-8", newline="").write(t)
    print(u"已写：去误注 %d 处；补新条目 %d 条；清单里路径逐枚存在（%d 条全过）"
          % (before, len(NEW_ITEMS), len(re.findall(r"^- `(patrol/[^`]+)`", t, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())