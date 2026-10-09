# -*- coding: utf-8 -*-
u"""把第⑩格的分类从 main 里抽成一个函数，好在自测里喂合成输入。

为什么要抽：这格现在分四态（在发／发过静默／两腿全无／只收不发），
而"只收不发"这一态是我今天现读才从"从没发过话"里拆出来的——没有合成反证，
下一班改词表时没人知道哪一态会被并掉（10-02 那次收窄一档悄悄删掉一类覆盖的前例）。
抽取只动这一格，不碰别的判据。

跑法：python _patrol_adoption_fn_extract_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_bb_patrol_once_r1.py")

FN = u'''
def adoption_split(rows, spoken, took, nowt, wmin):
    u"""把在册的车道按 BB 机两条腿分四态（第⑩格用的就是这一份，别复制第二把尺）。

      A 在发        ：wmin 分钟内以 from 出现过
      B 发过但静默  ：出现过，但在 wmin 之外
      C 两腿全无    ：from 从没出现，且名下没有一条被取走过 ⇒ 真没接上，缺整段接入件
      C2 只收不发   ：from 从没出现，但名下有被取走的 ⇒ 收信腿是通的，缺的只有 send
    判据只吃现读的 from/delivered_at，不吃名册的 verified：那枚旗会把后者读成"已接上"。
    """
    A, B, C, C2 = [], [], [], []
    for r in rows:
        hid = u"qoder:" + r["id8"]
        t = spoken.get(hid, 0)
        if not t:
            (C2 if took.get(hid) else C).append(r["id8"])
        elif nowt - t <= wmin * 60:
            A.append(r["id8"])
        else:
            B.append((r["id8"], int((nowt - t) / 60)))
    return A, B, C, C2


'''

OLD = u'''        A, B, C, C2 = [], [], [], []
        for r in rows:
            hid = u"qoder:" + r["id8"]
            t = spoken.get(hid, 0)
            if not t:
                (C2 if took.get(hid) else C).append(r["id8"])
            elif nowt - t <= wmin * 60:
                A.append(r["id8"])
            else:
                B.append((r["id8"], int((nowt - t) / 60)))
'''

NEW = u'''        A, B, C, C2 = adoption_split(rows, spoken, took, nowt, wmin)   # 四态见这个函数
'''


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"def adoption_split" in t:
        print(u"已抽过（文件里有 adoption_split），这次不重复写")
        return 0
    n = t.count(OLD)
    if n != 1:
        print(u"REFUSE：分类那段锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    anchor = u"def say_note(x):"
    if t.count(anchor) != 1:
        print(u"REFUSE：插入点 %r 不唯一（%d 次）" % (anchor, t.count(anchor)))
        return 1
    new = t.replace(OLD, NEW).replace(anchor, FN.strip() + u"\n\n\n" + anchor)
    ast.parse(new)
    if u"--check" in sys.argv:
        print(u"--check：两处锚各命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print(u"已写：分类抽成 adoption_split()（第⑩格调它）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
