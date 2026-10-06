# -*- coding: utf-8 -*-
u"""第⑦格加一格「Codex 身份指纹」：从 thread_items 首条 userMessage 里抽自称，代替人肉猜。

为什么（20:23 实测三步）：
  ① `~/.codex/thread_history_1.sqlite` 的表只有 thread_turns／thread_items／…，**没有标题列**；
     所以两侧对不上不是我没找，是库里真没有现成的互指字段。
  ② 但 `thread_items.item_json` 的**首条 userMessage** 自报身份。实测那条近 90 分活跃的
     thread（01a10cd0…）首条不是普通用户消息，而是一次 `create_thread` 的输出，
     里面有 `<source_thread_id>01a0c796-…` —— 它是**派生**出来的子窗。
  ③ 顺着 source_thread_id 读父窗首条 userMessage，真文本是
     **「You are CityNexus Codex Window R」**（父窗 23 轮，起 10-05）。
     这才是能与 BB 机身份互指的东西：窗名 "R"。

所以第⑦格现在能报的是「Codex 窗名 R（父 01a0c796 派生子窗 01a10cd0）」，
而不是一句「两侧对不上就不猜」。**仍然不猜**：BB 机名册里没有 "R" 这一条，
所以缺口照旧报缺口——但现在人看一眼就能认出这是哪扇窗，不必再翻库。

边界：只读 sqlite（mode=ro），0 写入、0 发送、0 敲门。
用法：python _codex_window_id_r1.py [thread_id…]     不给参数＝只报近 90 分活跃的那些
"""
import json
import os
import re
import sqlite3
import sys
import time

DB = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")
SRC_RE = re.compile(r"<source_thread_id>([0-9a-f-]{36})</source_thread_id>")
NAME_RE = re.compile(r"You are ([A-Za-z0-9 _\-]{2,60}?)(?:\\n|\.|\r|$)")


def q(con, sql, args=()):
    cur = con.cursor()
    return cur.execute(sql, args).fetchall()


def first_text(con, tid):
    u"""该 thread 头若干条 userMessage / functionCallOutput 里找身份句。

    20:23 踩到的坑：只取**第一条** userMessage 拿到的是 `"continue\\n"`——
    真正的身份句（`You are CityNexus Codex Window R` 与 `source_thread_id`）
    在更靠后的位置：子窗的第一条 userMessage 只是"继续"，身份包在**上一次
    `create_thread` 的 functionCallOutput** 里（那是父窗写给子窗的委派书）。
    所以这里扫头 12 条，取第一条命中身份正则的文本，而不是"第一条"。
    """
    rows = q(con, "select item_type, item_json from thread_items where thread_id=?"
                 " order by rollout_ordinal limit 12", (tid,))
    texts = []
    for _t, raw in rows:
        try:
            j = json.loads(raw)
        except Exception:
            continue
        c = j.get("content")
        if isinstance(c, list):
            texts.append(u"\\n".join(b.get("text", u"") for b in c if isinstance(b, dict)))
        elif isinstance(c, str):
            texts.append(c)
        for k in ("output", "text"):
            if isinstance(j.get(k), str):
                texts.append(j[k])
    return u"\\n".join(t for t in texts if t)


def fingerprint(con, tid):
    u"""→ (窗名, 父 id, 证据那一句)。窗名取不到就是空串，不拿别的东西冒充。"""
    txt = first_text(con, tid)
    m_src = SRC_RE.search(txt)
    parent = m_src.group(1) if m_src else u""
    # 子窗首条里没有自称，去父窗找
    for src in (txt, first_text(con, parent) if parent else u""):
        m = NAME_RE.search(src.replace("\\r\\n", "\\n"))
        if m:
            return m.group(1).strip(), parent, m.group(0)[:80]
    return u"", parent, (txt[:80] if txt else u"（首条读不到）")


def main():
    if not os.path.isfile(DB):
        print(u"REFUSE：%s 不在，不报身份" % DB)
        return 1
    con = sqlite3.connect(u"file:%s?mode=ro" % DB, uri=True, timeout=8)
    try:
        if len(sys.argv) > 1:
            tids = sys.argv[1:]
        else:
            cut = time.time() - 5400
            tids = [r[0] for r in q(con, "select distinct thread_id from thread_turns"
                                        " where coalesce(completed_at,started_at)>=?", (cut,))]
        if not tids:
            print(u"近 90 分没有活跃 thread")
            return 0
        print(u"现读 %s｜近 90 分活跃 thread %d 条" % (time.strftime("%H:%M:%S"), len(tids)))
        for tid in tids:
            name, parent, ev = fingerprint(con, tid)
            print(u"  %s" % tid)
            print(u"    自报窗名：%s" % (name or u"**读不到**（不拿父 id 或目录冒充窗名）"))
            print(u"    派生自　：%s" % (parent or u"不是子窗（或首条里没有 source_thread_id）"))
            print(u"    证据句　：%s" % ev)
        print()
        print(u"⇒ 这些是可互指的**窗名**；BB 机名册里若有同名身份即可对上，")
        print(u"  没有就仍算缺口——**我不据此猜身份**（猜错＝给不相干的会话装身份）。")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())