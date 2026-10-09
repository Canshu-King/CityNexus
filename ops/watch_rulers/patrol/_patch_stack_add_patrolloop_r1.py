# -*- coding: utf-8 -*-
u"""把巡检跑批挂进值守栈（`_watch_stack_r1.py` 的 COMPONENTS 加一条）。

为什么必须挂进去：19:14–19:16 实测——跑批两枚（4676、11300）都是
「跑完第一拍就被回收」，stdout 空、无异常栈，tasklist 三连查都读不到。
和栈里那几支同形制（DETACHED_PROCESS）却活不过一拍 ⇒ 它是被本工具进程树的清理带走的。
栈腿是 `autumn_supervise` 那类**自己就是长跑循环**、由工具起手之后不再被管的脚本；
跑批同样是循环，但它是**我**用工具起的，所以挂在工具的清理范围里。
挂进栈 ⇒ 由 `_watch_stack_r1.py` 起（那枚是整套栈的入口，清理归属不同），
并且机器重启后 `--check`/`起复` 就能把它带回来。

跑批自带单实例锁（claim()），所以「栈去重 + 跑批锁」两层都拒重复起。
安全：只加一条 COMPONENTS；不改任何腿的起法；不碰他人进程。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_watch_stack_r1.py")

NEW = u'''    # 巡检跑批也进覆盖：19:14-19:16 实测它由工具手起时只活一拍（stdout 空、无异常、tasklist 三查皆无），
    # 与栈腿同形制却被回收 ⇒ 它落在工具进程树的清理范围里。挂进栈就由栈来起、也随栈重启拉回。
    # 它自带单实例锁（`_patrol_loop_r1.py` 的 claim()），叠上栈的去重 ⇒ 不会起出第二枚。
    # **四元**：不能带第五项——栈把 entry[4] 当档点塞 `NVR_AT=` argv，跑批不认那个变量。
    # 间隔走 env（`PATROL_LOOP_MIN`，栈的 start() 也会把 os.environ 传下去）。
    ("patrol_loop", "_patrol_loop_r1.py", "_patrol_loop.log",
     u"每 %s 分钟自己跑一次巡逻并存档；到 %s 自停（比守到 11:00 晚五分钟留写快照）"
     % (os.environ.get("PATROL_LOOP_MIN", "12"), os.environ.get("PATROL_LOOP_STOP", "1105"))),
'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"patrol_loop" in t:
        print(u"已在栈里 ⇒ 不重复加")
        return 0
    if u"def start(" not in t:
        print(u"REFUSE：找不到 start()")
        return 1
    i = t.index(u"def start(")
    # 找到 COMPONENTS 列表的收尾 "]"：从 COMPONENTS 起点往后找第一个顶格 "]"
    c = t.index(u"COMPONENTS = [")
    end = t.index(u"\n]\n", c) + 1          # 指向 "]" 那一行
    new = t[:end] + u"\n" + NEW.rstrip(u"\n") + t[end:]
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    # 构表自证：真 import 一遍，拿名字与长度
    bak = SRC + u".bak_patrolloop_1917"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    import importlib
    sys.path.insert(0, HERE)
    m = importlib.import_module(u"_watch_stack_r1")
    importlib.reload(m)
    names = [e[0] for e in m.COMPONENTS]
    print(u"已加一条，栈现有 %d 腿：%s" % (len(names), u"、".join(names)))
    pl = [e for e in m.COMPONENTS if e[0] == u"patrol_loop"]
    if not pl:
        print(u"FAIL：加进去的名字没在 COMPONENTS 里")
        return 1
    e = pl[0]
    print(u"新腿条目：len=%d name=%s script=%s log=%s" % (len(e), e[0], e[1], e[2]))
    if len(e) != 4:
        print(u"FAIL：条元数 %d，栈会把 entry[4] 当档点" % len(e))
        return 1
    if not os.path.exists(os.path.join(HERE, e[1])):
        print(u"FAIL：脚本不在 %s" % e[1])
        return 1
    print(u"脚本存在：%s" % os.path.join(HERE, e[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())