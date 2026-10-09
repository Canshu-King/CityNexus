# -*- coding: utf-8 -*-
"""给看板自检加三条**语义**回归锁：主人那一屏的结构不许被悄悄改回去。

为什么现在加：board.py 有两个写者（我 + codex:bbfix1），昨夜已经互相覆盖过一回。
我这几轮做的三件事——读者是主人、按收件人拆两栏、回话框搬进零块——都属于"结构"，
一旦被回退，主人早上看到的就是机器腔那一屏，而接口全绿没人报警。

三条都断状态不断措辞（换说法不算红）：
① /api/triage 必须同时给 need_human 与 need_cmdr，且两数之和等于 need；
② 页面上零块必须有四个 .tcol，且四张名单容器都在；
③ 回话输入框 #body 必须真的落在零块 #inbox 里面（搬走就红）。
"""
import ast
import io
import sys

P = u"D:/moodle/agent_bus/board_check_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0

ANCHOR = u'''    if st == 200 and u"@media (max-width:720px)" in raw and u"table-layout:fixed" in raw:'''
NEW = u'''    # ── 三条语义回归锁（10-05 00:4x）：主人那一屏的结构不许被第二个写者悄悄改回去 ──
    ts_st, ts_ct, t_raw = fetch("/api/triage")
    t_ok = ts_st == 200 and u"json" in ts_ct
    ts = json.loads(t_raw) if t_ok else {}
    tc = (ts.get("counts") or {})
    if not ts:
        red.append(u"零块结构锁取不到 /api/triage ⇒ 不能当绿")
    elif u"need_human" not in tc or u"need_cmdr" not in tc:
        red.append(u"/api/triage 少了按收件人拆分的两格（need_human／need_cmdr）"
                   u"⇒ 主人那一屏会重新被包工头该点的事塞满")
    elif tc.get(u"need_human", 0) + tc.get(u"need_cmdr", 0) != tc.get(u"need"):
        red.append(u"两栏之和对不上总欠账（%s＋%s≠%s）⇒ 拆分漏了条目"
                   % (tc.get(u"need_human"), tc.get(u"need_cmdr"), tc.get(u"need")))
    else:
        green.append(u"零块按收件人拆成两栏且对得上总账（要你定的 %s＋等包工头点的 %s＝%s）"
                     % (tc.get(u"need_human"), tc.get(u"need_cmdr"), tc.get(u"need")))
    need_ids = [u"tNeedList", u"tCmdrList", u"tNoticeList", u"tWaitList"]
    missing = [x for x in need_ids if (u'id="%s"' % x) not in raw]
    if raw.count(u'class="tcol"') < 4 or missing:
        red.append(u"零块四栏结构不全（tcol 数=%d，缺 %s）"
                   % (raw.count(u'class="tcol"'), u"、".join(missing) or u"无"))
    else:
        green.append(u"零块四栏齐全（真要你定的／等包工头点的／报你一声的／站着等活的）")
    i_body = raw.find(u'id="body"')
    i_inbox = raw.find(u'id="inbox"')
    i_next = raw.find(u"</details>", i_inbox) if i_inbox >= 0 else -1
    if i_body < 0 or i_inbox < 0 or i_next < 0 or not (i_inbox < i_body < i_next):
        red.append(u"回话输入框不在零块里（body=%s inbox=%s 块尾=%s）"
                   u"⇒ 主人看见要点的和说话的地方又隔了一屏" % (i_body, i_inbox, i_next))
    else:
        green.append(u"回话框仍在零块内部（主人看见要点的就能就地回一句）")

''' + ANCHOR

if s.count(ANCHOR) != 1:
    sys.exit(u"ABORT：锚命中 %d 次，未改动" % s.count(ANCHOR))
s = s.replace(ANCHOR, NEW, 1)

# t_raw／t_ok 由 NEW 段自己现取，这里只确认锚还在原位（不在就 ABORT，不猜位置）
if s.count(u'    ts_st, ts_ct, t_raw = fetch("/api/triage")') != 1:
    sys.exit(u'ABORT：现取那行没落在预期处，别硬改')
if u"import json" not in s:
    sys.exit(u'ABORT：这文件没 import json，用了 json 就是假绿')

ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"三条语义锁已加｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
