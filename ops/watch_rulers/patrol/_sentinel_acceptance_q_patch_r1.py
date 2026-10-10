# -*- coding: utf-8 -*-
"""把「验收队列」挂进哨兵成为 Q 档：谁交完活就停着，每轮自己算，不靠我醒着。

01:1x 实测过这一格有用：包工头压着 19 条未验收交付，但"压了多少"他自己看得见；
看不见的是**哪一扇是交完活之后停下来的**（那种停既不是懒也不是缺单，是卡在验收口）。
我手工算了一次并投了话——如果它就停在"我算过一次"，那等于没修。

三条设计：
· 算法不重写：直接跑 `_bb_cmdr_acceptance_queue_r1.py` 那份（无 --send，只取它的结论行），
  免得两处两份尺各自漂移；
· 取不到数 ⇒ 写"不可得"并记红，**绝不当绿**（单向致盲的尺也算缺陷）；
· Q 不在 actionable 的 A/E/F/G 里 ⇒ 不会因为"有人等验收"就把哨兵退场叫人，
  它走 hub_alarm 那一扇门（受抑制名单与按天幂等键管着，不刷屏）。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_sentinel_relay_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:44]))
        return
    s = s.replace(old, new, 1)


rep(u"PROJECTS_DIR = os.path.expanduser(u\"~/.qoder/projects/D--moodle\")",
    u'''ACCEPT_LEG = os.path.join(HERE, u"_bb_cmdr_acceptance_queue_r1.py")


def acceptance_stalled():
    u"""Q 档：跑验收队列那条腿，取「交完活且已静默」的扇数与名单。

    返回 (扇数, 名单串)；取不到或读不懂结论行返回 None——None 一律写"不可得"，不许当绿。
    """
    try:
        p = subprocess.run([PYEXE, ACCEPT_LEG], cwd=HERE, capture_output=True, timeout=150,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (p.stdout or b"").decode("utf-8", "replace")
        m = re.search(u"可能正等验收）：(\\\\d+) 扇：(.*)", out)
        if not m:
            say(u"Q 档读不懂那条腿的结论行 ⇒ 写不可得（rc=%d）" % p.returncode)
            return None
        n = int(m.group(1))
        return n, m.group(2).strip()
    except Exception as e:
        say(u"Q 档取数失败（%s: %s）⇒ 写不可得" % (type(e).__name__, str(e)[:70]))
        return None


PROJECTS_DIR = os.path.expanduser(u"~/.qoder/projects/D--moodle")''')

rep(u'''        gap = adoption_gap()
        if gap:
            reds.append(gap)
            summary = summary + u"｜" + gap''',
    u'''        gap = adoption_gap()
        if gap:
            reds.append(gap)
            summary = summary + u"｜" + gap
        acc = acceptance_stalled()
        if acc is None:
            summary = summary + u"｜验收队列：不可得"
            reds.append(u"Q 尺取不到验收队列（那条腿没答话）——不能当绿")
        elif acc[0]:
            summary = summary + (u"｜交完活停着等验收 %d 扇（%s）" % (acc[0], acc[1]))
            reds.append(u"有 %d 扇交完活就停着，最可能卡在验收口：%s" % (acc[0], acc[1]))
            hub_alarm(u"Q", u"acceptance",
                      u"Q 档：这几扇是**交完活之后**停下来的，不是懒也不是缺单——"
                      u"先点它们比按时间往下读更省；压龄与静默分钟在那条腿的输出里，"
                      u"重算一条：python " + ACCEPT_LEG)
        else:
            summary = summary + u"｜交完活停着等验收 0 扇"''')

rep(u'"｜P 代插腿插了块却拿不到镜像回执（远端不可证）⇒ 这一档由 _inbox_applier_r2 直接投，本腿登记口径并在板子上算进未取"',
    u'"｜P 代插腿插了块却拿不到镜像回执（远端不可证）⇒ 这一档由 _inbox_applier_r2 直接投，本腿登记口径并在板子上算进未取"\n'
    u'        "｜Q 谁交完活就停着（跑 _bb_cmdr_acceptance_queue_r1 那份算法，不重写第二把尺）；取不到写不可得"')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：哨兵未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"Q 档已挂上哨兵｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
