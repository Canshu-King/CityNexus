# -*- coding: utf-8 -*-
u"""交接稿补一节：五·五十五——J 档那句成因是**手写**的，分类器从没报过"断在半路"。

为什么必须写：20:35:57 哨兵 J 档报「1d64acf5 断在半路（尾条是没回音的 tool_use）」，
我按纪律回读流水复核，三条独立读数都说不是：
  ① 它自己那把分类器 `_why_stopped_r1.py` 判的是「**卡闸、等裁语、谈交付**」；
  ② 末态尺读出末三条 tool_use → **tool_result** → text（有回音）；
  ③ 240 KB 尾窗里 tool_result 出现 20 次（"只读尾部看不见回音"被排除）。
根因：分类器把"卡闸"和"断在半路"放**同一栏**（「该敲车道本人（卡闸/断在半路）」），
而 J 档那条消息的成因是**手写的**——就把卡闸讲成了断在半路。

修法（已落）：成因改为**从分类器原文取**；分类器真报"断在半路"才写那句，
否则写「分类器判：XXX（**非断在半路**）⇒ 该敲的是号令者点验收」，
读不到判词写「成因不可判」——**不回退到手写那句**（那正是假红的路）。

另记两条当晚踩的坑：
  · 跑批 `judge` 是**跑批自己进程里**的函数，改它必须重起跑批；
    「巡逻每拍 subprocess 重起所以自动生效」只对巡逻成立。
  · 取分类器那一行，行首**有两个空格**，直接 `startswith(id8)` 恒 False
    （我 20:40 踩过：明明输出里有那一行，取回来却是 None）。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC = u"""## 五·五十五、J 档那句成因是**手写的**：分类器从没报过"断在半路"

20:35:57 哨兵 J 档报：「J 车道 1d64acf5 断在半路（尾条是没回音的 tool_use）」。
按纪律回读复核，三条独立读数都说**不是**断在半路：

| 来源 | 读数 |
|---|---|
| 它自己那把分类器 `_why_stopped_r1.py` | 1d64acf5 静 52 分｜判：**卡闸、等裁语、谈交付** |
| 末态尺 `_lane_tailform_r1.py` | 末三条＝tool_use → **tool_result** → text ⇒ **交活型停着**，有回音 |
| 240 KB 尾窗字节计数 | 尾窗里 tool_result **20 次**（全文件 5418 次）⇒ "只读尾部"被排除 |

**根因**：分类器把「卡闸」与「断在半路」放**同一栏**（「该敲车道本人（卡闸/断在半路）」），
而 J 档那条消息的成因是**手写的**——它把卡闸讲成了断在半路。
⇒ **这是 relay 的成因，不是分类器的成因。**

**修法（已落，`_patch_j_cause_r1.py`）**：成因改为从分类器原文取（`why_stopped_line()`）。
分类器真报"断在半路"才写那句；否则写「分类器判：XXX（**非断在半路**）⇒ 该敲的是号令者点验收，
不是叫醒这一扇」；读不到判词写「成因不可判」——**不回退到手写那句**，那正是假红的路。

现读验（20:40）：`why_stopped_line("1d64acf5")` → `卡闸、等裁语、谈交付`（不含"断在半路"）；
不存在的 id → `None`。keepalive 20:40:31 起的第 71 支哨兵正好带上新代码。

**附一：改跑批的 `judge` **必须重起跑批**

`judge()` 是**跑批自己进程里**的函数——`_patrol_loop_r1.py` 每拍用 subprocess 起新的**巡逻**，
所以「改完巡逻自动生效」成立；但改跑批自己不会。19:18 那枚一直跑着改前代码，
而 `_stack_staleness_check_r1.py` **只查栈腿、不查跑批自己**，一句都没报。
⇒ 20:36 重起跑批（pid 56500），第一拍就带新判据（等单清单带出、没占红位）。

**附二：取分类器那一行，行首**有两个空格**

`_why_stopped_r1.py` 的输出行真形是 `␠␠1d64acf5␠␠车道␠␠静 52 分｜判：…`
（实测 20:40）。`line.startswith(id8)` **恒 False** ⇒ 取回来一路 None，
而"取不到"长得和"没有判词"一模一样。必须 `strip()` 之后再比。
"""
ANCHOR = u"## 五·五十四、"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十五" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十四锚")
        return 1
    new = t[:i] + SEC + u"\n" + t[i:]
    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    if any(l.startswith(u"### ") for l in new.splitlines()):
        print(u"REFUSE：出现三级标题，未写盘")
        return 1
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    bak = HAND + u".bak_55_2041"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 五·五十五；行数 %d → %d；五·小节现 %d 节"
          % (t.count(u"\n"), new.count(u"\n"),
             len(re.findall(r"^## 五·", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())