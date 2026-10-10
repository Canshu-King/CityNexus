# -*- coding: utf-8 -*-
"""值守 10-02 01:26 · 哨兵的续跑器：它早退之后自动再起一支，让夜里剩下的时间不断档。

为什么需要：`_sentinel_relay_r1.py` 现在只在 A/E/F 三格（我动得了的那三格）早退——早退之后**没人再起它**。
今晚的目标是 10-02 23:00 那一档，还有 21 个多小时；我一次在线只能补一段，用户睡了。
所以把「续跑」装进进程里（和 `autumn_supervise_r1.py` 对自动轮做的事同一个形制）。

形制（沿用今晚验过的三条）：
  · 只按 **CommandLine 含 `_sentinel_relay_r1.py`** 数活着的实例，不认 PID、不认端口（复用 PID 认错人今晚踩过）；
  · 起之前先算还剩多少分钟到 STOP，预算按剩余时间给，不写死；
  · 到 STOP（默认今天 23:35）就收工并在日志里写明为什么停，免得下一班以为它死了。
  · 只启动我自己那一支仪表；绝不碰 `cmdr_night_watch_r1.py`（号令者的助手）与任何别人的进程。

用法：PYTHONIOENCODING=utf-8 python _sentinel_keepalive_r1.py        （后台跑，每 300 秒查一次）
边界：本脚本自己不起第二支（认到现支就等）；`SENTINEL_STOP` 可改收工时刻。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
LOG = os.path.join(HERE, "_sentinel_keepalive.log")
STOP = os.environ.get("SENTINEL_STOP", "2335")
PERIOD = int(os.environ.get("SENTINEL_PERIOD", "900"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(s):
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(time.strftime("[%m-%d %H:%M:%S] ") + s + "\n")


def instances():
    u"""现支哨兵的 pid 列表。返回 []＝确认没有；返回 None＝这一拍查不到（超时/系统忙）。

    为什么不 raise（10-06 实测）：这条 CIM 全表枚举在负载高时会跑满 120 秒而 TimeoutExpired，
    老写法让整支续跑器退出——日志里一晚上有六次。续跑器死了不算"哨兵死了"，
    但从这一刻起没人再看住那一拍，最长十五分钟的空窗就是这么来的。
    """
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                            "ForEach-Object { if ($_.CommandLine -match '_sentinel_relay_r1\\.py') { $_.ProcessId } }"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:                      # TimeoutExpired / OSError 都算"这一拍不知道"
        say(u"查现支没查到（%s: %s）⇒ 这一拍当不知道，绝不因为看不见就起第二支"
            % (type(e).__name__, str(e)[:80]))
        return None
    return [x.strip() for x in (r.stdout or "").splitlines() if x.strip().isdigit()]


def stop_today(stop=STOP):
    """收工时刻。`2335` = 今天 23:35；`1004-1100` = 10-04 11:00。

    为什么加日期形制：objective 要值守到「明天 11 点」，而旧写法只认当天——
    过午夜就会直接收工， coverage 从半夜断掉，除非我半夜再起来重启一次（人会睡着，脚本不该依赖我）。
    """
    if "-" in str(stop):
        md, hm = str(stop).split("-", 1)
        base = "%s-%s-%s" % (time.strftime("%Y"), md[:2], md[2:])
    else:
        base = time.strftime("%Y-%m-%d")
        hm = str(stop)
    h, m = int(hm[:2]), int(hm[2:])
    return time.mktime(time.strptime(base + " %02d:%02d:00" % (h, m), "%Y-%m-%d %H:%M:%S"))


def decide(live, now, stop_at):
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
    mins = max(5, int((stop_at - now) / 60))
    return ("launch", mins)


def launch(mins):
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008   # DETACHED_PROCESS
    with io.open(os.devnull, "rb") as dn, io.open(LOG, "a") as out:
        subprocess.Popen([PYEXE, os.path.join(HERE, "_sentinel_relay_r1.py"), str(mins), str(PERIOD)],
                         stdin=dn, stdout=out, stderr=out, cwd=HERE, creationflags=flags,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def main():
    stop_at = stop_today()
    say("=== 哨兵续跑器起来：到 %s 收工；每 300 秒查一次现支（pid=%s）" % (STOP, os.getpid()))
    n = 0
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
        if act == "launch":
            n += 1
            launch(mins)
            say("起第 %d 支哨兵：预算 %d 分钟（到 %s）、每 %d 秒一轮" % (n, mins, STOP, PERIOD))
        time.sleep(120)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
