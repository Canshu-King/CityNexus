# -*- coding: utf-8 -*-
"""给哨兵补 O 档：推广缺口——流水在动、却从没接 BB 机的会话。

为什么 L 档不够（23:5x 实测）：L 档报的是「板子上看得见、但没接 BB 机」的窗口。
而我刚拿项目目录的会话流水比对名册，抓到 4 枚既不在板子上、也不在名册里的会话——
它们在板子两桶分母（360 分／720 分）之外，L 档根本看不见。缺口恰恰长在这种地方。

阈值取「近 30 分钟动过流水」：只盯**正在干活却没接入**的，不把两三天前的旧窗口当缺口
（那 4 枚实测是 64–70 小时前的，本来就不该敲门）。取不到名册时写「不可得」，
绝不当绿——单向致盲的尺也算仪器缺陷。
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


rep(u"def hub_alarm(band, id8, text):",
    u'''PROJECTS_DIR = os.path.expanduser(u"~/.qoder/projects/D--moodle")
HUB_URL = u"http://127.0.0.1:4799"
ADOPT_RECENT_MIN = 30.0


def adoption_gap():
    u"""O 档：会话流水近 30 分钟在动，却不在 BB 机名册里 ⇒ 推广缺口。

    目标里那句「给其他会话推广你制作的通讯软件」不该靠我记得去敲：这一档每轮自己比，
    比出来就走 hub_alarm 那一扇门（因此同样受抑制名单与按天幂等键管着，不会刷屏）。
    """
    try:
        import urllib.request
        st = json.loads(urllib.request.urlopen(HUB_URL + u"/agents", timeout=8)
                        .read().decode("utf-8", "replace"))
    except Exception as e:
        say(u"O 档取不到 BB 机名册（%s）⇒ 这格写不可得，不当绿" % e)
        return u"推广缺口：不可得（BB 机名册没答话）"
    on = set()
    for aid in st:
        on.add(str(aid).split(u":")[-1][:8].lower())
    cut = time.time() - ADOPT_RECENT_MIN * 60
    try:
        names = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(u".jsonl")]
    except Exception as e:
        say(u"O 档读不到会话目录（%s）⇒ 这格写不可得" % e)
        return u"推广缺口：不可得（项目会话目录读不到）"
    gaps = []
    for f in names:
        path = os.path.join(PROJECTS_DIR, f)
        try:
            mt = os.path.getmtime(path)
        except Exception:
            continue
        if mt < cut:
            continue
        key = f.split(u"-")[0][:8].lower()
        if key not in on:
            gaps.append((key, int((time.time() - mt) / 60)))
    if not gaps:
        return None
    gaps.sort(key=lambda x: x[1])
    text = (u"O 档：有 %d 枚会话流水近半小时在动、却不在 BB 机名册里（%s）。"
            u"这一格的动作是递一页纸 JOIN.txt，不是替它们注册——身份要它自己认领才算自证。"
            % (len(gaps), u"、".join(u"%s 静 %d 分" % (k, m) for k, m in gaps[:6])))
    say(u"O 档推广缺口 %d 枚：%s" % (len(gaps), u"、".join(k for k, _ in gaps[:6])))
    hub_alarm(u"O", u"sessions", text)
    return u"推广缺口 %d 枚（近 30 分钟在动却没接 BB 机）" % len(gaps)


def hub_alarm(band, id8, text):''')

rep(u'''        save_gdone(g_done)
        say("轮 %d：%s｜%s" % (rounds, summary, "红" if reds else "绿"))''',
    u'''        save_gdone(g_done)
        # O 档挂在主循环而不是 pass_once 的返回值链上：它只加一条红因，
        # 且 O 不在 actionable 的 A/E/F/G 里 ⇒ 不会因为"有人没接入"就早退叫人。
        gap = adoption_gap()
        if gap:
            reds.append(gap)
            summary = summary + u"｜" + gap
        say("轮 %d：%s｜%s" % (rounds, summary, "红" if reds else "绿"))''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：哨兵未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"O 档已装｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
