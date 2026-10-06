# -*- coding: utf-8 -*-
"""补上链尾那一环：让 supervise 反过来保 keeper，形成交叉监督。

01:4x 现场审计：
· `_stack_keeper_r1.py` 每 900 秒跑一次 `_watch_stack_r1.py`，保 7 个组件——**其中包括 supervise**；
· 但 `autumn_supervise_r1.py` 只数 `autumn_watch.py`，完全不看 keeper；
· 于是 keeper 是单点：它一死（应用重启、被误杀、自己异常退），整栈没人再起，
  而板子与哨兵日志会一起停更——那正是 10-04 那次 178 分钟黑窗的形状。

修法只加一条腿：supervise 每次醒（它起完 watch 后每 300 秒查一次那条非阻塞分支）
顺手数一次 keeper，不在就带 STOP 起一支。这样两边互保：任一活着都能拉起另一个。
不解决"两个同时死"（应用整体重启）——那种只能靠人或有外部触发器，交接稿里写明。

注意别把这条加进阻塞分支：supervise 起 watch 是 subprocess.call，会等几个小时，
放那儿等于整段不查。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/autumn_supervise_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


rep(u'''def main():
    say("=== 监督启动器起来''',
    u'''def keepers():
    u"""数活着的栈看护（按 CommandLine，不按 PID、不按端口）。"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                        "ForEach-Object { if ($_.CommandLine -match '_stack_keeper_r1\\\\.py') { $_.ProcessId } }"],
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
    say("=== 监督启动器起来''')

rep(u'''        live = watchers()
        if live:''',
    u'''        ensure_keeper()          # 交叉监督：放在非阻塞位置，别放进下面那段几小时的 call 里
        live = watchers()
        if live:''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"交叉监督已接上｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
