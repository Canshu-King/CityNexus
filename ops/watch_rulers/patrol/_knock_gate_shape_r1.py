# -*- coding: utf-8 -*-
u"""给"该敲"那一格加一道**形状闸**：静默过档还必须末态是"断在半路"才真该敲。

为什么（20:11 实测，六拍数据）：
  19:18／19:30／19:43 三拍 ②格＝0（全绿）；
  19:55 ①静默超45＝1 ⇒ ②列出 0afdb49b 静 51 分；
  20:08 ①静默超45＝2 ⇒ ②列出 8ac89982 静 46 分、0afdb49b 静 63 分；
  20:11 我逐扇回读流水（`_lane_tailform_r1.py`）：**这两扇末条都在 1 分前**
  （8ac89982 在跑工具、0afdb49b 在思考），板上同刻读数 idle 0.9／1.1，两把尺一致。
⇒ 那两扇当时确实静，但静了 46–63 分之后**自己走回来了**。所以"静默过档"这一格
  在这支队里量到的是**一次长间隔**，不是停摆；直接当"该敲"就是周期性假红。

闸怎么设（不拍脑袋）：
  静默过档 **且** 末态判词是"断在半路" ⇒ 真该敲。
  静默过档 **但** 末态是「交活型停着」或已经在写 ⇒ 记"看着像停、现读在动"，**不列该敲**。
判词由 `_lane_tailform_r1.py` 给，不另写一套形态识别（两个尺 disagree 时以流水那份为准）。

边界：只读 jsonl 与板上 API，0 次发送、0 次敲门。敲门仍归 B（号令者）那一格。
用法：python _knock_gate_shape_r1.py
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TAILFORM = os.path.join(HERE, "_lane_tailform_r1.py")
BOARD = "http://127.0.0.1:4820/api/fleet"
OVER_MIN = 45.0          # 与巡逻第①格同一门槛
TRUELY_STUCK = (u"断在半路",)


def board_rows():
    d = json.load(urllib.request.urlopen(BOARD, timeout=20))
    return d.get("fleet") or d.get("rows") or []


def tail_verdict(pre):
    r = subprocess.run([sys.executable, TAILFORM, pre], capture_output=True, cwd=HERE,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    txt = (r.stdout or b"").decode("utf-8", "replace")
    for l in txt.splitlines():
        if l.strip().startswith(u"⇒"):
            return l.strip()[1:].strip(), txt
    return u"（读不到判词）", txt


def main():
    rows = board_rows()
    if not rows:
        print(u"REFUSE：板上读不到行，不报判")
        return 1
    now = time.time()
    over = []
    for r in rows:
        idle = r.get("idle_min")
        if idle is None:
            continue
        try:
            idle = float(idle)
        except Exception:
            continue
        if idle > OVER_MIN:
            over.append((r.get("id8"), r.get("name"), idle, r.get("live")))
    print(u"现读 %s｜分母 %d 扇｜静默超 %d 分的 %d 扇"
          % (time.strftime("%H:%M:%S"), len(rows), int(OVER_MIN), len(over)))
    real, look = [], []
    for id8, name, idle, live in sorted(over, key=lambda x: -x[2]):
        v, raw = tail_verdict(id8)
        line = u"  %s %s 静 %.0f 分（板读态 %s）" % (id8, name or u"", idle, live)
        if any(k in v for k in TRUELY_STUCK):
            real.append(id8)
            print(line + u" ⇒ **真该敲**：" + v)
        else:
            look.append(id8)
            print(line + u" ⇒ 不列该敲（" + v + u"）")
    print()
    print(u"⇒ 真该敲 %d 扇：%s" % (len(real), u"、".join(real) or u"无"))
    print(u"  看着像停、现读在动 %d 扇：%s" % (len(look), u"、".join(look) or u"无"))
    print(u"边界：只读，未敲未发；敲门归号令者那一格。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())