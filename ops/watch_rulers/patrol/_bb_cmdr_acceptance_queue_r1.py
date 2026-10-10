# -*- coding: utf-8 -*-
"""验收队列：谁交了活、交完是不是就停了——给包工头一条带因果的传话，不是又一条泛报警。

为什么要它（01:1x 现算）：包工头压着 19 条 deliver 未验收，最老 156 分。
但"压了多少条"他自己看得见，看不见的是**哪一扇因为等验收而停了**——
车道交完一件通常等一句裁语才开下一件，这种停不是懒，也不是缺单，是卡在验收口。

算法就一句：把"未验收的 deliver 发件人"与板子上该扇的当前状态并起来，
凡「交了活 + 现在已静默」的单列出来。其余仍在写的，压着多久都不算卡。

两个模式：
  python _bb_cmdr_acceptance_queue_r1.py          # 只打印（也当 --evidence 用，中枢会真跑它）
  python _bb_cmdr_acceptance_queue_r1.py --send   # 打印后投一枚 note 给号令者
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
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
CMDR = u"qoder:494abfd7"
ME = u"qoder:42d1a6fa"
BODYF = os.path.join(ROOT, u"_outbox_draft_acceptance.txt")
STALL_MIN = 25.0


def compute():
    st = json.loads(io.open(os.path.join(ROOT, "state.json"), encoding="utf-8").read())
    acks = st.get("acks", {})
    now = time.time()
    pend = {}
    for ln in io.open(os.path.join(ROOT, "bus.jsonl"), encoding="utf-8", errors="replace"):
        try:
            m = json.loads(ln)
        except Exception:
            continue
        if str(m.get("to")) != CMDR or str(m.get("kind")) != "deliver":
            continue
        if m.get("delivered_at") or acks.get(m.get("id")):
            continue
        pend[str(m.get("from"))] = max(pend.get(str(m.get("from")), 0),
                                       int(now - float(m.get("ts", now))) / 60)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    fleet = json.loads(op.open(u"http://127.0.0.1:4820/api/fleet", timeout=25)
                      .read().decode("utf-8", "replace"))
    byid = {r["id8"]: r for r in fleet["rows"]}
    rows, stuck = [], []
    for frm, age in sorted(pend.items(), key=lambda x: -x[1]):
        id8 = frm.split(":")[-1][:8]
        r = byid.get(id8)
        nm = r["name"] if r else u"（不在板上）"
        if r is None:
            rows.append((id8, nm, age, None, None))
            continue
        rows.append((id8, nm, age, r["state"], r["idle_min"]))
        if r["state"] != "writing" and r["idle_min"] >= STALL_MIN:
            stuck.append((id8, nm, age, r["idle_min"]))
    return rows, stuck, len(pend)


def main():
    rows, stuck, total = compute()
    print(u"未验收的交付共 %d 条，涉及 %d 扇：" % (total, len(rows)))
    for id8, nm, age, state, idle in rows:
        print(u"   %-9s %-10s 压 %3.0f 分｜%s" % (id8, nm, age,
              (state if state else u"不在板上") + (u"" if idle is None else u"｜静 %d 分" % idle)))
    print(u"交了活且已静默≥%d 分（可能正等验收）：%d 扇：%s"
          % (STALL_MIN, len(stuck),
             u"、".join(u"%s %s 交%d 分/静%d 分" % s for s in stuck) or u"无"))
    if "--send" not in sys.argv:
        return 0
    if not stuck:
        print(u"没人因等验收而停 ⇒ 不投，免得又一条噪声")
        return 0
    tail = io.open(CLOSING, encoding="utf-8").read().strip()
    body = (u"包工头：验收口这里有一条带因果的，不是泛泛催。**这几扇是交了活之后停下来的**，"
            u"最可能正等你那一句才开下一件——先点它们比按时间顺序往下读更省。"
            u"其余交了活但仍在写的，我没列进来（那不叫卡）。"
            u"每条的压龄与静默分钟都在出处那栏，那段就是本机这条算法现跑的结果：\n")
    for id8, nm, age, idle in stuck:
        body += u"　· %s %s：交完活了静默到现在，交付压龄与静默分钟见出处行\n" % (id8, nm)
    body += (u"要重算就一条：python %s\n" % os.path.join(HERE, os.path.basename(__file__)))
    body += tail
    io.open(BODYF, "w", encoding="utf-8", newline=chr(10)).write(body)
    ev = u"验收队列现算|python " + os.path.join(HERE, os.path.basename(__file__))
    p = subprocess.run([sys.executable, os.path.join(ROOT, "bus.py"), "send",
                        "--from", ME, "--to", CMDR, "--kind", u"note",
                        "--topic", u"acceptance-queue-" + time.strftime("%m%d%H%M%S"),
                        "--body-file", BODYF, "--evidence", ev],
                       cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.stdout.decode("utf-8", "replace")
    print(u"send rc=%d" % p.returncode)
    try:
        mid = json.loads(out).get("id", u"")
    except Exception:
        sys.exit(u"ABORT：非 JSON：%s" % out[:260])
    if not mid:
        sys.exit(u"ABORT：没拿到 id：%s" % out[:260])
    got = json.loads(urllib.request.urlopen(
        u"http://127.0.0.1:4799/msg?id=" + urllib.parse.quote(mid), timeout=10)
        .read().decode("utf-8", "replace"))
    last = (got.get("body") or u"").strip().splitlines()[-1]
    print(u"回读 id=%s｜尾行逐字相同=%s｜evidence %d 段"
          % (mid, last == tail, len(got.get("evidence") or [])))
    if last != tail:
        sys.exit(u"ABORT：尾行没对上")
    os.remove(BODYF)
    print(u"ACCEPTANCE_QUEUE_SENT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
