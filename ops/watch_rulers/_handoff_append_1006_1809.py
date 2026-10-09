# -*- coding: utf-8 -*-
u"""记 census 数据被我手滑清空一次、以及把默认值反过来的修法（五·三十七）。

经过（10-06 18:02）：我手动跑了一次 `_lane_round_len_census_r1.py`（想验它刚加的基线行），
**没带 `--append`** —— 而那把尺的旧默认值是"不带 `--append` 就覆盖"，于是把巡逻第⑫格
从 17:42 起攒的**五拍数据冲成了一拍**。巡逻那腿一直带的是 `--append`，它没错，错在我手动那次。

为什么这条要记（它是一类容易发生又最难发现的丢数）：
  · 攒数据的文件被手滑清空，**不会报错**（脚本照常 rc=0、照常说"已落"），
    只是明天想看分布时才发现少了几拍——**丢得静悄悄**；
  · 而这类数据的价值恰恰在"连续几拍"（五·二十七：改门槛要连续几拍分布），丢几拍等于那段时间白攒。

修法（`_lane_round_len_census_r1.py`）：**默认值反过来——默认追加，只有显式 `--overwrite` 才覆盖。**
让"手滑"和"清空"不再是同一个动作。验过：不带参数拍数 1→2（追加生效），ast 过。

给下一班一句：**凡是攒数据（逐拍落盘、逐轮追加）的脚本，默认都该是追加，覆盖必须显式。**
今晚这条与 [[feedback-verification-copies-cost-shared-disk]]（按字节判据省共享盘）是同一族，
一个怕"错算"、一个怕"错删"，都落在"别让人手滑就改了语义"上。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·三十七"

SEC = u"""## 五·三十七、census 的数据被我手滑清空过一次：默认值已反过来（默认追加）

经过（18:02）：我手动跑了一次 `_lane_round_len_census_r1.py`（想验它刚加的基线行），
**没带 `--append`** —— 而那把尺的旧默认值是「不带 `--append` 就覆盖」，于是把巡逻第⑫格
从 17:42 起攒的**五拍数据冲成了一拍**。巡逻那腿一直带的是 `--append`，它没错，错在我手动那次。

为什么这条要记（它是一类容易发生、又最难发现的丢数）：
- 攒数据的文件被手滑清空，**不会报错**（脚本照常 rc=0、照常说「已落」），
  只是以后想看分布时才发现少了几拍——**丢得静悄悄**；
- 而这类数据的价值恰恰在「连续几拍」（五·二十七：改门槛要连续几拍分布），丢几拍等于那段时间白攒。

修法（`_lane_round_len_census_r1.py`）：**默认值反过来——默认追加，只有显式 `--overwrite` 才覆盖**，
让「手滑」和「清空」不再是同一个动作。验过：不带参数拍数 1→2（追加生效）、ast 过。

给下一班一句：**凡是攒数据（逐拍落盘、逐轮追加）的脚本，默认都该是追加，覆盖必须显式。**

"""


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if MARK in t:
        print(u"已写过，不重复写")
        return 0
    a = ANCHOR + u"\n"
    if t.count(a) != 1:
        print(u"REFUSE：锚命中 %d 次 ⇒ 未写盘" % t.count(a))
        return 1
    io.open(HAND, "w", encoding="utf-8", newline="").write(t.replace(a, SEC + a))
    print(u"已插入 %s" % MARK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
