# -*- coding: utf-8 -*-
u"""结论行"不可判不算绿"那一臂的验：三扇判词读不到 ⇒ 结论**不许**是"全队都在动"。

为什么必须验：20:18 刚把不可判并进结论行。没验的话，这是一处**只改没证**的改动——
而这类改动的典型失败恰是"看着对、其实没生效"（结论行仍走旧分支）。

做法：沿用现网反证那套（只换 jget），把三扇换成 idle 过档 + unread>0，
**并把 shape_of 打成读不到判词**（模拟末态尺起不来）。三条臂都要看：
  甲 零扇过档、零不可判        ⇒ 全队都在动
  乙 三扇过档但末态是交活型    ⇒ 没人该敲；缺单的那 N 扇等包工头点
  丙 三扇过档且判词读不到      ⇒ **不可判不算绿**（本臂）
边界：只读，0 发送 0 敲门。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bb_patrol_once_r1 as P

ROWS = [{"id8": "aaaa1111", "name": u"甲", "idle_min": 60.0, "unread": 1,
         "live": "idle", "in_hub": True},
        {"id8": "bbbb2222", "name": u"乙", "idle_min": 70.0, "unread": 2,
         "live": "idle", "in_hub": True},
        {"id8": "cccc3333", "name": u"丙", "idle_min": 80.0, "unread": 1,
         "live": "idle", "in_hub": True}]
CALM = {"aaaa1111": u"**交活型停着**：末条是 text",
        "bbbb2222": u"**交活型停着**：末条是 text",
        "cccc3333": u"**交活型停着**：末条是 text"}
BLIND = u"（读不到判词：子支起不来）"
COUNTS = {"writing": 0, "idle": 3, "quiet45": 3, "quota": 0, "dropped": 0}


def run(rows, verdict):
    real_jget = P.jget
    P.jget = lambda p: ({"rows": rows, "counts": COUNTS, "at": "20:19:00", "retired_n": 0}
                        if "fleet" in str(p) else real_jget(p))
    # shape_of 是 main() 里定义的闭包，换不了 ⇒ 改它的取数口：末态尺子进程的 stdout
    real_run = P.subprocess.run

    def fake_run(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd and "tailform" in str(cmd[1]):
            class R(object):
                stdout = (u"  ⇒ %s\n" % verdict).encode("utf-8")
                stderr = b""
                returncode = 0
            return R()
        return real_run(cmd, *a, **kw)

    P.subprocess.run = fake_run
    buf = io.StringIO()
    so = sys.stdout
    sys.stdout = buf
    try:
        P.main()
    except SystemExit:
        pass
    finally:
        sys.stdout = so
        P.jget, P.subprocess.run = real_jget, real_run
    for l in buf.getvalue().splitlines():
        if l.startswith(u"②") or l.startswith(u"③"):
            print(u"   " + l[:130])
        if l.startswith(u"结论"):
            print(u"   " + l)
    return buf.getvalue()


fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


print(u"甲 零扇过档：")
out = run([dict(ROWS[0], idle_min=5.0)], CALM)
ck(u"结论：全队都在动" in out, u"甲 零扇过档却不是全队都在动")

print(u"乙 三扇过档、末态交活型：")
out = run(ROWS, CALM)
ck(u"结论：没人该敲" in out, u"乙 该落到没人该敲：\\n%s" % out)
ck(u"②b" not in out, u"乙 不该有不可判那格")

print(u"丙 三扇过档、判词读不到（本臂）：")
out = run(ROWS, BLIND)
ck(u"结论：有 3 扇末态不可判" in out, u"丙 结论行没接住不可判：\\n%s" % out)
ck(u"全队都在动" not in out, u"丙 把不可判读成了全队都在动——这正是要防的那一形")
ck(u"② 该敲" in out and u"0 扇" in out, u"丙 判词读不到却列进了该敲")

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    raise SystemExit(1)
print(u"⇒ 三臂全绿：零过档⇒全队都在动｜交活型⇒没人该敲｜判词读不到⇒不可判不算绿且不列该敲")