# -*- coding: utf-8 -*-
u"""把附录清单里两条"我编的文件名"删掉/改正（`_adoption_boot_check_r1.py`、`_patch_sentinel_blindretry_r1.py`）。

那两条对应的真实改动是：
  · 续跑器的 blind 分支 ⇒ 真件是 `patrol/_patch_keepalive_blindretry_r1.py`（我写错了后缀）；
  · "开机时刻现读"那把尺 ⇒ **不存在**（我当时把它写进清单时并没有那个文件）⇒ 整条删掉。
这是今晚第二次"清单里写了没核实的东西"：上一次是裸名（找不到），这次是**整个文件名是编的**。
清单里的每一项必须 `os.path.exists` 过才准留——这条本身也写进脚本里当下次自检。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")


def main():
    p = HAND
    t = io.open(p, encoding="utf-8", newline="").read()
    before = len(t)
    # ① 续跑器那条：改正名
    t = t.replace(u"`_patch_sentinel_blindretry_r1.py`", u"`patrol/_patch_keepalive_blindretry_r1.py`")
    # ② 开机时刻现读那条：整条删（那个文件不存在）
    t = re.sub(r"(?m)^- `_adoption_boot_check_r1\.py`（[^）]*）.*\n", u"", t)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    # ③ 自检：附录里每一条的路径都得真存在
    app = t[t.index(u"## 附录：今夜"):]
    bad = []
    for m in re.finditer(r"`([A-Za-z0-9_/]+\.py)`", app):
        f = m.group(1)
        if not (os.path.exists(f)
                or os.path.exists(os.path.join("patrol", os.path.basename(f)))
                or os.path.exists(os.path.join("..", "agent_bus", os.path.basename(f)))):
            bad.append(f)
    print("改正后字符数 %d（少了 %d）；附录指不到文件的：%s"
          % (len(t), before - len(t), bad or "无"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
