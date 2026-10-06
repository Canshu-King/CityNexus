# -*- coding: utf-8 -*-
u"""交接稿补一节：五·五十三——「静默过档」这一格会周期性假红，要加形状闸。

为什么必须写：19:55 与 20:08 两拍，巡逻第②格把 0afdb49b（静 51→63 分）与 8ac89982（静 46 分）
列成「该敲」；20:11 我逐扇回读流水，**两扇末条都在 1 分前**（一扇在跑工具、一扇在思考），
板上同刻读数 idle 0.9／1.1，两把尺一致 ⇒ 当时确实静过，但静完自己走回来了。
这条不写进交接稿，下一班会把"静 60 分"直接当停摆去敲门，敲的是刚走回来的车。

另附两件同晚的东西：
  · `_lane_tailform_r1.py`——流水末态尺。今晚为同一件事写过三个探针、三次都栽在 timestamp 形状上
    （整数 epoch 毫秒／ISO 串／缺键三种都有），固化成一把尺。
  · `_knock_gate_shape_r1.py`——形状闸：静默过档 **且** 末态判「断在半路」才真该敲；
    交活型停着归"看着像停、现读在动"，不列该敲；判词读不到归不可判，**不当该敲**。
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC = u"""## 五·五十三、「静默过档」会**周期性假红**：静完自己走回来的车不算停摆

六拍现读（巡检跑批 pid 35364 的前五档，档名在 `patrol/rounds/`）：

| 时刻 | 在写 | 静默超45 | 第②格「该敲」 |
|---|---|---|---|
| 19:18 | 12 | 0 | 0 扇 |
| 19:30 | 5 | 0 | 0 扇 |
| 19:43 | 14 | 0 | 0 扇 |
| 19:55 | 13 | 1 | 0afdb49b 静 51 分 |
| 20:08 | 9 | 2 | 8ac89982 静 46 分、0afdb49b 静 63 分 |

20:11 我逐扇回读流水：**这两扇末条都在 1 分前**（8ac89982 在跑工具、0afdb49b 在思考）；
板上同刻读数 idle 0.9／1.1，两把尺一致。⇒ 那两扇当时确实静，但静完自己走回来了。

所以第②格量到的是**一次长间隔**，不是停摆——这是本文件 五·三十三 那条结论的另一半：
"交活型停着不该敲"讲的是末态；这里讲的是**门槛**：静 46–63 分在这支队里是正常呼吸。

### 修法：加形状闸（已装、已自测）

`patrol/_knock_gate_shape_r1.py`：静默过档 **且** 末态判「断在半路」⇒ 真该敲；
末态是「交活型停着」或已经在写 ⇒ 记「看着像停、现读在动」，**不列该敲**；
判词读不到 ⇒ **不可判**，不当该敲（不拿默认值冒充读数）。

判词来自 `patrol/_lane_tailform_r1.py`（末态尺），不另写一套形态识别——
两个尺 disagree 时以读流水那份为准。自测 `_knock_gate_shape_selftest_r1.py` 四臂：
断在半路→真该敲｜交活型→不列｜两态分开不混｜判词读不到→不可判。20:12 全绿。

### 顺带固化的坑：timestamp 有三种形状

今晚为同一件事现写过三个探针，三次都栽在**同一处**。Qoder 的 jsonl 里 `timestamp`：
整数 epoch **毫秒**（实测 1791286362177）／ ISO 字符串（2026-10-06T12:10:11.518Z）／ **缺这个键**。
拿秒去 `fromtimestamp` 直接 OverflowError，拿字符串去 `float()` 直接 ValueError。
现在统一走 `_lane_tailform_r1.py` 的 `to_epoch()`，取不到返回 None（不猜）。

另：读末态**只认有 role 或 content 的对话节点**。jsonl 末尾三条常常是 `active-leaf`／
`runtime-config`／`file-history-snapshot` 这类脚手架节点，**每分钟被工具刷新**——
取到它们会把活车读成"活的假象"（20:00 我第一版核实就栽在这儿）。

### 19:40 那次投递的门拒原话（留给下一班省一次返工）

块被 Q43 拒了一轮，19 处 `NUMBER_WITHOUT_COORDINATE`。改法不是换量词——量词「件」在
`COUNT_WORDS` 里但不在这把尺的 `UNITS`（px/秒/分钟/字节…）里，所以"290 件"照样红。
正解是**每个数字所在行内带一个耐久坐标**。三个反直觉的点：

1. `live_checks/patrol/_recount_decision_tbl_r1.py:52` 这种行号坐标过门了，但门会给一条
   advisory `QUANTITY_VOUCHED_ONLY_BY_A_SOURCE_LINE_NUMBER`（32 项）——行号会随上游位移失效。
2. **「同上」「坐标同上表」不算坐标**。窗口 ±200 字符内必须出现真的 `file:行` 字面。
3. 表行与长列举行最容易漏：`| human:you01 … |` 那格里的数字离上一行的坐标超窗，
   得在**表行下面贴一行 HTML 注释**当坐标才过。

坐标里的行号要**现读**再写：我凭印象写 `_sentinel_relay_r1.py:399`，真值是 792。
"""

ANCHOR = u"## 五·五十二、"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十三" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十二锚")
        return 1
    new = t[:i] + SEC + u"\n" + t[i:]
    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    bak = HAND + u".bak_53_1212"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 五·五十三；行数 %d → %d；五·小节现 %d 节"
          % (t.count(u"\n"), new.count(u"\n"),
             len(re.findall(r"^## 五·", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())