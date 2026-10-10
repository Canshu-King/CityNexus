# -*- coding: utf-8 -*-
u"""巡逻加第⑪格：号令者名下「已送未拆」拆成 可一批清掉／真要动脑 两堆。

为什么值得进巡逻（10-06 04:2x 实测）：那把尺 `_cmdr_backlog_split_r1.py` 跑一遍 **1423 毫秒**，
而它量的维度第⑧格没有——⑧ 只说"压着 113 条"，⑪ 说"其中 60 条的交付物**已经在账本里**"。
这一句直接决定动作：前者只能等，后者可以一次点一堆。不装进巡逻，这格就还是"我手算过一次"的一次性件。

形制：用 subprocess 调那把尺自己的输出取数，不在巡逻里复制第二份判据
（[[feedback-faithful-pattern-replica]]「调用形制必须与被调方一致」＋「判据只该有一份」）。
取不到就写不可得，绝不当"没有积压"。

跑法：python _patrol_backlog_cell_patch_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_bb_patrol_once_r1.py")

OLD = u'''    print(u"结论：%s" % (u"有扇该敲" if knock else
'''

NEW = u'''    # ⑪：号令者名下"已送未拆"的两堆拆分。⑧ 只给"压着多少条"，这一格给"其中多少条不用再读全文"，
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

''' + OLD


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"⑪ 验收口拆分" in t:
        print(u"已装过第⑪格，不重复写")
        return 0
    n = t.count(OLD)
    if n != 1:
        print(u"REFUSE：结论锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    new = t.replace(OLD, NEW)
    ast.parse(new)
    if u"--check" in sys.argv:
        print(u"--check：锚逐字命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print(u"已写：巡逻新增第⑪格（调 _cmdr_backlog_split_r1 自己那把尺）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
