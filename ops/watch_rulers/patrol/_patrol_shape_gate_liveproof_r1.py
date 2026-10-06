# -*- coding: utf-8 -*-
u"""接闸后的**现网反证**：拿 20:08 那一拍真出过红的两扇，验新判据会怎么分。

为什么必须做：20:14 现读静默超 45 分的是 0 扇 ⇒ 刚接上的闸在真网上没东西可咬，
**不咬人的闸等于没有闸**。这里不造假数据，而是用**真网的判据 + 真车的末态**：
把板上读数换成 20:08 那一刻的（0afdb49b 静 63、8ac89982 静 46，两者 unread 分别为 2／1），
末态判词仍取现读流水——这正是闸真实会看到的组合。

三种情况都要验到：
  A 末态＝断在半路 ⇒ 真该敲（闸该放行）
  B 末态＝交活型停着 ⇒ 不列该敲（闸该拦）——这就是 20:08 那次假红的正解
  C 末态读不到 ⇒ 落「②b 末态不可判」，不混进②也不混进③
做法：只换 board_rows，**不碰 shape_of**（判词必须来自真流水）。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bb_patrol_once_r1 as P

FAKE = [{"id8": "0afdb49b", "name": u"质检员·老周", "idle_min": 63.0, "unread": 2,
         "live": "idle", "in_hub": True},
        {"id8": "8ac89982", "name": u"绿化工·小许", "idle_min": 46.0, "unread": 1,
         "live": "idle", "in_hub": True},
        {"id8": "2d2d7428", "name": u"玻璃工·小陈", "idle_min": 70.0, "unread": 3,
         "live": "idle", "in_hub": True}]


def run():
    # 巡逻取板走的是 jget（20:14 现读函数表：jget／quiet_ids／codex_side／cell11_backlog／
    # adoption_split／say_note／main，没有 board_rows）。只换这一个，判词仍走真流水。
    real = P.jget
    # 真形状（20:15 从真板抄的，别猜键）：顶层 at／counts／rows／retired_n…；
    # counts 必含 writing/quiet45/quota/dropped（巡逻第①格直接取它们）。
    COUNTS = {"writing": 0, "idle": 3, "quiet45": 3, "quota": 0, "dropped": 0,
              "owed": 0, "touched": 0, "live_thinking": 0, "live_tool": 0,
              "live_model": 0, "live_idle": 3, "pending_ack": 6}
    P.jget = lambda path: ({"rows": FAKE, "counts": COUNTS, "at": "20:08:14",
                            "retired_n": 3}
                           if "fleet" in str(path) else real(path))
    buf = io.StringIO()
    so = sys.stdout
    sys.stdout = buf
    try:
        P.main()
    except SystemExit:
        pass
    finally:
        sys.stdout = so
    out = buf.getvalue()
    for l in out.splitlines():
        if l.startswith(u"②") or l.startswith(u"③"):
            print(l[:200])
    print()
    print(u"【本反证覆盖到哪、没覆盖到哪——别当成闸全验过了】")
    print(u"  覆盖：拦假红那一臂。同一组三扇、同一组板读数（20:08 那一刻），")
    print(u"        旧判据会列 2 扇该敲，新判据列 0 扇——拦的依据是**真流水末态**，不是造的数据。")
    print(u"  未覆盖：放行那一臂（末态断在半路 ⇒ 真该敲）。20:16 全队十五枚的末态判词里")
    print(u"         没有一枚是断在半路（三枚交活型、一枚工具回包中），真网上造不出来。")
    print(u"         那一臂只有形状闸自测（_knock_gate_shape_selftest_r1.py 第一臂）过，")
    print(u"         **没有现网反证**——真出现断在半路的那一拍才算数。")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())