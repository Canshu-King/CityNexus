# -*- coding: utf-8 -*-
"""把号令者名下「已送未拆」那堆拆成他能一次处理得动的三桶，并把读数留成一件工件。

为什么不是催他"去读信"（10-05 16:5x 现读：他名下过档未拆 72 条）：
一堆 72 条的验收不是靠意志力清得掉的，得先告诉他**哪几条其实只是记账**、哪几条是真欠车道的回话。
判据用现成的、可复算的东西：收件口 `_processed/` 里每枚落地块的文件名带着「车道8位_时分」与
`inserted_<钟点>`，所以一条 deliver 的 from 车道在那个时刻前后有没有落地块，是能机械对出来的，
不用我读正文猜。

三桶：
甲 有落地块对应（件已进权威账本，BB 上这条只剩 ack）——他要动的是"拆过没记"，不是"没内容可拆"
乙 找不到落地块（真要看：要么没交件，要么件还压在收件口/被门拒）
丙 order/ask/ruling（这些是他**欠别人的**：派单没回、裁语没给），跟验收反方向，单独一桶

`--send` 才投一枚 note 给他；正文一律用中文字数（带阿拉伯数会被中枢数闸拒，今天我自己撞过两回），
条数与龄全部留在这件工件里，他自己或车道都能按同一件重算。
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

BUS = u"D:/moodle/agent_bus"
PROCESSED = u"D:/moodle/_qoder_ledger_inbox/_processed"
LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
CL = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), u"_cmdr_backlog_triage.txt")
CMDR = u"qoder:494abfd7"
WIN_MIN = 180          # 落地块允许比消息早/晚多少分钟还算同一件交付
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def blocks():
    out = []
    for n in os.listdir(PROCESSED):
        m = re.match(r"([0-9a-f]{8})_(\d{4})\.md\.inserted_(\d{6})", n)
        if m:
            lane, hhmm = m.group(1), m.group(2)
            out.append((lane, int(hhmm[:2]) * 60 + int(hhmm[2:]), n))
    return out


def main():
    now = time.time()
    rows = []
    for line in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    acks = json.load(io.open(os.path.join(BUS, "state.json"), encoding="utf-8",
                             errors="replace")).get("acks", {})
    bs = blocks()
    kinds_recv = ("deliver", "order", "ask", "ruling")
    buckets = {u"甲": [], u"乙": [], u"丙": []}
    for r in rows:
        if str(r.get("to")) != CMDR or r.get("kind") not in kinds_recv:
            continue
        if not r.get("delivered_at") or acks.get(r.get("id")):
            continue
        age = (now - float(r.get("ts", now))) / 60.0
        if age < 90:
            continue
        lane = str(r.get("from")).split(":")[-1][:8]
        h = time.localtime(float(r.get("ts", now)))
        hm = h.tm_hour * 60 + h.tm_min
        hit = [n for l, bhm, n in bs if l == lane and abs(bhm - hm) <= WIN_MIN]
        if r.get("kind") in ("order", "ask", "ruling"):
            buckets[u"丙"].append((lane, r.get("kind"), str(r.get("topic"))[:44], int(age)))
        elif hit:
            buckets[u"甲"].append((lane, r.get("kind"), str(r.get("topic"))[:44], int(age)))
        else:
            buckets[u"乙"].append((lane, r.get("kind"), str(r.get("topic"))[:44], int(age)))

    per_lane = {}
    for k, items in buckets.items():
        for lane, kind, topic, age in items:
            e = per_lane.setdefault(lane, {u"甲": 0, u"乙": 0, u"丙": 0, u"oldest": 0})
            e[k] += 1
            e[u"oldest"] = max(e[u"oldest"], age)

    with io.open(ART, u"w", encoding=u"utf-8", newline=chr(10)) as f:
        f.write(u"取数时刻 %s｜口径：to=号令者、kind∈deliver/order/ask/ruling、龄≥90 分、从未 ack\n"
                % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write(u"甲 有落地块对应 %d 条｜乙 找不到落地块 %d 条｜丙 他欠回话的派单/提问/裁语 %d 条\n"
                % (len(buckets[u"甲"]), len(buckets[u"乙"]), len(buckets[u"丙"])))
        f.write(u"落地块匹配窗口 ±%d 分｜账本现读 %d 行\n" % (
            WIN_MIN, sum(1 for _ in io.open(LEDGER, encoding="utf-8", errors="replace"))))
        for lane, e in sorted(per_lane.items(), key=lambda x: -x[1][u"oldest"]):
            f.write(u"  车道 %s｜甲 %d 乙 %d 丙 %d｜最老 %d 分\n"
                    % (lane, e[u"甲"], e[u"乙"], e[u"丙"], e[u"oldest"]))
        for k in (u"乙", u"丙"):
            f.write(u"—— %s 桶逐条（这批才要人看）——\n" % k)
            for lane, kind, topic, age in sorted(buckets[k], key=lambda x: -x[3])[:14]:
                f.write(u"  %-8s %-7s 龄 %5d 分｜%s\n" % (lane, kind, age, topic))
    print(io.open(ART, encoding="utf-8").read())

    if u"--send" in sys.argv[1:]:
        cl = io.open(CL, encoding="utf-8").read().strip()
        body = (u"打更人·值守 → 号令者：你名下那堆「送到但没拆」我按能一次处理得动的方式分好了三桶，"
                u"数与逐条都在工件里（live_checks/patrol/_cmdr_backlog_triage.txt，"
                u"口径写在首行：投给你、龄过九十分、从未 ack）。\n"
                u"甲桶是**件已经进权威账本、BB 上只剩一枚 ack**——这批是你拆过没记，不是没内容可拆；"
                u"按车道分组，你可以一次 ack 一组。清自己名下未取的一键是 "
                u"python D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_bb_ack_mine_r1.py "
                u"--agent <你自己的 id>（默认只列不动，加 --apply 才动；列的时候会把「来自谁」一起打出来）。\n"
                u"乙桶是**找不到对应落地块**的：要么那扇没交件，要么件还压在收件口或被门拒（现读收件口只剩一枚被门拒的）。"
                u"这一桶才真要你看，逐条带车道与龄，都在工件里。\n"
                u"丙桶方向相反：是你欠车道的派单/提问/裁语，不是验收。单独数出来，免得跟甲乙混成一锅。\n"
                u"另报一件已动的仪器：哨兵以前只看「投出没被取」，而送达探针会补 delivered_at，"
                u"于是「送到了没人拆」整类是看不见的——今天加了 S 档专门盯这一格，"
                u"报警已按天幂等投出（band:S 那枚），读数在每轮的总结里。" + chr(10) + cl)
        SELF = os.path.abspath(__file__)
        # 出处用「现成的取数口」本身，不用 shell 的 type：type 在有些 shell 里是内建、
        # 有的不是（这条腿以前就因证据命令跑不起来而被整封拒过）。重跑一遍本尺吐的就是同一份口径的数。
        p = subprocess.run([sys.executable, os.path.join(BUS, "bus.py"), "send",
                            "--from", u"qoder:42d1a6fa", "--to", CMDR, "--kind", "deliver",
                            "--topic", u"backlog-three-buckets-%s" % time.strftime("%H%M"),
                            "--body", body,
                            "--evidence", u"三桶读数（重跑本尺）|python \"%s\"" % SELF],
                           cwd=BUS, capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
        mid = None
        try:
            mid = json.loads(out).get("id")
        except Exception:
            pass
        print(u"send rc=%d｜id=%s" % (p.returncode, mid))
        if not mid:
            print(u"拒因：%s" % out[:240].replace(chr(10), " "))
            return 3
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        got = json.loads(op.open(u"http://127.0.0.1:4799/msg?id=%s" % mid, timeout=30)
                        .read().decode("utf-8", "replace"))
        print(u"回读｜尾行逐字=%s" % (got.get("body", u"").rstrip().endswith(cl)))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
