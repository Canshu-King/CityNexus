# -*- coding: utf-8 -*-
"""把 supervise 从"阻塞等一支跑完"改成"周期巡检，缺谁起谁"——否则交叉监督是假的。

01:4x 端到端负对照当场抓出来：
· 我给 supervise 加了 ensure_keeper()，放在主循环顶部；
· 但主循环紧接着是 `subprocess.call(autumn_watch.py 30 600)`——那是 **5 小时阻塞**；
· 日志为证：01:43:19 起来、01:43:21 起第 1 支，之后我杀掉 keeper，
  340 秒后再查：keeper 没回来。supervise 活着，却正卡在 call 里，一次都不会再查。
也就是说：加了函数 ≠ 加了腿。放错位置的守护代码比没有更骗人。

改法：主循环改成每 300 秒醒一次，醒来做三件事——查 keeper、查自动轮、缺哪个补哪个；
watch 用 Popen 起、用 poll() 收 rc，不再阻塞等它跑完。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/autumn_supervise_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0

OLD_LOOP = u'''    n = 0
    while True:
        if time.time() >= stop_today():
            say("到 STOP=%s，监督主动收工；此后没有自动轮，需要就再跑一次本脚本。" % STOP)
            return 0
        ensure_keeper()          # 交叉监督：放在非阻塞位置，别放进下面那段几小时的 call 里
        live = watchers()
        if live:
            say("现成有自动轮在跑（%d 条进程行：%s），这一轮不起，300 秒后再查" % (len(live), ",".join(live[:4])))
            time.sleep(300)
            continue
        n += 1
        say("起第 %d 支：autumn_watch.py %s %s" % (n, ROUNDS, GAP))
        t0 = time.time()
        with io.open(os.path.join(HERE, "autumn_watch.log"), "a", encoding="utf-8", errors="replace") as lg:
            rc = subprocess.call([PYEXE, os.path.join(HERE, "autumn_watch.py"), ROUNDS, GAP],
                                 stdout=lg, stderr=subprocess.STDOUT, cwd=HERE)
        dur = (time.time() - t0) / 60.0
        say("第 %d 支退出 rc=%s，跑了 %.1f 分钟（rc=2 是单实例锁拒绝双开，等一拍再试）" % (n, rc, dur))
        time.sleep(120 if rc == 2 else 30)'''

NEW_LOOP = u'''    n = 0
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
        time.sleep(TICK_S)'''

if s.count(OLD_LOOP) != 1:
    sys.exit(u"ABORT：主循环锚命中 %d 次，未改动" % s.count(OLD_LOOP))
s = s.replace(OLD_LOOP, NEW_LOOP, 1)

old_tick = u'GAP = os.environ.get("SUP_GAP", "600")'
new_tick = (u'GAP = os.environ.get("SUP_GAP", "600")\n'
            u'TICK_S = int(os.environ.get("SUP_TICK_S", "300"))   # 本监督自己的巡检节拍（秒）')
if s.count(old_tick) != 1:
    sys.exit(u"ABORT：节拍锚命中 %d 次" % s.count(old_tick))
s = s.replace(old_tick, new_tick, 1)
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"主循环已改成非阻塞巡检｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
