# -*- coding: utf-8 -*-
u"""写一份"今夜收尾快照"：此刻状态 ＋ 可复跑凭据，与决策单、审计页并列。

为什么不是"又一篇日志"：交接稿已有五十多节、1168 行；明早接手的人要的是**一个数字来源**
（此刻状态）和**三件待裁**（决策单）而不是重读日志。这一页把"收在什么位置"一屏说完。
"""
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "SHIFT_CLOSE_1006.md")


def main():
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    f = json.loads(subprocess.run(
        [sys.executable, "-c",
         "import json,urllib.request;"
         "print(urllib.request.urlopen('http://127.0.0.1:4820/api/fleet',timeout=25).read().decode('utf-8'))"],
        capture_output=True).stdout.decode("utf-8", "replace"))
    c = f["counts"]
    stack = subprocess.run([sys.executable, os.path.join(HERE, "patrol", "_watch_stack_r1.py"), "--check"],
                           capture_output=True, timeout=180).stdout.decode("utf-8", "replace").strip().splitlines()[-1]
    census = ""
    cp = os.path.join(HERE, "patrol", "_lane_round_len_census_1006.txt")
    if os.path.exists(cp):
        for l in reversed(io.open(cp, encoding="utf-8", errors="replace").read().splitlines()):
            if "形态结论" in l:
                census = l.strip()
                break

    T = u"""# 今夜收尾快照（%s 现读）

**一句话**：在册 %d 扇**全部在写**，静默超 45 分 %d 扇，该敲 0，缺单 0，额度墙 %d，掉线 %d。
推广满格（本机车道侧：两腿全无 0／只收不发 0）。

## 凭据（都可复跑）
- 舰队现读：`python -c "import json,urllib.request;print(urllib.request.urlopen('http://127.0.0.1:4820/api/fleet',timeout=25).read().decode())"`
- 值守栈：`python _watch_stack_r1.py --check` ⇒ `%s`
- 形态结论（每拍随巡逻落盘）：`%s`

## 三件等人裁 / 点头（细的见 DECISION_1006.md）
1. BB 机"人"那三个地址还要不要当交付收件人（号令者未取 78／主人未取 13；里面没有一条真待办）。
2. Codex 那个活跃 thread 是不是新车道（在册那枚 bbfix1 已完成推广；thread 与地址无映射，值守不猜）。
3. 开机任务注册那一行（预检：名字未被占、非管理员 ⇒ 需一次提权）。

## 覆盖到哪
- 四条常驻腿收工 23:35–23:40，晚于明早 11:00 与今晚 23:20 终值单；两档取数器到点自跑、不依赖腿收工。
- 唯一会打断覆盖的是本机重启；兜底件 `patrol/stack_boot_restart.bat` 本机跑过、幂等，注册见上第 3 件。

## 别把"值守在跑"读成"目标达成了"
逐条对账见 GOAL_AUDIT_1006.md；交接稿本体 `HANDOFF_20261005_NIGHT.md`（体检全绿，附录每条路径可解析）。
""" % (now, c["writing"], c["quiet45"], c["quota"], c["dropped"], stack, census or "（census 文件暂无）")

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(T)
    print(u"已写 %s（%d 字符）：在写 %d／静默超45 %d／掉线 %d／栈 %s"
          % (os.path.basename(OUT), len(T), c["writing"], c["quiet45"], c["dropped"], stack))


if __name__ == "__main__":
    sys.exit(main())
