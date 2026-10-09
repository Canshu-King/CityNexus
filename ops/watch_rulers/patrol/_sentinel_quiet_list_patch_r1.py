# -*- coding: utf-8 -*-
"""给哨兵装一张**带到期时刻**的报警抑制名单（号令者 10-04 23:3x 裁的第三条）。

裁语：「6efab655（实例 A）被平台日限额压着，它名下两格（打卡拒答屏入口定位、0520 屏侧）
等它额度恢复再催，哨兵不用重复报它。」

为什么不把这句话写进代码或我脑子：那都会变成"我记得"。写进一张带到期时刻的名单，
① 装在 hub_alarm() 这一扇唯一出口上（不是散在 K/M 各档里），漏不掉；
② 到点自动失效——明天额度恢复了它还停着，报警照旧响；
③ 每一轮抑制都在日志里留一行，不是静默消失。
读不懂到期时刻就当它不存在：宁可多报，不可漏报。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_sentinel_relay_r1.py"
Q = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_quiet_list.txt"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:40]))
        return
    s = s.replace(old, new, 1)


rep(u"def hub_alarm(band, id8, text):",
    u'''QUIET_LIST = os.path.join(HERE, u"_quiet_list.txt")


def quiet_hit(id8):
    u"""报警抑制名单：一行一枚 `id8|到期 月-日 时:分|原因`，到点自动失效。

    来源（号令者 10-04 23:3x）：6efab655 被平台日限额压着，名下两格等额度恢复再催，
    「哨兵不用重复报它」。这条如果写进代码或写进我脑子里，就成了"我记得"；写进带到期
    时刻的名单，才会自己过期——明天它额度恢复了还停着，报警照旧响。
    读不懂到期时刻 ⇒ 当它不存在：宁可多报，不可漏报。
    """
    if not os.path.isfile(QUIET_LIST):
        return None
    now = time.time()
    year = time.localtime(now).tm_year
    for ln in open(QUIET_LIST, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln or ln.startswith(u"#"):
            continue
        parts = [x.strip() for x in ln.split(u"|")]
        if len(parts) < 3 or parts[0] != id8:
            continue
        try:
            exp = time.mktime(time.strptime(u"%d-%s" % (year, parts[1]), "%Y-%m-%d %H:%M"))
        except Exception:
            say(u"抑制名单这行到期时刻读不懂（%s）⇒ 忽略它，照常报警" % parts[1])
            continue
        if now < exp:
            return parts[1], parts[2]
    return None


def hub_alarm(band, id8, text):''')

rep(u'''    topic = u"band:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    if not HUB_ON:''',
    u'''    topic = u"band:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    q = quiet_hit(id8)
    if q:
        # 留一行日志再走 skip：抑制不是"没发生"，将来对账要能看出这几轮是被名单挡下的
        say(u"抑制中（到 %s）：%s ⇒ %s 档这轮不投 alarm｜原因：%s"
            % (q[0], id8, band, q[1]))
        return ("skip", topic)
    if not HUB_ON:''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：哨兵未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)

if len(sys.argv) > 1 and sys.argv[1] == "--seed":
    io.open(Q, "w", encoding="utf-8", newline=chr(10)).write(
        u"# 报警抑制名单（哨兵 hub_alarm 每轮读它；到点自动失效，不用谁记得删）\n"
        u"# 形制：id8|到期 月-日 时:分|原因\n"
        u"# 10-04 23:3x 号令者裁：6efab655（副号令者·夜班）被平台日限额压着，"
        u"名下两格（打卡拒答屏入口定位、0520 屏侧）等额度恢复再催，哨兵不用重复报它。\n"
        u"# 到期取值守终点 10-05 11:00：那之后若仍静默，K/M 档照旧响。\n"
        u"6efab655|10-05 11:00|平台日限额压着，名下两格等额度恢复再催（号令者 10-04 裁）\n")
    print(u"名单已种一枚：6efab655 到 10-05 11:00")
print(u"哨兵已装抑制腿｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
