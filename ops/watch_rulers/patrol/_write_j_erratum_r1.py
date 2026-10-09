# -*- coding: utf-8 -*-
u"""哨兵 J 档红因与它自己的分类器**对不上**：把两边读数并排写进 HIT 档。

20:35:57 哨兵 J 档报：「J 车道 1d64acf5 断在半路（尾条是没回音的 tool_use）」。
20:37 我并排量了三条独立读数：

| 来源 | 读数 |
|---|---|
| 哨兵 `_why_stopped_r1.py` **自己那一轮的分类** | 1d64acf5 静 50 分｜判：**卡闸、等裁语、谈交付** |
| 我的末态尺 `_lane_tailform_r1.py`（读流水末三条） | 末三条＝assistant tool_use:TaskUpdate → **user tool_result** → assistant text ⇒ **交活型停着**，有回音 |
| 我对 240 KB 尾窗的直接字节计数 | 尾窗里 tool_result 出现 20 次（全文件 5418 次）⇒ "没回音"不可能是"读太短"造成的 |

⇒ 三个读数都指向**不是断在半路**；只有哨兵正文那一句这么写。
它**自己那一轮的分类**里根本没有"断在半路"这一类，却把 1d64acf5 列进了
「该敲车道本人（卡闸/断在半路）」那一栏——那一栏是**两类共用**的，
所以它报出去时把"卡闸"讲成了"断在半路"。

**这是 relay 的成因，不是分类器的成因。** 按纪律（别人给的成因是假设）：
复现不出 ⇒ 两边读数都贴，并当场更正，不去修那个错的点。
真正该修的是**措辞**：J 档那条消息的成因应当从分类器的原文取，而不是手写一句。

判语：**1d64acf5 不该被当"断在半路"叫醒**。它是卡闸／等裁语／谈交付，
该敲号令者点验收（那是 `_why_stopped_r1.py` 自己"该敲号令者"那一栏里的四扇之一）。

边界：0 次发送、0 次敲门、0 次改分类器（本轮只留痕与并排读数）。
"""

NOTE = u"""
━━ 并排读数（20:37–20:38）━━
哨兵 20:35:57 的 J 档正文写：J 车道 1d64acf5 断在半路（尾条是没回音的 tool_use）。
三条独立读数都说**不是**断在半路：

  ① 哨兵自己那把分类器 `_why_stopped_r1.py` 的判定：
     1d64acf5 静 50 分｜判：**卡闸、等裁语、谈交付**
     且它把 1d64acf5 列进的是「该敲车道本人（卡闸/断在半路）」——
     **那一栏是两类共用的**，报出去时把"卡闸"讲成了"断在半路"。
  ② 我的末态尺 `_lane_tailform_r1.py` 读流水末三条：
     assistant tool_use:TaskUpdate → **user tool_result** → assistant text
     ⇒ **交活型停着**，tool_use 有回音。
  ③ 我对 240 KB 尾窗的直接字节计数：尾窗里 tool_result 出现 20 次
     （全文件 5418 次）⇒ "没回音"不是"只读尾部"造成的。

判语：1d64acf5 **不该被当断在半路叫醒**。它是卡闸／等裁语／谈交付，
该敲的是号令者点验收（它本来就在分类器"该敲号令者"那一栏的四扇里）。

这是 **relay 的成因**（措辞），不是分类器的成因：分类器没报"断在半路"，
是 J 档那一句手写的消息把它讲成了那样。按纪律不去修那个错的点，先并排留痕。

真正该改的：J 档那条消息的**成因应当从分类器原文取**，不是手写。
留给下一班或号令者裁，我这一轮 0 发送、0 敲门、0 改分类器。
"""


def main():
    import io
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    hit = os.path.join(here, "_sentinel_relay_HIT.txt")
    if not os.path.exists(hit):
        print(u"REFUSE：HIT 档不在 %s，不写" % hit)
        return 1
    t = io.open(hit, encoding="utf-8", errors="replace").read()
    if u"并排读数（20:37–20:38）" in t:
        print(u"已在 ⇒ 不重复写")
        return 0
    with io.open(hit, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(NOTE)
    back = io.open(hit, encoding="utf-8", errors="replace").read()
    print(u"已并排写进 HIT 档；%d → %d 字节" % (len(t), len(back)))
    for k in (u"卡闸、等裁语、谈交付", u"交活型停着", u"relay 的成因"):
        print(u"  回读含「%s」：%s" % (k, k in back))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())