# -*- coding: utf-8 -*-
u"""交班快照（22:05 现读）：明早那班不接班也能一眼看清"夜班留下了什么"。

为什么要有它：交接稿已经 1522 行、59 节——那是**给要查细节的人**读的。
但明早第一件事往往是"现在什么状况"，翻 1500 行不划算。
所以这份只放**现读读数**＋**已知缺口**，每条都带出处（哪一格／哪个文件），查得到。

三条纪律：
  ① 每个数都来自**这一轮现读**，不抄上一轮的（车道在动，抄就过期）；
  ② 每个数后面写清**分母**（"在写 12／在册 15" 而不是 "在写 12"）；
  ③ 缺口单列，不混进正常项——不写"推广已完成"这类乐观话（今晚已为此更正过两处）。

跑法：python _shift_snapshot_r1.py            # 打印
      python _shift_snapshot_r1.py --write    # 追加进 SHIFT_CLOSE_1006.md
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(os.path.dirname(HERE), "SHIFT_CLOSE_1006.md")


def board():
    d = json.load(urllib.request.urlopen("http://127.0.0.1:4820/api/fleet", timeout=20))
    # 收班那格现读。写它时我第一版把它**写死成 0**（`if False else 0`），
    # 输出"收班 0 扇"而板上报 3 —— **写死的数字冒充读数**，是今晚反复出现的那类错。
    return (d.get("rows") or [], d.get("counts") or {}, d.get("at"),
            d.get("retired_n", u"?"))


def stack():
    import _watch_stack_r1 as W
    rows = W.ps_rows()
    out = []
    for entry in W.COMPONENTS:
        name, script = entry[0], entry[1]
        slot = entry[4] if len(entry) > 4 else None
        hit = W.alive(name, os.path.basename(script), rows, slot=slot)
        out.append((name, [h[0] for h in hit]))
    return out


def rounds():
    fs = [f for f in os.listdir(os.path.join(HERE, "rounds"))
          if f.startswith("round_") and f.endswith(".txt")]
    fs.sort(key=lambda f: os.path.getmtime(os.path.join(HERE, "rounds", f)))
    return fs


def main():
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    A = lines.append
    A(u"# 交班快照 · 读数时刻 %s" % now)
    A(u"")
    A(u"> 只放现读读数与已知缺口；细节查 `HANDOFF_20261005_NIGHT.md`（59 节）。")
    A(u"")

    # ① 车队
    try:
        rows, cnt, at, retired = board()
        A(u"## 车队（板上现读 %s）" % at)
        A(u"")
        A(u"- 在册 **%d** 扇＋收班 **%s** 扇；**在写 %s**；静默超 45 分 **%s**；"
          u"额度墙 **%s**；掉线 **%s**；未接 BB 机 **%s**"
          % (len(rows), retired, cnt.get("writing", u"?"), cnt.get("quiet45", u"?"),
             cnt.get("quota", u"?"), cnt.get("dropped", u"?"),
             sum(1 for r in rows if not r.get("in_hub"))))
        A(u"  （出处：板 `/api/fleet`；分母＝在册 %d 扇）" % len(rows))
    except Exception as e:
        A(u"## 车队：**读不到**（%s: %s）⇒ 不当它空" % (type(e).__name__, str(e)[:60]))

    # ② 值守栈
    A(u"")
    A(u"## 值守栈（现读）")
    A(u"")
    try:
        for name, pids in stack():
            A(u"- %-14s %s" % (name, u"、".join(pids) if pids else u"**缺**"))
    except Exception as e:
        A(u"- **读不到**（%s: %s）" % (type(e).__name__, str(e)[:60]))

    # ③ 巡检跑批
    A(u"")
    A(u"## 巡检跑批（现读）")
    A(u"")
    try:
        fs = rounds()
        newest = fs[-1] if fs else None
        n = len([f for f in fs if "56500" in f])
        A(u"- pid 56500 已落 **%d** 拍；末拍 `%s`（%s）"
          % (n, newest, time.strftime("%H:%M", time.localtime(
              os.path.getmtime(os.path.join(HERE, "rounds", newest)))) if newest else u"（无）"))
        ne = os.path.join(HERE, "rounds", "_needs_eyes.log")
        if os.path.exists(ne):
            body = io.open(ne, encoding="utf-8", errors="replace").read().strip().splitlines()
            A(u"- 待看档最后一条：%s" % (body[-1] if body else u"（空）"))
    except Exception as e:
        A(u"- **读不到**（%s: %s）" % (type(e).__name__, str(e)[:60]))

    # ④ 已知缺口（单列，不混进正常项）
    A(u"")
    A(u"## 已知缺口（**未完成**，别当已完成）")
    A(u"")
    A(u"- **推广：Codex 侧零活跃车道接入**。名册里唯一接过的 `codex:bbfix1` 最近一次发出在"
      u" 4404 分前（约 73 小时）⇒ 接上过、早已不活跃；唯一活跃的那扇窗自报窗名"
      u" `CityNexus Codex Window R`（thread `01a10cd0…`），**尚未注册**。")
    A(u"  那扇窗的流水里从未提过账本或接入件 ⇒ **投块它收不到**，只能由人把它叫起来粘一条"
      u" `bus.py join --id codex:winR`（接入件：`D:/moodle/agent_bus/INVITE_CODEX.txt`，已验命令能跑通）。")
    A(u"- **开机任务 `CNXWatchStackBoot` 未注册**（预检：任务名空闲、指向件存在）。")
    A(u"  一键件已备好：`patrol/register_boot_task_once.bat`（纯 ASCII/CRLF、幂等），"
      u"**等主人在时点一次**——值守会话不该在无人时弹 UAC。")
    A(u"- **落地顺序表刚出生就过期**：权威尖在连续动（22:00 前几分钟内从 4323a5ce 走到 "
      u"ff7f62011 之后又动）。处置是点单前那一拍现跑现读，不是重跑到绿。")
    A("")
    A(u"## 不动的边界（这一班守住的）")
    A(u"")
    A(u"- 权威线只由号令者移动；我 0 次 fetch 写／0 次 apply／0 次重写历史。")
    A(u"- 敲门归号令者那一格；我的形状闸只拦「静默过档但末态是交活型」的假红。")
    A(u"- 删锁、注册身份、改计划任务都要人点头；本班只准备件。")

    text = "\n".join(lines) + "\n"
    print(text)
    if "--write" in sys.argv:
        with io.open(OUT, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(u"\n" + text)
        print(u"⇒ 已追加进 %s（%d 字节）" % (os.path.basename(OUT), len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())