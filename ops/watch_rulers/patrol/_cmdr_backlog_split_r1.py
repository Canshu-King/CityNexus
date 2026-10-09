# -*- coding: utf-8 -*-
u"""把号令者名下「已送未拆」那一大摞拆成两类，让他一次动作能清掉一摞：

  甲类：这条 deliver 说的块**已经在账本里**（按块头标题现读命中）⇒ 不用再读全文，
        要么 ack 要么具名作废，一次点一堆；
  乙类：账本里找不到 ⇒ 才是真要他动脑子的那几件。

为什么做这个（10-06 03:3x 现读）：号令者名下未拆 119 条，第④格报的"22 条"是**没取走**的那一类，
两把尺常被混读成一把；不拆的话"验收口积压"这句话没法动手。
边界：只读 bus.jsonl / state.json / 账本，0 次写、0 次上总线、0 次 ack（ack 的含义归号令者裁）。

跑法：PYTHONIOENCODING=utf-8 python _cmdr_backlog_split_r1.py [--to qoder:494abfd7]
"""
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "agent_bus"))
LEDGER = os.path.normpath(os.path.join(HERE, "..", "..", "..", "CITYNEXUS_AGENT_CONTROL.md"))
KINDS = (u"deliver", u"order", u"ask", u"ruling")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def norm(s):
    # 只留汉字/数字/字母：块头常被"·｜（）"和空格改动措辞，逐字比必假阴性
    return u"".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", (s or u"")[:60]))


def main():
    to = u"qoder:494abfd7"
    if u"--to" in sys.argv:
        to = sys.argv[sys.argv.index(u"--to") + 1]
    st = json.load(io.open(os.path.join(BUS, "state.json"), encoding="utf-8"))
    acks = st.get("acks", {})
    rows = [json.loads(l) for l in io.open(os.path.join(BUS, "bus.jsonl"),
                                           encoding="utf-8", errors="replace") if l.strip()]
    now = time.time()
    pend = [m for m in rows if str(m.get("kind")) in KINDS and m.get("to") == to
            and m.get("delivered_at") and not acks.get(m.get("id"))]
    led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    nled = norm(led)
    # 账本行号要现读，不能只说"在"：拿命中处的行首往前数
    lines = led.split(u"\n")
    norms = [norm(x) for x in lines]

    jia, yi = [], []
    # 第二条腿：代插落件后会在 _processed/ 留 `<lane>_<HHMM>.md.inserted_<HHMMSS>` 的回执，
    # 而很多 deliver 的 topic 里就带着那枚块名（形如 6efab655_2130）。只按标题子串比会漏掉这一大类
    # ——第一版实测甲类只有 10 条，而同一时刻 _processed 里当天的回执远不止这个数。
    PROC = os.path.join(os.path.dirname(BUS), u"_qoder_ledger_inbox", u"_processed")
    receipts = {}
    try:
        for fn in os.listdir(PROC):
            g = re.match(r"([0-9a-f]{8}_\d{4})", fn)
            if g:
                receipts.setdefault(g.group(1), fn)
    except Exception:
        pass
    STAMP = re.compile(r"([0-9a-f]{8}_\d{4})")

    for m in pend:
        # 块头优先从 body 的 `### ` 行取（交付件的形制），取不到再退回 topic
        cand = []
        body = m.get("body") or u""
        for ln in body.split(u"\n"):
            if ln.strip().startswith(u"###"):
                cand.append(norm(ln))
        cand.append(norm(m.get("topic")))
        hit = None
        for c in cand:
            if len(c) < 8:
                continue
            for idx, nl in enumerate(norms):
                if c in nl:
                    hit = idx + 1
                    break
            if hit:
                break
        stamp = None
        if not hit:
            for s in STAMP.findall((m.get("topic") or u"") + u" " + body):
                if s in receipts:
                    # 命中只算「数」不够——回执文件名是 `<块名>.md.inserted_<HHMMSS>`，
                    # 拿 `<块名>.md` 去收件口找必然读不到（我 03:3x 就这么误判过一次「50 枚全读不到」）。
                    # 这里现读回执本体里的块头，再回数一遍账本；对不上就不给进甲类。
                    fn = receipts[s]
                    rp = os.path.join(PROC, fn)
                    head = u""
                    try:
                        head = next((l for l in io.open(rp, encoding="utf-8", errors="replace")
                                     .read().split(u"\n") if l.strip()), u"")
                    except Exception:
                        head = u""
                    key = norm(head)
                    if not key or len(key) < 8 or sum(1 for nl in norms if key in nl) < 1:
                        continue
                    stamp, hit = u"%s｜块头现读账本有" % s, -1
                    break
        rec = (m.get("id"), str(m.get("kind")), int((now - float(m.get("ts") or now)) / 60.0),
               (m.get("topic") or u"")[:60], hit, stamp)
        (jia if hit else yi).append(rec)

    n_title = sum(1 for x in jia if x[4] and x[4] > 0)
    n_rcpt = sum(1 for x in jia if x[4] == -1)
    print(u"收件人 %s｜已送未拆 %d 条（现读 %s）｜取数口 bus.jsonl＋state.json＋账本＋_processed 回执"
          % (to, len(pend), time.strftime("%H:%M:%S")))
    print(u"甲类 %d 条（交付物已在账本：按块头命中 %d 条、按 _processed 代插回执命中 %d 条）"
          u"⇒ 不用再读全文，逐条 ack 或具名作废：" % (len(jia), n_title, n_rcpt))
    for mid, k, age, topic, ln, stamp in sorted(jia, key=lambda x: -x[2])[:40]:
        where = (u"账本第 %s 行" % ln) if ln and ln > 0 else (u"回执 %s" % stamp)
        print(u"   %-14s %-7s 压%5d 分｜%s｜%s" % (mid, k, age, where, topic))
    if len(jia) > 40:
        print(u"   （其余 %d 条同形制，未列出）" % (len(jia) - 40))
    print(u"乙类 %d 条（块头与回执都对不上）⇒ 真要动脑子的那几件，按发件方归堆：" % len(yi))

    fr = {}
    for m in pend:
        fr[m.get("id")] = str(m.get("from") or u"?")
    grp = {}
    for rec in yi:
        grp.setdefault(fr.get(rec[0], u"?"), []).append(rec)
    for f, lst in sorted(grp.items(), key=lambda x: -len(x[1])):
        print(u"   %-22s %d 条｜最老 %d 分" % (f, len(lst), max(x[2] for x in lst)))
    for rec in sorted(yi, key=lambda x: -x[2])[:25]:
        mid, k, age, topic, ln, stamp = rec
        print(u"   %-14s %-7s 压%5d 分｜%s｜发件 %s" % (mid, k, age, topic, fr.get(mid, u"?")))
    if len(yi) > 25:
        print(u"   （其余 %d 条同形制，未列出）" % (len(yi) - 25))
    print(u"边界：只读；0 次 ack、0 次写账本、0 次上总线。"
          u"甲类的「命中」是按规范化标题子串比的（措辞小改不致假阴性），仍可能与另一块同名撞车 ⇒ "
          u"要点单前先 cat 那一行确认。")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
