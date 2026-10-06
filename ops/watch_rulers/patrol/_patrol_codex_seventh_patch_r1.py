# -*- coding: utf-8 -*-
"""给巡逻加第⑦格：Codex 那侧的活跃度与失败成因（并入同一条命令，覆盖值守盲区）。

01:5x 现读：Codex 的 thread_history 近 6 小时只有 4 轮完成 + 2 轮失败（其中一枚是额度/限流），
也就是说**它这一夜基本停着**。而 `_bb_patrol_once_r1.py` 前六格全部来自 Qoder 侧流水与那块板，
Codex 停多久都不会在巡逻里露头——这是值守的覆盖缺口，不是 Codex 的问题。

三条约束：
· 只读打开（mode=ro）并设短 timeout：那库 567 MB 且 Codex 正在写，绝不抢锁；
· 读不到就写「不可得」，绝不当绿（单向致盲的尺也算仪器缺陷）；
· 与 BB 机名册并排打印，但**不去猜映射**：codex 的 thread_id 与 BB 机 id 之间没有对照表。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_bb_patrol_once_r1.py"
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
    fleet = jget(BOARD + u"/api/fleet")''',
    u'''CODEX_DB = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")


def codex_side(hours=6.0):
    u"""第⑦格：Codex 那侧近 N 小时的轮次与失败成因。读不到返回 None（写不可得，不当绿）。"""
    try:
        import sqlite3
        import re as _re
        if not os.path.isfile(CODEX_DB):
            return None
        con = sqlite3.connect(u"file:%s?mode=ro" % CODEX_DB, uri=True, timeout=8)
        try:
            cur = con.cursor()
            cut = time.time() - hours * 3600
            st = dict(cur.execute(
                u"select status, count(*) from thread_turns"
                u" where coalesce(completed_at, started_at) >= ? group by status", (cut,)).fetchall())
            errs = [r[0] for r in cur.execute(
                u"select error_json from thread_turns"
                u" where status in ('failed','interrupted') and coalesce(completed_at, started_at) >= ?", (cut,))]
            act = cur.execute(
                u"select count(distinct thread_id) from thread_turns"
                u" where coalesce(completed_at, started_at) >= ?", (time.time() - 5400,)).fetchone()[0]
        finally:
            con.close()
        def cls(e):
            s_ = e or u""
            for pat, name in ((u"usageLimit|daily usage|rate limit", u"额度/限流"),
                              (u"network|Connection|timeout|reset", u"网络"),
                              (u"auth|token|401|403", u"鉴权")):
                if _re.search(pat, s_, _re.I):
                    return name
            return u"其他"
        from collections import Counter
        return {"states": st, "bad_causes": Counter(cls(e) for e in errs).most_common(),
                "bad": len(errs), "active_threads_90m": act}
    except Exception as e:
        say_note(u"⑦ Codex 侧读不动（%s: %s）⇒ 写不可得，不当绿" % (type(e).__name__, str(e)[:60]))
        return None


def say_note(x):
    io.open(os.path.join(HERE, u"_patrol_notes.log"), "a", encoding="utf-8", newline=chr(10)
            ).write(time.strftime("[%m-%d %H:%M:%S] ") + x + chr(10))


def main():
    fleet = jget(BOARD + u"/api/fleet")''')

rep(u'''    print(u"结论：%s" % (u"有扇该敲" if knock else''',
    u'''    cx = codex_side()
    if cx is None:
        print(u"⑦ Codex 侧：不可得（读不动那座库或文件不在）⇒ 这一格不许当绿")
    else:
        print(u"⑦ Codex 侧｜近 90 分活跃 thread %d 条｜近 6 小时轮次 %s｜失败或中断 %d 轮（成因 %s）"
              % (cx["active_threads_90m"], cx["states"] or u"无", cx["bad"],
                 u"、".join(u"%s×%d" % kv for kv in cx["bad_causes"]) or u"无"))
        print(u"   名册里 codex 身份 %d 枚：%s｜两侧对不上就不猜，要接得主人或包工头点名"
              % (len([a for a in st if a.startswith(u"codex:")]),
                 u"、".join(a for a in st if a.startswith(u"codex:")) or u"无"))

    print(u"结论：%s" % (u"有扇该敲" if knock else''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：%d 条没落上，未改动" % len(miss))
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"第⑦格已并入巡逻｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
