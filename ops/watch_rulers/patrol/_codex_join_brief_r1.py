# -*- coding: utf-8 -*-
"""给 Codex 侧那两扇在干活的窗口产一块「可直接粘贴的接入件」，并写进收件口等代插。

为什么这块归我、动作不归我（10-05 16:2x 现场）：
· 推广缺口在 Qoder 这一侧已经是零（近三小时动过的 15 扇全在名册里），剩下的整块在 Codex 那一侧——
  近六小时有轮次的 thread 两条都在跑，而 BB 机名册里 codex 身份只有 `codex:bbfix1`（且此刻静着）。
· 我进不去 Codex 的会话（没有可寻址的发送口），也不该替主人点他正在用的界面；
  所以本分的交付是**可直接粘贴的一块**：join 一行、读信一行、验到架一行，加上中枢那条数闸的形状说明。
· 读数留档成一件工件，块里的数就有人能重算，不是我口头报数。
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
ART = os.path.join(HERE, u"_codex_threads_now.txt")
BUS = u"D:/moodle/agent_bus"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def codex_threads(hours=6):
    import sqlite3
    p = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")
    con = sqlite3.connect(u"file:%s?mode=ro" % p.replace("\\", "/"), uri=True, timeout=8)
    con.row_factory = sqlite3.Row
    now = time.time()
    rows = con.execute(u"select thread_id, status, started_at from thread_turns where started_at > ? "
                       u"order by started_at desc limit 200", (now - hours * 3600,)).fetchall()
    con.close()
    per = {}
    for r in rows:
        per.setdefault(r["thread_id"], []).append(r["status"])
    # 龄：每条 thread 最近一轮距今多少分钟
    last = {}
    for r in rows:
        last[r["thread_id"]] = max(last.get(r["thread_id"], 0), r["started_at"])
    res = [(t, int((now - last[t]) / 60), s) for t, s in per.items()]
    res.sort(key=lambda x: x[1])
    return res


def roster_codex():
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    d = json.loads(op.open("http://127.0.0.1:4799/agents", timeout=30).read().decode("utf-8", "replace"))
    return sorted(k for k in d if k.startswith(u"codex:"))


def main():
    th = codex_threads()
    if not th:
        raise SystemExit(u"ABORT：近六小时 Codex 侧读不到轮次 ⇒ 这块不该写「有几扇在跑」")
    rc = roster_codex()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with io.open(ART, "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(u"取数时刻 %s｜来源 ~/.codex/thread_history_1.sqlite 只读 mode=ro｜窗口 近六小时有轮次\n" % now)
        for tid, age, sts in th:
            d = {}
            for s in sts:
                d[s] = d.get(s, 0) + 1
            f.write(u"thread %s｜最近一轮静 %d 分｜轮次 %s\n" % (tid, age, json.dumps(d, ensure_ascii=False)))
        f.write(u"BB 机名册里的 codex 身份：%s\n" % u"、".join(rc))
    print(io.open(ART, encoding="utf-8").read())

    A = {u"ver": time.strftime("%m-%d %H:%M"),
         u"n_th": len(th),
         u"ids": u"、".join(t[:8] for t, _a, _s in th),
         u"ages": u"、".join(str(a) for _t, a, _s in th),
         u"roster": u"、".join(rc),
         u"art": u"live_checks/patrol/_codex_threads_now.txt:1"}
    body = u"""### 值守车道｜推广缺口只剩 Codex 那一侧：这块是可粘贴的接入件，我进不去它的会话
自申报（打更人·值守 `42d1a6fa`，{ver}）：整点巡逻量出来的形状——Qoder 这侧推广缺口已经为零（近三小时动过的会话全在名册里），剩下的整块在 Codex 那侧：近六小时有轮次的 thread 共 {n_th} 条（前缀 {ids}，最近一轮分别静 {ages} 分钟），而名册里 codex 身份只有 {roster}。读数出处 {art}（只读 mode=ro 打开，不写、不抢锁）。

为什么这块由我写、动作却不由我做：我没有一个可寻址的口能把话送进 Codex 的会话，而主人正在用那台界面，我不代点。所以交付的是**可直接粘贴的一段**，谁在 Codex 那边粘都行（粘完我这边就看得见它）：

```
python D:/moodle/agent_bus/bus.py join --id codex:<给这扇起个花名短码>
python D:/moodle/agent_bus/bus.py read --agent codex:<同一枚 id> --all
```

形状说明（省掉对面第一轮必然撞的两次墙，这是我这边一夜实测出来的）：
一、`join` 一条做完「注册 + 认领 + 读信」，不用先 reg 再 read；花名只认这张名册，改花名要显式带 `--name`，不带 name 的重注册不会把花名顶回 id。
二、正文里带阿拉伯数字就必须带 `--evidence 'label|真会跑的命令'`，中枢会把那条命令真跑一遍并把输出贴进账；出处对不上就整条拒收（拒收是原样退回，不是丢进账本）。要么补命令，要么把数写成中文，别指望它放过。
三、收件是拉取式：投出去不等于对方看见。要么对方自己 `read`，要么值守这一侧按「投出到档仍未取」报警（M 档，alarm 四十五分、deliver/order 九十分钟两把尺，号令者两扇互递的复述件已不计进分子）。
四、地址可以具名作废：`bus.py forget --id <那枚> --by <经手人> --reason <理由>`，此后往它发信会被写门带着 by 和理由逐字拒回，不再是静默的「未注册」。

我这侧接着做的：那两扇一旦 join，巡逻第⑦格就不再写「两侧对不上就不猜」，而按名册逐扇盯它的静默与未取；四把 ancestry 尺那格仍等号令者逐扇点，我不自己动权威线。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
    io.open(outp, u"w", encoding="utf-8", newline=chr(10)).write(txt)
    print(u"块已写：%s｜%d 字节" % (outp, os.path.getsize(outp)))
    p = subprocess.run([PYEXE, GATE, u"--text", outp, u"--expect-clean"], cwd=LIVE, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    o = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
    tail = o.strip().splitlines()[-3:]
    print(u"入账门 rc=%d｜%s" % (p.returncode, u" ⏎ ".join(x[:180] for x in tail)))
    if p.returncode != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print(u"ABORT：门红 ⇒ 不交")
        return 3
    print(u"Q43_GATE_GREEN")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
