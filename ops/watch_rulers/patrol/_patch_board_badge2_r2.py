# -*- coding: utf-8 -*-
u"""改板子另外两处「N 分没出字」——**这两处才是主人天天看的那两处**。

第一版（`_patch_board_badge_wording_r1.py`）只改了 `badge()` 里那两句，
可主人看到的顶部计数器标签（`25分没出字` / `45分没出字`）与表格里那枚状态串
（`Math.round(r.idle_min)+' 分没出字'`）**都还在说旧话**。
我第一版的自检只查了 `badge()` 那一处 ⇒ 差点当成改完了（这正是「改了没验全」的老坑）。

**为什么这三处都要改**（22:5x 主人一句"除了包工头都在摸鱼"量出来的）：
数据层算的是 `self_idle`＝**他多久自己产出过**（不是文件 mtime，外壳记账节点不算），
这个数**是对的**；错的是显示话。「50 分没出字」把"50 分钟前刚交完活、此刻在等下一件"
读成"50 分钟什么也没产出"。人看话不看数 ⇒ 整块板读成全停摆。

改法（只换措辞，一个数不碰）：
  · 顶部两个计数器：`25分没出字` → `25分前在动`、`45分没出字` → `45分前在动`
  · 表格状态串：`(N)+' 分没出字'` → `(N)+' 分钟前在动'`

改后回读**三处全查**（`分没出字` 应为 0），再跑 `board_check_r1.py` 看结构锁。
"""
import io
import os
import sys

BOARD = r"D:\moodle\agent_bus\board.py"

PAIRS = [
    (u"<em>25分没出字</em>", u"<em>25分前在动</em>"),
    (u"<em>45分没出字</em>", u"<em>45分前在动</em>"),
    (u"(Math.round(r.idle_min)+' 分没出字')",
     u"(Math.round(r.idle_min)+' 分钟前在动')"),
]


def main():
    t = io.open(BOARD, encoding="utf-8", newline="").read()
    n0 = t.count(u"分没出字")
    print(u"改前「分没出字」出现 %d 次" % n0)
    if n0 == 0:
        print(u"已改过 ⇒ 不重复改")
        return 0
    new = t
    for old, rep in PAIRS:
        c = new.count(old)
        print(u"  锚 %d 次：%s" % (c, old[:40]))
        if c != 1:
            print(u"REFUSE：锚命中数不对，未写盘")
            return 1
        new = new.replace(old, rep, 1)
    bak = BOARD + u".bak_badgewording2_2300"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(BOARD, "w", encoding="utf-8", newline="").write(new)
    back = io.open(BOARD, encoding="utf-8", errors="replace").read()
    left = back.count(u"分没出字")
    print(u"已写（备份 %s）；改后「分没出字」还有 %d 处" % (os.path.basename(bak), left))
    if left:
        for k, l in enumerate(back.splitlines(), 1):
            if u"分没出字" in l:
                print(u"   残留 行%d: %s" % (k, l.strip()[:120]))
        return 1
    for k in (u"25分前在动", u"45分前在动", u"分钟前在动"):
        print(u"  新话含「%s」：%s" % (k, k in back))
    return 0


if __name__ == "__main__":
    sys.exit(main())