# -*- coding: utf-8 -*-
u"""记「11:00 那一档的读数件到点能不能出」这条依赖确认（五·三十四）。

问题：目标写的是"守到明天 11:00"，而交接稿里有两档到点取数（10:55 收尾档、23:00 终值单档）。
万一到点那一刻某条值守腿已经收工，取数会不会跟着空跑、那份读数件就出不来？

现读核对（10-06 18:03，`_night_verdict_runner_r1.py` → `run_writer` → 两条尺）：
  · `night_verdict_r2.py` 读的是：本地 `disk_points.txt`／`bus_ids.txt`／`autumn_watch.log`、
    GitHub API（现读尖）、以及子进程跑的几把小尺（`_quota_roster_r1.py`／`_dark_window_r1.py` 等）；
  · `_night_tip_local_r1.py` 读的是：本地 git（`ls-remote`／`log`）。
  ⇒ **两条都不依赖哨兵、板子、BB 机这些"值守腿"**；依赖的是**本地文件 ＋ git ＋ GitHub API**。
     就算 23:40 各腿都收工了，那一档照样能出件（前提是本机没重启——重启的话由开机起复件补，见 五·一一）。

这一条要写下来的原因：它把"11:00 交班时会不会少一份读数"这个担心，从"取决于值守腿还在不在"
变成"只取决于本机没重启"——**后者我有开机起复件兜着**（待主人点头注册，见 五·一一）。

（顺带把今晚另一处"看着空其实没空"记在这儿：五·二〇 那次，第 1 格权威尖空了是
 GitHub API 侧 IncompleteRead（远端库拉不完），不是本地腿的问题——两处空因完全不同，别混着归因。）
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·三十四"

SEC = u"""## 五·三十四、"11:00 交班时那一份读数件到点能不能出"——只取决于本机没重启

现读核对（18:03，`_night_verdict_runner_r1.py` → `run_writer` → 两条尺）：
- `night_verdict_r2.py` 读的是：本地 `disk_points.txt`／`bus_ids.txt`／`autumn_watch.log`、
  GitHub API（现读尖）、以及子进程跑的几把小尺；
- `_night_tip_local_r1.py` 读的是：本地 git（`ls-remote`／`log`）。

⇒ **两条都不依赖哨兵、板子、BB 机这些"值守腿"**，依赖的是**本地文件 ＋ git ＋ GitHub API**。
就算 23:40 各腿都收工了，那一档照样能出件；**唯一会真的让它空的，是本机重启**
（而重启由开机起复件兜着，待主人点头注册，见 五·一一）。

把这条写下来的原因：它把"11:00 交班时会不会少一份读数"从"取决于值守腿还在不在"
变成"只取决于本机没重启"——后者已有兜底，前者本来就没有。

顺带把今晚另一处"看着空其实没空"记在这儿：五·二〇 那次第 1 格权威尖空了，是 GitHub API 侧
IncompleteRead（远端库拉不完），**不是本地腿的问题**——两处空因完全不同，别混着归因。

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
