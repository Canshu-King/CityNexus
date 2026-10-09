# -*- coding: utf-8 -*-
u"""给哨兵续跑器装一道"查不到就当不知道、绝不因此起第二支"的闸。

成因（10-06 现读日志）：`_sentinel_keepalive.log` 里 `subprocess.TimeoutExpired` 出现 6 次——
`instances()` 那条 CIM 全进程枚举在机器负载高时会超过 120 秒，一超时就 raise，
main() 没接 ⇒ 整支续跑器当场退场。栈那一格之后会把它补回来（04:09 实测补回 pid=48568），
但每一回都留下最长十五分钟的"没人看哨兵"空窗，而这班的目标是守到明天 11:00。

为什么不能改成"查不到就起一支"：双哨兵＝双报警，那是这堆仪表里点名的真事故
（`_watch_stack_r1.py` 的「哨兵判红早退」那一格专门写了别再手起第二枚）。
所以 unknown 只能等下一拍重查，但必须**连续**重查不成就在日志里具名喊出来——
单向致盲也算仪器缺陷。

改三处：instances() 吞掉超时/OS 错并返回 None；decide() 多一个 unknown 分支（wait，不 launch）；
main() 数连续 unknown，到第 3 次写一行点名（之后每 3 次再写一行，不刷屏）。
动盘前 ast.parse；备份由调用方先做。

跑法：python _patch_keepalive_blindretry_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, u"_sentinel_keepalive_r1.py")

EDITS = [
    # ① instances()：查不到就返回 None（不是 []：[] 是"确认没有"，None 是"这一拍不知道"）
    (u'''def instances():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                        "ForEach-Object { if ($_.CommandLine -match '_sentinel_relay_r1\\\\.py') { $_.ProcessId } }"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return [x.strip() for x in (r.stdout or "").splitlines() if x.strip().isdigit()]
''',
     u'''def instances():
    u"""现支哨兵的 pid 列表。返回 []＝确认没有；返回 None＝这一拍查不到（超时/系统忙）。

    为什么不 raise（10-06 实测）：这条 CIM 全表枚举在负载高时会跑满 120 秒而 TimeoutExpired，
    老写法让整支续跑器退出——日志里一晚上有六次。续跑器死了不算"哨兵死了"，
    但从这一刻起没人再看住那一拍，最长十五分钟的空窗就是这么来的。
    """
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                            "ForEach-Object { if ($_.CommandLine -match '_sentinel_relay_r1\\\\.py') { $_.ProcessId } }"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:                      # TimeoutExpired / OSError 都算"这一拍不知道"
        say(u"查现支没查到（%s: %s）⇒ 这一拍当不知道，绝不因为看不见就起第二支"
            % (type(e).__name__, str(e)[:80]))
        return None
    return [x.strip() for x in (r.stdout or "").splitlines() if x.strip().isdigit()]
'''),

    # ② decide()：多一个 unknown 形——等，不起
    (u'''def decide(live, now, stop_at):
    """续跑决策：到点收工 / 有现支就等 / 没现支就起（返回要起的分钟数）。"""
    if now >= stop_at:
        return ("stop", 0)
    if live:
        return ("wait", 0)
''',
     u'''def decide(live, now, stop_at):
    u"""续跑决策：到点收工 / 有现支就等 / 查不到也等 / 确认没有才起（返回要起的分钟数）。

    live is None 那一支是新加的：查不到不等于没有。双哨兵＝双报警，比空窗更坏，
    所以这里只能等下一拍重查（空窗由 main() 里的连续计数点名）。
    """
    if now >= stop_at:
        return ("stop", 0)
    if live is None:
        return ("blind", 0)
    if live:
        return ("wait", 0)
'''),

    # ③ main()：连续盲拍要具名喊，不能只躺在日志行里
    (u'''    n = 0
    while True:
        now = time.time()
        if now >= stop_at:
            say("到 STOP=%s，续跑器主动收工；此后没有哨兵，需要就再跑一次本脚本。" % STOP)
            return 0
        act, mins = decide(instances(), now, stop_at)
        if act == "wait":
            time.sleep(300)
            continue
''',
     u'''    n = 0
    blind = 0
    while True:
        now = time.time()
        if now >= stop_at:
            say("到 STOP=%s，续跑器主动收工；此后没有哨兵，需要就再跑一次本脚本。" % STOP)
            return 0
        act, mins = decide(instances(), now, stop_at)
        if act == "blind":
            blind += 1
            if blind % 3 == 1:                   # 第 1、4、7… 次点名，不刷屏
                say(u"连续 %d 拍查不到现支 ⇒ 这一格此刻不可信（栈完整不等于哨兵在跑）；"
                    u"下一拍重查，仍不做起第二支的动作" % blind)
            time.sleep(120)
            continue
        blind = 0
        if act == "wait":
            time.sleep(300)
            continue
'''),
]


def main():
    t = io.open(T, encoding="utf-8").read()
    if u'"blind"' in t:
        print(u"已装过（decide 里有 blind 分支），不重复写")
        return 0
    for old, new in EDITS:
        n = t.count(old)
        if n != 1:
            print(u"REFUSE：一处锚命中 %d 次（要 1 次）⇒ 未写盘：%r" % (n, old[:70]))
            return 1
    for old, new in EDITS:
        t = t.replace(old, new)
    ast.parse(t)
    if u"--check" in sys.argv:
        print(u"--check：%d 处锚各命中一次、替换后 ast 过（未写盘）" % len(EDITS))
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(t)
    print(u"已写 _sentinel_keepalive_r1.py：查不到就等＋连续盲拍点名")
    return 0


if __name__ == "__main__":
    sys.exit(main())
