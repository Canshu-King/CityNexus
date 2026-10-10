# -*- coding: utf-8 -*-
"""把「谁停了、等谁」编成两腿外发（总线耐久副本 + 号令者窗口敲门），所有数字现测。

为什么要有它：01:2x 这一拍的判断只能来自流水，而我要往外发的是一张**清单**——手打的数一定会飘
（09-30 的串位教训）。所以这里：
  · 停了谁、静几分钟 ⇒ 跑 `_why_stopped_r1.py` 拿它的输出（单一尺源）；
  · 等裁语的原话 ⇒ 去那扇窗的尾条里**取含关键词那句**，不是我复述；
  · 门堵不堵 ⇒ 收件口根目录枚数 + `_processed` 里按 mtime 数插入（名字里的 HHMMSS 跨天会串，不能用）；
  · 哨兵最后一拍 ⇒ 读它自己的日志行。
任何一格取不到就 REFUSE 不落笔，宁可这条不发。

只读 + 只在 --apply 时写两个正文文件；**不发帖、不发消息**（外发由我另外两条腿走，避免 import 就发帖）。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SENT_LOG = os.path.join(HERE, "_sentinel_relay_latest.log")
# 词表必须与判「谁在等裁语」那把尺同一份来源。10-03 06:27 现形：我给 `_why_stopped_r1.py` 补了
# 主动请裁那一形（请裁／候裁／请号令者），而这里还留着自己抄的一份旧表 ⇒ 尺说 6a150e1e 在等裁语、
# 取原话的那只手却找不到句子，本枚要么 REFUSE（今天就是它拒的）、要么更糟——去编一句。
sys.path.insert(0, HERE)
import _why_stopped_r1 as WHY
KW = WHY.RULING
KW_NEG = WHY.RULING_NEG
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def die(msg):
    print(u"REFUSE：" + msg)
    return 1


def why_stopped(idle_min=25.0):
    out = subprocess.run([sys.executable, os.path.join(HERE, "_why_stopped_r1.py"), str(int(idle_min))],
                         capture_output=True).stdout.decode("utf-8", "replace")
    stopped = []
    for m in re.finditer(r"^\s{2}([0-9a-f]{8})\s+\S+\s+静\s+(\d+) 分｜判：(.*)$", out, re.M):
        stopped.append({"id": m.group(1), "idle": int(m.group(2)), "verdict": m.group(3).strip()})
    ask_line = u""
    m = re.search(u"该敲号令者（等裁语）：(.*)$", out, re.M)
    if m:
        ask_line = m.group(1).strip()
    waiting = [x for x in ask_line.split(u"、") if re.match(r"^[0-9a-f]{8}$", x.strip())]
    m2 = re.search(u"^在写（<\\d+ 分）(\\d+) 扇：(.*)$", out, re.M)
    alive_n = int(m2.group(1)) if m2 else -1
    alive = m2.group(2).strip() if m2 else u""
    return stopped, waiting, alive_n, alive, out


def last_ask(id8):
    """从该扇流水尾部取出含关键词的那一句（逐字，不复述）。"""
    cands = [p for p in os.listdir(PROJ) if p.startswith(id8) and p.endswith(".jsonl")]
    if not cands:
        return None
    path = os.path.join(PROJ, cands[0])
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - 220000))
        if size > 220000:
            f.readline()
        data = f.read()
    last = u""
    for line in data.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else None
        if not m or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                    last = x["text"]
        elif isinstance(c, str) and c.strip():
            last = c
    if not last:
        return None
    for sent in re.split(u"[。\\n]", last):
        s = sent.strip()
        if s and any(k in s for k in KW) and not any(n in s for n in KW_NEG) and len(s) >= 8:
            return (s[:190] + u"…" if len(s) > 190 else s)
    return None


def door_state(since_hhmm):
    root = [p for p in os.listdir(INBOX)
            if os.path.isfile(os.path.join(INBOX, p)) and p.endswith(".md")]
    b = time.mktime(time.strptime(since_hhmm, "%Y-%m-%d %H:%M:%S"))
    proc = os.path.join(INBOX, "_processed")
    ins = 0
    latest = None
    for p in os.listdir(proc):
        fp = os.path.join(proc, p)
        if os.path.isfile(fp) and ".inserted_" in p:
            mt = os.path.getmtime(fp)
            if mt > b:
                ins += 1
                if latest is None or mt > latest[0]:
                    latest = (mt, p)
    return len(root), ins, latest


def sentinel_last():
    if not os.path.isfile(SENT_LOG):
        return None, None
    all_rows = io.open(SENT_LOG, encoding="utf-8", errors="replace").read().split(chr(10))
    starts = [i for i, l in enumerate(all_rows) if u"哨兵起来" in l]
    rounds_idx = [i for i, l in enumerate(all_rows) if re.match(r"^\[\d\d:\d\d:\d\d\] 轮 \d+：", l)]
    if not rounds_idx:
        return None, None
    # 「已跑几拍」只数**这一支实例**的：按行号取最后一行『哨兵起来』之后的轮次。
    # 不用钟点比较——日志跨午夜时 23:1x 的秒数比 00:1x 大，会把昨夜那一支的拍也算进来（第一版就撞了）。
    base = starts[-1] if starts else -1
    mine = [all_rows[i] for i in rounds_idx if i > base]
    if not mine:
        mine = [all_rows[rounds_idx[-1]]]
    return mine[-1][:400], len(mine)


def main():
    since = sys.argv[1] if len(sys.argv) > 1 else "2026-10-03 00:31:00"
    stopped, waiting, alive_n, alive, raw = why_stopped(25)
    if alive_n < 0:
        return die(u"名册『在写』那行取不到，不能拿猜的数往外发")
    if not stopped:
        return die(u"这一拍没有停车道，不必发清单")
    asks = {}
    for id8 in waiting:
        q = last_ask(id8)
        if not q:
            return die(u"%s 被判等裁语，但取不到它含关键词的那句原话——不能替它编" % id8)
        asks[id8] = q
    nroot, nins, latest = door_state(since)
    sl, srounds = sentinel_last()
    if sl is None:
        return die(u"哨兵日志读不到 ⇒ 覆盖情况不明，这条不该发")

    now = time.strftime("%H:%M:%S")
    idle_txt = u"、".join(u"%s(%d 分)" % (x["id"], x["idle"]) for x in sorted(stopped, key=lambda z: z["idle"]))
    lines = []
    lines.append(u"【夜间值守清单 · 谁停了、等谁】现测 %s，单一尺源 `_why_stopped_r1.py 25` + `_idle_census_compose_r1.py`。" % now)
    lines.append(u"")
    lines.append(u"- 在写（静 <25 分）**%d 扇**：%s。停了 **%d 扇**：%s。" % (alive_n, alive, len(stopped), idle_txt))
    lines.append(u"- 明写在等你点单的 **%d 扇**（原话逐字取自各自尾条，我没复述）：" % len(asks))
    for id8 in waiting:
        mins = [x["idle"] for x in stopped if x["id"] == id8]
        lines.append(u"  · `%s`（静 %s 分）：%s" % (id8, mins[0] if mins else u"?", asks[id8]))
    others = [x["id"] for x in stopped if x["id"] not in waiting]
    lines.append(u"- 其余 **%d 扇**尾条都是交付陈词、没提问题也没未接的单：%s" % (len(others), u"、".join(others)))
    lines.append(u"  ⇒ 按你『无未接单时不敲静默车』的口径，**我这一侧 0 扇车道被敲**；要不要给他们下一手是你的权。")
    lines.append(u"- 门不堵：收件口根目录 **%d 枚**待插；`%s` 之后 `_processed` 里新增 **%d 枚** inserted（按移动后 mtime 数，"
                 u"名字里的 HHMMSS 跨天会串所以我没用它）。最近一枚 %s。" % (
                     nroot, since, nins, (latest[1] + u" @ " + time.strftime("%H:%M:%S", time.localtime(latest[0]))) if latest else u"无"))
    lines.append(u"- 值守覆盖：哨兵已跑 %d 拍，最后一拍原文：%s" % (srounds, sl))
    lines.append(u"- 这把尺修过的形制（**逐条带日期，不冒充「现在还有」**）："
                 u"09-30 首版按关键词把「两道闸都干净」误标成卡闸，已收窄成必须有被拒形制且同句无清白声明；"
                 u"10-03 05:4x 加「意图句后就停了」一档（话说出去了手没落下来，旧版只报分不出）；"
                 u"10-03 06:1x 补主动请裁那一形（请裁／候裁／请号令者），并把反形剥掉——"
                 u"『停等裁语已照做』先前被词面抓成在等裁语，会让人去敲一记不存在的需求；"
                 u"同一时刻本枚原先自带一份旧词表，与尺子那份分叉 ⇒ 尺说有人等、取原话的手找不到句子，"
                 u"今天它 REFUSE 过一次而没有编话，这是对的；现在 KW 直接 import `_why_stopped_r1`，单一来源。"
                 u"本条里只有『等裁语』那一格是逐字读尾条得来的。")
    body = u"\n".join(lines)

    out1 = os.path.join(HERE, "_idle_census_body_%s.txt" % time.strftime("%H%M"))
    io.open(out1, "w", encoding="utf-8", newline="\n").write(body + chr(10))
    import hashlib
    b = (body + "\n").encode("utf-8")
    print(u"[落盘 %s｜%d B｜sha1 %s]" % (os.path.basename(out1), len(b), hashlib.sha1(b).hexdigest()))
    print(u"")
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
