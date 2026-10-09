# -*- coding: utf-8 -*-
"""给包工头清收件框：把 32 条未取按「要不要你现在动」分桶，再连出处投给他。

为什么不是催一句「你去读信」：他压着的量已经大到需要有人先分好类。
而且这 32 条里有一批是哨兵自己投的报警回声（那类我已经不再新增，但存量还挂着）——
让他逐条读那些，等于替我的仪器还债。

两个模式：
  python _bb_cmdr_inbox_triage_r1.py            # 只打印读数（给 --evidence 用，中枢会真跑它）
  python _bb_cmdr_inbox_triage_r1.py --send     # 打印之后投一枚 note，并按 id 回读核对尾行
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = u"D:/moodle/agent_bus"
CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
TARGET = u"qoder:494abfd7"
ME = u"qoder:42d1a6fa"
BODYF = os.path.join(ROOT, u"_outbox_draft_triage.txt")


def buckets():
    st = json.loads(io.open(os.path.join(ROOT, "state.json"), encoding="utf-8").read())
    acks = st.get("acks", {})
    forgotten = set((st.get("forgotten") or {}).keys())
    now = time.time()
    rows = []
    with io.open(os.path.join(ROOT, "bus.jsonl"), encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except Exception:
                continue
            if str(m.get("to")) != TARGET:
                continue
            if m.get("delivered_at") or acks.get(m.get("id")):
                continue
            rows.append((m, int(now - float(m.get("ts", now))) / 60))
    b = {"echo": [], "need": [], "info": [], "dead": []}
    for m, age in rows:
        tp = str(m.get("topic", ""))
        if str(m.get("to")) in forgotten:
            b["dead"].append((m, age))
        elif str(m.get("from")) == ME and str(m.get("kind")) == "alarm" and tp.startswith("band:"):
            b["echo"].append((m, age))
        elif str(m.get("kind")) in ("deliver", "order", "ask", "ruling"):
            b["need"].append((m, age))
        else:
            b["info"].append((m, age))
    for k in b:
        b[k].sort(key=lambda x: -x[1])
    return b, len(rows)


def report():
    b, total = buckets()
    print(u"包工头未取共 %d 条，分四桶：" % total)
    for k, label in (("need", u"要他动的（交付／派单／提问／裁语）"),
                     ("info", u"看一眼就行的（通报）"),
                     ("echo", u"哨兵自己投的报警回声"),
                     ("dead", u"收件人已作废的死信")):
        lst = b[k]
        oldest = int(lst[0][1]) if lst else 0
        print(u"  %-22s %2d 条｜最老 %d 分" % (label, len(lst), oldest))
    print(u"最该先读的 3 条（按最老）：")
    for m, age in b["need"][:3]:
        print(u"  %-8s｜%4.0f 分前｜%s" % (m.get("kind"), age, str(m.get("topic", ""))[:46]))
    return b, total


def main():
    b, total = report()
    if "--send" not in sys.argv:
        return
    tail = io.open(CLOSING, encoding="utf-8").read().strip()
    # 正文刻意不带条数与分钟龄：那些在"我算"与"中枢重跑"之间一直在漂，
    # 一漂出处就对不上（第一版就是这么被拒的——正文里的分钟龄比中枢那份老了 11 分）。
    # 数交给出处那栏：那是中枢刚跑出来的现值，他重跑同一条命令能对上。
    body = (u"包工头：你收件框压着的信我按四桶分好了——真要你动的（交付／派单／提问／裁语）、"
            u"看一眼就行的通报、哨兵自己投的报警回声、收件人已作废的死信。"
            u"每桶几条、最老压了多久，都在这条消息带的那段出处里（中枢现跑），"
            u"你自己重跑一遍同一条命令就能对上。\n"
            u"其中「哨兵自己投的报警回声」那一桶可以整批跳过：那些只是「你没读我的报警」又变成新报警，"
            u"事实都在板子与哨兵日志里；这个环我今晨已经切断，改成自己投的不再算积压。\n"
            u"要动的那桶里最老的三条，出处那栏按龄排好了，从头往下读即可。\n"
            + tail)
    io.open(BODYF, "w", encoding="utf-8", newline=chr(10)).write(body)
    ev = (u"未取分桶现算|python " + os.path.join(HERE, os.path.basename(__file__)))
    cmd = [sys.executable, os.path.join(ROOT, "bus.py"), "send", "--from", ME, "--to", TARGET,
           "--kind", u"note", "--topic", u"收件框分桶-" + time.strftime("%m%d%H%M%S"),
           "--body-file", BODYF, "--evidence", ev]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.stdout.decode("utf-8", "replace")
    print(u"send rc=%d" % p.returncode)
    try:
        mid = json.loads(out).get("id", u"")
    except Exception:
        sys.exit(u"ABORT：输出不是 JSON：%s" % out[:300])
    if not mid:
        sys.exit(u"ABORT：没拿到 id：%s" % out[:300])
    got = json.loads(urllib.request.urlopen(
        u"http://127.0.0.1:4799/msg?id=" + urllib.parse.quote(mid), timeout=8)
        .read().decode("utf-8", "replace"))
    last = (got.get("body") or u"").strip().splitlines()[-1]
    print(u"回读 id=%s｜尾行逐字相同=%s｜evidence %d 段"
          % (mid, last == tail, len(got.get("evidence") or [])))
    if last != tail:
        sys.exit(u"ABORT：尾行没对上")
    os.remove(BODYF)
    print(u"TRIAGE_SENT")


HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__":
    main()
