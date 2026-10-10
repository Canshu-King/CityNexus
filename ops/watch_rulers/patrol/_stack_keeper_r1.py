# -*- coding: utf-8 -*-
"""值守栈的「看门人」：每 PERIOD 秒跑一次 `_watch_stack_r1.py`（那条命令本身自测过：缺才起、有就不起）。

为什么要有它：这一夜的覆盖是四层互相拉的——supervise 带 watch、keepalive 带哨兵、栈脚本能一键起复全部（含 BB 机中枢）。
但**栈脚本原先只能靠人敲**：我睡着或我正忙于传话时，supervise 或 keepalive 自己掉了，就没人再去跑那条一键起复，
剩下的夜里全是「看起来在跑、实际断档」。这枚把「一键起复」变成定时自动，且只启动我自己这条线的仪表。

边界（沿用今晚验过的形制）：
  · 判活只按 CommandLine 含脚本名，不认 PID、不认端口（复用 PID 认错人踩过）；
  · 绝不碰 `cmdr_night_watch_r1.py` 与任何别人的进程；
  · 收工时刻支持 `MMDD-HHMM`（要覆盖到「明天 11 点」，旧写法只认当天，过午夜就自己下班）；
  · 它自己也在 `_watch_stack_r1.py` 的覆盖表里：那一轮里按 CommandLine 认到现支就不会再起第二枚 ⇒ 不会自我增殖。

用法：SENTINEL_STOP=1004-1100 PYTHONIOENCODING=utf-8 python _stack_keeper_r1.py        （长跑，默认每 900 秒一轮）
      python _stack_keeper_r1.py --once   （跑一轮就退，给我当场验用）
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable
LOG = os.path.join(HERE, "_stack_keeper.log")
STOP = os.environ.get("STACK_KEEPER_STOP", os.environ.get("SENTINEL_STOP", "2340"))
# 10-06 17:3x 修：旧默认 "1004-1100" 同样写死了日期、早已过期。不带 env 冷启动会一起步自退（理由见代插腿那处）。
PERIOD = int(os.environ.get("STACK_KEEPER_PERIOD", "900"))
STACK = os.path.join(HERE, "_watch_stack_r1.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(s):
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(
        time.strftime("[%m-%d %H:%M:%S] ") + s + "\n")


def stop_at(stop=STOP):
    """`2335`＝今天 23:35；`1004-1100`＝10-04 11:00。"""
    if "-" in str(stop):
        md, hm = str(stop).split("-", 1)
        base = "%s-%s-%s" % (time.strftime("%Y"), md[:2], md[2:])
    else:
        base = time.strftime("%Y-%m-%d")
        hm = str(stop)
    h, m = int(hm[:2]), int(hm[2:])
    return time.mktime(time.strptime(base + " %02d:%02d:00" % (h, m), "%Y-%m-%d %H:%M:%S"))


def decide(now, stop_epoch):
    """到点就收工；否则算还剩多少分钟（预算不写死，和 keepalive 同一个判法）。"""
    left = (stop_epoch - now) / 60.0
    if left <= 0:
        return None
    return left


def run_once():
    """跑一遍栈起复，把结果原样抄进日志；认出「起了东西」就单标一行，方便下一班一眼看出断过档。"""
    # 收工时刻必须随起复一起传下去：各腿自己的默认值是「今天 23:35 / 23:40」，而 keeper 只带着 STACK_KEEPER_STOP 的话，夜里补起来的支会立刻按默认收工——看着「栈完整」，实际下一拍又空。所以这里把我这一班的 STOP 显式铺给整条链（_watch_stack 起子进程时用的是 dict(os.environ)，会再往下传一层）。
    env = dict(os.environ, SUP_STOP=STOP, SENTINEL_STOP=STOP, APPLIER_STOP=STOP,
                    PYTHONIOENCODING="utf-8")
    r = subprocess.run([PYEXE, STACK], capture_output=True, cwd=HERE, env=env)
    out = (r.stdout or b"").decode("utf-8", "replace")
    tail = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not tail or r.returncode not in (0,):
        # 「取不到数」绝不能写成「齐」——那是单向致盲的尺：它只会把断档读成正常，然后让所有人都放心。
        say(u"不可判 轮：栈脚本退 %d、输出 %d 行（%s）" % (
            r.returncode, len(tail), u"；".join(tail[-2:])[:200] if tail else u"空"))
        return False, out, r.returncode
    started = u"动作：" in out
    say(u"%s轮：%s" % (u"补起 " if started else u"齐 ", u"；".join(tail[-4:])[:400]))
    return started, out, r.returncode


def main():
    once = "--once" in sys.argv
    se = stop_at()
    left = decide(time.time(), se)
    if left is None:
        say(u"收工：已到 %s，不再起复（这一行写明原因，免得下一班以为它死了）" % STOP)
        return 0
    say(u"看门人起来：还剩 %.0f 分钟到 %s、每 %d 秒一轮（跑的是 _watch_stack_r1.py，缺才起、有就不起）"
        % (left, STOP, PERIOD))
    while True:
        run_once()
        if once:
            say(u"--once：跑完一轮就退")
            return 0
        left = decide(time.time(), se)
        if left is None:
            say(u"收工：到 %s，本进程自退；栈里剩下的会自己按预算下班" % STOP)
            return 0
        time.sleep(min(PERIOD, max(5, int(left * 60))))


if __name__ == "__main__":
    sys.exit(main())
