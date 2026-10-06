# -*- coding: utf-8 -*-
"""值守 03:5x · 自动轮的监督启动器：一支预算跑完就再起一支，让覆盖不断档。

为什么要有这一枚：`autumn_watch.py` 是一次性预算（argv[1] 拍 × argv[2] 秒）。03:39 起那一支只有 30 拍，
到 09:0x 就退；退之后到夜里 23:00 这段（车队真正要干活的时间）没人看着。叫醒我一次只能补一段，
而用户睡了——所以把"续跑"这件事装进一个进程里，而不是依赖我记得去重启。

形制（都是今晚踩过才知道要的）：
  · 起之前先按 **CommandLine 含 `autumn_watch.py`** 数活着的支（不是 PID、不是端口）；有就不起，等下一轮再查。
    这一条是 01:08 那枚锁的教训反过来用：那支锁认错人是把复用 PID 当成了活人，这里只认同一条命令的命令行。
  · 内层退码 0 = 预算跑完 ⇒ 立刻续一支；退码 2 = 单实例锁拒绝双开 ⇒ 等一拍再来，不硬抢。
  · 到 STOP 时刻（默认今天 23:40）就不再续，日志里写明为什么停，免得下一班以为它死了。
  · 只启动我自己那一支仪表；绝不碰 `cmdr_night_watch_r1.py`（号令者的助手）与任何别人的进程。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
LOG = os.path.join(HERE, "autumn_supervise.log")
ROUNDS = os.environ.get("SUP_ROUNDS", "30")
GAP = os.environ.get("SUP_GAP", "600")
TICK_S = int(os.environ.get("SUP_TICK_S", "300"))   # 本监督自己的巡检节拍（秒）
STOP = os.environ.get("SUP_STOP", "2340")          # 到这天 23:40 就不再续
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(s):
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(time.strftime("[%m-%d %H:%M:%S] ") + s + "\n")


def watchers():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                        "ForEach-Object { if ($_.CommandLine -match 'autumn_watch\\.py') { $_.ProcessId } }"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    return [x.strip() for x in (r.stdout or "").splitlines() if x.strip().isdigit()]


def stop_today():
    """收工时刻：`2340` 是今天 23:40，`1004-1100` 是 10-04 11:00（同 keepalive，写到这里说明原因一次就够）。"""
    if "-" in STOP:
        md, hm = STOP.split("-", 1)
        base = "%s-%s-%s" % (time.strftime("%Y"), md[:2], md[2:])
    else:
        base, hm = time.strftime("%Y-%m-%d"), STOP
    h, m = int(hm[:2]), int(hm[2:])
    return time.mktime(time.strptime(base + " %02d:%02d:00" % (h, m), "%Y-%m-%d %H:%M:%S"))


def keepers():
    u"""数活着的栈看护（按 CommandLine，不按 PID、不按端口）。"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                        "ForEach-Object { if ($_.CommandLine -match '_stack_keeper_r1\\.py') { $_.ProcessId } }"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    return [x.strip() for x in (r.stdout or "").splitlines() if x.strip().isdigit()]


def ensure_keeper():
    u"""交叉监督：keeper 保着本脚本，本脚本也回头看它一眼。

    为什么必须反着保一条（01:4x 审计）：keeper 每 900 秒跑 _watch_stack 起复 7 个组件，
    其中就有 supervise；但 supervise 原先只数 autumn_watch，不看 keeper ⇒
    keeper 一死整栈没人起，日志与板子一起停更，正是 10-04 那 178 分钟黑窗的形状。
    取不到数时按"不确定"处理：宁可不猜死，也不重复起（keeper 自己有单实例锁）。
    """
    try:
        live = keepers()
    except Exception as e:
        say(u"keeper 那一支查不动（%s）⇒ 这一拍不猜它死了，不起第二支" % type(e).__name__)
        return
    if live:
        return
    say(u"栈看护不在（CommandLine 数到 0 条）⇒ 带 STOP=%s 起一支回来" % STOP)
    det = 0x00000008 | 0x00000200
    with io.open(os.path.join(HERE, "_stack_keeper.log"), "a", encoding="utf-8", errors="replace") as lg:
        subprocess.Popen([PYEXE, os.path.join(HERE, "_stack_keeper_r1.py")], cwd=HERE,
                         stdout=lg, stderr=subprocess.STDOUT,
                         env=dict(os.environ, STACK_KEEPER_STOP=STOP, SENTINEL_STOP=STOP,
                                  PYTHONIOENCODING="utf-8"),
                         creationflags=det, close_fds=True)


def main():
    say("=== 监督启动器起来：每支 %s 拍 x %s 秒；到 %s 就不再续（pid=%s）" % (ROUNDS, GAP, STOP, os.getpid()))
    n = 0
    child = None
    t0 = 0.0
    while True:
        if time.time() >= stop_today():
            say("到 STOP=%s，监督主动收工；此后没有自动轮，需要就再跑一次本脚本。" % STOP)
            return 0
        # 三件都在这一个非阻塞节拍里做：收上一支的 rc、查栈看护、查自动轮。
        # 以前这里是 subprocess.call(30 拍 x 600 秒)＝阻塞 5 小时，
        # 期间 keeper 死了也无人查（01:4x 负对照实测：340 秒后 keeper 没回来）。
        if child is not None and child.poll() is not None:
            say("第 %d 支退出 rc=%s，跑了 %.1f 分钟（rc=2 是单实例锁拒绝双开，等一拍再试）"
                % (n, child.returncode, (time.time() - t0) / 60.0))
            child = None
        ensure_keeper()
        if child is None:
            live = watchers()
            if live:
                say("现成有自动轮在跑（%d 条进程行：%s），这一拍不起" % (len(live), ",".join(live[:4])))
            else:
                n += 1
                t0 = time.time()
                say("起第 %d 支：autumn_watch.py %s %s（不阻塞，%d 秒后再查）" % (n, ROUNDS, GAP, TICK_S))
                lg = io.open(os.path.join(HERE, "autumn_watch.log"), "ab", buffering=0)
                child = subprocess.Popen([PYEXE, os.path.join(HERE, "autumn_watch.py"), ROUNDS, GAP],
                                         stdout=lg, stderr=subprocess.STDOUT, cwd=HERE)
        time.sleep(TICK_S)


if __name__ == "__main__":
    raise SystemExit(main())
