# -*- coding: utf-8 -*-
u"""给 `_stack_staleness_check_r1.py` 补三处，让它认得巡检跑批这条腿。

为什么必须补：19:18 我把跑批挂进 COMPONMENTS，这把尺的 LEGS 里**没有它**（19:36 现读实测）。
一条不在尺里的腿 = 以后改它的代码尺一句都不会提，等于这条腿脱管
（同「单向致盲的尺也算仪器缺陷」）。

补三处，各有各的必要性：
  ① LEGS 加 `(patrol_loop, _patrol_loop_r1.py)` —— 否则不报陈旧。
  ② STOP_ENV 加 `PATROL_LOOP_STOP` —— 跑批的到点从那个 env 读。
  ③ STOP_DEFAULT 加 `1105` —— 不补的话 stop_epoch() 返回 None，
     尺就分不出「只是看着旧，不必现在动」与「实际到点已过，立刻重启」这两种裁决
     （那正是这把尺存在的主要理由）。

改完自证：真跑一遍尺，确认 patrol_loop 那行出现且判语合理（现读它是 19:17 起的、代码也是 19:17 改的）。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_stack_staleness_check_r1.py")

PATCHES = [
    (u'    (u"board", u"D:/moodle/agent_bus/board.py"),\n',
     u'    (u"board", u"D:/moodle/agent_bus/board.py"),\n'
     u'    # 巡检跑批 19:18 进 COMPONENTS；这把尺原先不认它（19:36 现读实测），\n'
     u'    # 不补 ⇒ 以后改它的代码尺不会报，等于这条腿脱管。\n'
     u'    (u"patrol_loop", u"_patrol_loop_r1.py"),\n'),
    (u'    u"verdict": u"NVR_AT",\n}',
     u'    u"verdict": u"NVR_AT",\n'
     u'    u"patrol_loop": u"PATROL_LOOP_STOP",\n}'),
    (u'    u"verdict": u"23:00:20",\n}',
     u'    u"verdict": u"23:00:20",\n'
     u'    # 跑批默认到 1105（守到 11:00 之后五分钟，留写快照）\n'
     u'    u"patrol_loop": u"1105",\n}'),
]


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"patrol_loop" in t:
        print(u"已在尺里 ⇒ 不重复补")
        return 0
    new = t
    miss = []
    for old, rep in PATCHES:
        c = new.count(old)
        if c != 1:
            miss.append((old.strip()[:40], c))
            continue
        new = new.replace(old, rep, 1)
    if miss:
        print(u"REFUSE：这些锚命中数不是 1，未写盘：%s" % miss)
        return 1
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_patrolloop_1936"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 3 处（LEGS／STOP_ENV／STOP_DEFAULT），备份 %s" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())