# -*- coding: utf-8 -*-
"""`_watch_stack_r1.py` 的合成自测：证它「缺才起、有就不起、--check 绝不动手」。

为什么必须自测：这枚是重启后的唯一恢复入口。它若会重复起支，一夜起来两三套 watch，
就会互相抢着上总线（10-01 的重复投递就是这么来的）；它若把在跑的判断成没跑，就等于没有入口。
这里全程喂合成进程表，不碰真进程；真机上只另跑一次 `--check` 看它不误起。
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _watch_stack_r1 as W

res = []


def check(name, got, want):
    ok = want in str(got)
    res.append(ok)
    print(u"%-52s %s" % (name, u"对" if ok else u"错（实读：%s｜期望含：%s）" % (str(got)[:160], want)))
    return ok


def run(argv, rows_map, sleep=False):
    calls = []
    W.start = lambda name, script, log: (calls.append((name, script)), 41000 + len(calls))[1]
    W.ps_rows = lambda: list(rows_map)
    real_sleep = time.sleep
    if not sleep:
        time.sleep = lambda s: None
    try:
        sys.argv = ["_watch_stack_r1.py"] + argv
        buf = io.StringIO()
        old = sys.stdout
        class Tee:
            def write(self, s):
                buf.write(s); return len(s)
            def flush(self):
                pass
        sys.stdout = Tee()
        try:
            W.main()
        finally:
            sys.stdout = old
            time.sleep = real_sleep
        return buf.getvalue(), calls
    finally:
        time.sleep = real_sleep


FULL = [("33776", "python.exe autumn_supervise_r1.py"),
        ("35360", "python.exe autumn_watch.py 40 600"),
        ("32612", "python.exe _sentinel_keepalive_r1.py"),
        ("48980", "python.exe _sentinel_relay_r1.py 1265 900"),
        ("35888", "python.exe _night_verdict_runner_r1.py"),
        # 真机上中枢就是这一形：`python bus_hub.py`（相对名＋cwd 在 agent_bus）。
        # 登记表里我写的是绝对路径 ⇒ 这一行同时是「判活按脚本名、不按登记路径」的反证。
        ("36001", "python.exe bus_hub.py"),
        ("36010", "python.exe _stack_keeper_r1.py")]
HALF = [("33776", "python.exe autumn_supervise_r1.py"),
        ("35360", "python.exe autumn_watch.py 40 600")]
NONE = [("1", "python.exe something_else.py"), ("ProcessId", "CommandLine")]     # 表头混进来也要不被当活

o, c = run(["--check"], HALF)
check("--check 缺支时也不起任何东西", str(len(c)) + u"（" + o[:0], "0")
check("--check 要指出缺的那支", o, u"keepalive **缺**")
o, c = run([], FULL)
check("五支根都在（含 BB 机中枢与看门人）⇒ 0 次启动", str(len(c)), "0")
check("五支根都在 ⇒ 报栈完整", o, u"栈完整")
check("中枢按脚本名判活得到（登记写的是绝对路径）", o, u"bus_hub 已在")
check("看门人也在覆盖表里（它掉了，这一夜的自动起复就断档）", o, u"keeper 已在")
o, c = run([], HALF)
check("缺 keepalive、取数器、中枢与看门人 ⇒ 正好起这 4 支（不误起别的）", str(len(c)), "4")
check("起的必须是 keepalive 本体", str(c), "_sentinel_keepalive_r1.py")
check("23:00 取数器也在补起之列", str(c), "_night_verdict_runner_r1.py")
check("第五轮重启起来时 BB 机中枢必须被拉回（它不在就没人吸收 drop/）", str(c), "bus_hub.py")
check("不许顺手替 keepalive 起哨兵（子支归父支）", str(len([x for x in c if x[0] == "sentinel"])), "0")
o, c = run([], NONE)
check("全空 ⇒ 起 5 支（supervise + keepalive + 取数器 + 中枢 + 看门人）", str(len(c)), "5")
check("CSV 表头那行不许被当成在跑的进程", str(len(c)), "5")
check("全空时子支要说还没起来由父支带", o, u"父支下一拍会带起")
check("绝对路径组件解析后仍在 agent_bus（cwd 归脚本自己那目录）",
      os.path.dirname(W.resolve(u"D:/moodle/agent_bus/bus_hub.py")), "agent_bus")
print("PASS %d/%d" % (sum(1 for x in res if x), len(res)))
if not all(res):
    print(u"FAIL：%d 条不符——这枚恢复入口不可信，别把它当兜底" % (len(res) - sum(1 for x in res)))
sys.exit(0 if all(res) else 1)
