# -*- coding: utf-8 -*-
u"""交接稿补一节：五·五十四——Codex 那个"对不上"的窗，名字其实抽得出来。

为什么必须写：第⑦格从 10-05 起就写「活跃 thread 与名册没有字段能互指 ⇒ 不猜，要人看一眼」。
那句话**当时是对的**（库里真没有标题列），但它把「查不到」与「没查」混成了一件事，
于是 20:23 之前谁都没去翻 `thread_items` 的正文。窗名一抽出来，推广那最后一米就从
"没法办"变成"只差一个点头"。

另附：缺口判据为什么不能按数差（数量对上≠同一扇），这条已经造成过一次实打实的假零。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC = u"""## 五·五十四、Codex 那扇窗的名字抽得出来：**「对不上」与「没查」长得一样**

第⑦格从 10-05 起写的是「活跃 thread 与名册没有字段能互指 ⇒ 不猜，要人看一眼窗口」。
那句话**当时为真**——`~/.codex/thread_history_1.sqlite` 里确实**没有标题列**，
表只有 `thread_turns`／`thread_items`／`thread_history_projection_state`／`thread_realtime_items`。
但"没有标题列"不等于"没有身份"，20:23 翻 `thread_items` 的正文就翻出来了：

- 那扇近 90 分活跃的 thread（`01a10cd0-05e8…`）**首条 userMessage 只是 `continue`**——
  只取第一条什么也拿不到（我第一版就栽在这儿，打出"证据句 continue"）。
- 身份包在**上一次 `create_thread` 的 functionCallOutput** 里，那是父窗写给子窗的委派书，
  里面有 `<source_thread_id>01a0c796-93d8-7621-9157-161a973cab50</source_thread_id>`
  与一句 **「You are CityNexus Codex Window R.」**
- ⇒ 窗名 ＝ **CityNexus Codex Window R**，派生自父窗 `01a0c796`。

工具：`patrol/_codex_window_id_r1.py`（只读 sqlite mode=ro，可重跑）。
它扫**头 12 条** item（userMessage ＋ functionCallOutput 的 output/text），不是只取第一条。
**窗名读不到就写"读不到"，不许拿父 id 或目录冒充窗名。**

**缺口判据：按窗名判，**不许按数差**

旧判据是「活跃 thread 数 − 在册 codex 身份数」。接上窗名后它当场打出**多 0 枚**——
可现读是：一枚**已接**的 `codex:bbfix1`（10-04 19:0x 交过真 deliver）＋ 一枚**未接**的
Window R，减出来正好 0。**一枚已接加一枚未接 = 数都是 1**。
两个互相抵消的错谓词比一个更危险，所以旧那行已删（第⑦格现读只剩窗名判据那一行）。

现读（第⑦格，20:28）：

```
活跃窗自报名：CityNexus Codex Window R
派生自　：01a0c796-93d8-7621-9157-161a973cab50
**推广缺口 1 扇（窗名在名册里没有同名身份）**：CityNexus Codex Window R
   名册现有：codex:bbfix1｜要接得主人或包工头点名，我不据窗名自动注册
接入件（可直接粘）：D:/moodle/agent_bus/INVITE_CODEX.txt
```

接入件已更新（`INVITE_CODEX.txt` 1617 → 2150 字节，备份 `.bak_winR_2028`）：
不再写"两侧对不上、还是得人看一眼"，改成告诉那扇窗"你就是 Window R，粘下面这段"，
id 建议 `codex:winR`。**仍不自动注册身份**——名册里没有这一条，猜错＝给不相干的会话装身份。

**附：形状闸接进巡逻（第②格），现网反证只覆盖一臂

`_lane_tailform_r1.py`（末态尺）＋ `_knock_gate_shape_r1.py`（形状闸）已接进
`_bb_patrol_once_r1.py` 第②格。现网对照：同一组三扇、同一组 20:08 的板读数，
**旧判据列 2 扇该敲、新判据列 0 扇**——拦的依据是真流水末态，不是造的数据。

**未覆盖**：放行那一臂（末态断在半路 ⇒ 真该敲）此刻真网上造不出来（20:16 全队十五枚的末态
没有一枚是断在半路），只有自测过。`_patrol_shape_gate_liveproof_r1.py` 每次跑都会打这句声明。

另一处已补的致盲：形状闸把"判词读不到"单开②b，但它原先**没进结论行**——
"三扇不可判、零扇该敲"会被结论行报成"全队都在动"，越界的那些扇没人看见。已并入，
自测 `_conclude_undec_selftest_r1.py` 三臂全绿。
"""

ANCHOR = u"## 五·五十三、"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十四" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十三锚")
        return 1
    new = t[:i] + SEC + u"\n" + t[i:]
    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    if any(l.startswith(u"### ") for l in new.splitlines()):
        print(u"REFUSE：出现三级标题（交接稿通篇二级，三级会被体检判 bad_head），未写盘")
        return 1
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    bak = HAND + u".bak_54_2030"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 五·五十四；行数 %d → %d；五·小节现 %d 节"
          % (t.count(u"\n"), new.count(u"\n"),
             len(re.findall(r"^## 五·", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())