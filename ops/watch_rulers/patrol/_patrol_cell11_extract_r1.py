# -*- coding: utf-8 -*-
u"""把第⑪格那段抽成函数 cell11_backlog(here)，好让自测喂假尺跑**真代码**。

为什么再动一次：10-03 那条规矩是"每加一格要故意造一次该报的输入，验清单会 +1"，
而我第一版自测只能在临时目录里"复刻判据的两半"（rc／关键词在场＋三行前缀），
没跑到巡逻里那四十行 print——那叫测了我自己写的副本，不叫覆盖。
抽成函数之后，自测 import 巡逻、直接调这个函数，跑的是一模一样的代码。

只动第⑪格，不碰别的格。跑法：
  python _patrol_cell11_extract_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_bb_patrol_once_r1.py")

FN = u'''def cell11_backlog(here, runner=subprocess.run, emit=None):
    u"""第⑪格：把号令者名下「已送未拆」拆成两堆并打印三行。

    尺是现成那把 `_cmdr_backlog_split_r1.py`（实测跑 1.4 秒），这里只搬运它的输出，
    判据不在巡逻里复制第二份。runner/emit 是给自测留的注入位：
    喂一枚假尺（rc=1 或没有「甲类」）进去，就能验"坏的那一侧写成不可得、而不是没积压"。
    （emit 默认用内置 print；别写 globals().get("print")——那不是全局名，会取到 None。）
    """
    if emit is None:
        def emit(x):
            sys.stdout.write(x + chr(10))
    ruler = os.path.join(here, u"_cmdr_backlog_split_r1.py")
    try:
        sp = runner([exe or sys.executable, ruler], capture_output=True, timeout=120, cwd=here,
                    env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        o = (sp.stdout or b"").decode("utf-8", "replace")
        if sp.returncode != 0 or u"甲类" not in o:
            emit(u"⑪ 验收口拆分：尺没答（rc=%d｜输出 %d 字符）⇒ 不可得，不许当'没积压'"
                 % (sp.returncode, len(o)))
        else:
            l1 = next((l for l in o.splitlines() if l.startswith(u"收件人")), u"")
            l2 = next((l for l in o.splitlines() if l.startswith(u"甲类")), u"")
            l3 = next((l for l in o.splitlines() if l.startswith(u"乙类")), u"")
            emit(u"⑪ %s" % l1[:110])
            emit(u"   %s" % l2[:110])
            emit(u"   %s" % l3[:110])
    except Exception as e:
        emit(u"⑪ 验收口拆分：取不到（%s）⇒ 不当零" % type(e).__name__)


'''

OLD = u'''    # ⑪：号令者名下"已送未拆"的两堆拆分。⑧ 只给"压着多少条"，这一格给"其中多少条不用再读全文"，
    # 因为那决定动作（等 vs 一次点一堆）。尺是现成那一把，跑 1.4 秒，判据不在这里复制第二份。
    try:
        sp = subprocess.run([sys.executable, os.path.join(HERE, u"_cmdr_backlog_split_r1.py")],
                            capture_output=True, timeout=120, cwd=HERE,
                            env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        o = (sp.stdout or b"").decode("utf-8", "replace")
        if sp.returncode != 0 or u"甲类" not in o:
            print(u"⑪ 验收口拆分：尺没答（rc=%d｜输出 %d 字符）⇒ 不可得，不许当'没积压'"
                  % (sp.returncode, len(o)))
        else:
            l1 = next((l for l in o.splitlines() if l.startswith(u"收件人")), u"")
            l2 = next((l for l in o.splitlines() if l.startswith(u"甲类")), u"")
            l3 = next((l for l in o.splitlines() if l.startswith(u"乙类")), u"")
            print(u"⑪ %s" % l1[:110])
            print(u"   %s" % l2[:110])
            print(u"   %s" % l3[:110])
    except Exception as e:
        print(u"⑪ 验收口拆分：取不到（%s）⇒ 不当零" % type(e).__name__)

'''

NEW = u'''    cell11_backlog(HERE)          # ⑪ 验收口两堆（函数在这份文件里，判据只有这一份）

'''
ANCHOR = u"def adoption_split(rows, spoken, took, nowt, wmin):"


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"def cell11_backlog" in t:
        print(u"已抽过（文件里有 cell11_backlog），不重复写")
        return 0
    n = t.count(OLD)
    m = t.count(ANCHOR)
    if n != 1 or m != 1:
        print(u"REFUSE：第⑪格那段命中 %d 次、插入点命中 %d 次，都要 1 次 ⇒ 未写盘" % (n, m))
        return 1
    new = t.replace(OLD, NEW).replace(ANCHOR, FN + ANCHOR)
    ast.parse(new)
    if u"--check" in sys.argv:
        print(u"--check：两处锚各命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print(u"已写：第⑪格抽成 cell11_backlog()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
