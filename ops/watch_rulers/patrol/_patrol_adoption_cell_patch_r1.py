# -*- coding: utf-8 -*-
u"""给巡逻加一格「推广（本机车道侧）」：A 一直在用／B 接过了但静默／C 整本账没发过话。

为什么要它：10-06 03:3x 我手算了一次名册（_adoption_census_1006_0330.txt），
那是一次性的；目标里"给其他会话推广"是要持续盯的，一格不进巡逻就等于下班从零开始。
第⑦格只管 Codex 那侧，本机车道这一侧原先没有复算口。

判据（与名册同一份算法，不复制第二把尺的说法）：
  分母＝板上在册的行（fleet rows，非我自己列名单）；
  A＝近 ADM_WINDOW_MIN 分钟在 bus.jsonl 里发过话；B＝发过但窗口外；C＝from 从没出现。
边界：只读取数，0 次写、0 次发帖、0 次邀请。取不到就写不可得，绝不当「都接上了」。

跑法：python _patrol_adoption_cell_patch_r1.py --check   # 只看锚
      python _patrol_adoption_cell_patch_r1.py
"""
import ast
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_bb_patrol_once_r1.py")

OLD = u'''    print(u"结论：%s" % (u"有扇该敲" if knock else
                        (u"没人该敲；缺单的那 %d 扇等包工头点" % len(waiting) if waiting else u"全队都在动")))
'''

NEW = u'''    # ⑩：推广（本机车道这一侧）。Codex 那侧是第⑦格，这两格合起来才是"给其他会话推广"的覆盖；
    # 判据与 agent_bus/_adoption_census_1006_0330.txt 同形：分母取板上在册的行，
    # 分子只看 bus.jsonl 里 from 自己出现的时刻——"我发过几次邀请"不作数（10-03 定过这条）。
    try:
        wmin = float(os.environ.get("ADM_WINDOW_MIN", "360"))
        nowt = time.time()
        spoken = {}
        led = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                           u"agent_bus", u"bus.jsonl")
        if os.path.isfile(led):
            for line in io.open(led, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    mm = json.loads(line)
                except ValueError:
                    continue
                f = str(mm.get("from") or u"")
                t = float(mm.get("ts") or 0)
                if t > spoken.get(f, 0):
                    spoken[f] = t
        A, B, C = [], [], []
        for r in rows:
            hid = u"qoder:" + r["id8"]
            t = spoken.get(hid, 0)
            if not t:
                C.append(r["id8"])
            elif nowt - t <= wmin * 60:
                A.append(r["id8"])
            else:
                B.append((r["id8"], int((nowt - t) / 60)))
        if not os.path.isfile(led):
            print(u"⑩ 推广：BB 机账读不到 ⇒ 这一格不可得，不许当'都接上了'")
        else:
            print(u"⑩ 推广（分母在册 %d 扇｜窗口 %.0f 分）｜在用 %d｜接过但静默 %d｜从没发过话 %d"
                  % (len(rows), wmin, len(A), len(B), len(C)))
            print(u"   静默最久的三扇：%s｜从没发过话：%s"
                  % (u"、".join(u"%s(%d 分)" % x for x in sorted(B, key=lambda y: -y[1])[:3]) or u"无",
                     u"、".join(C) or u"无"))
            if C:
                print(u"   接入件（板子现取，别手打）：GET %s/api/invite?agent=qoder:<id8>" % BOARD)
    except Exception as e:
        print(u"⑩ 推广：取不到（%s）⇒ 不当零" % type(e).__name__)

''' + OLD


def main():
    t = io.open(T, encoding="utf-8").read()
    n = t.count(OLD)
    if n != 1:
        print(u"REFUSE：结论那枚锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    new = t.replace(OLD, NEW)
    ast.parse(new)
    if u"--check" in __import__("sys").argv:
        print(u"--check：锚逐字命中 1 次，替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print(u"已写 _bb_patrol_once_r1.py（新增第⑩格）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
