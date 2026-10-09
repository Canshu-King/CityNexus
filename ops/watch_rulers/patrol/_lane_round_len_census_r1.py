# -*- coding: utf-8 -*-
u"""攒"车道一轮要多长"的分布数据，好让第②格那个 45 分门槛有据可改。

为什么要攒（五·二十七 定下的规矩）：17:38 那拍静默超 45 分的有 6 扇，逐扇读末条发现**五扇都是
"本轮交完一件"**、真 busy 的 0 扇 ⇒ 那些静默是它们一轮的正常长度，45 分门槛偏低，
报出来的"该敲"多数是假阳性。但**不能凭一拍就改阈值**，改法要同时满足：
  一、连续若干拍里"末条是交活语句"的静默时长分布稳定落在某个区间；
  二、该区间之上仍能抓到真停摆（负对照：拿真停摆那几扇验门槛仍命中）。
所以这把尺逐拍把分布落盘，攒够拍数再谈改。

形态：只读（各扇自己的 jsonl + 板子那一格定位），落一份带日期的 txt；0 次写账本、0 次上总线。
跑法：PYTHONIOENCODING=utf-8 python _lane_round_len_census_r1.py [--append]
  默认追加每一拍；只有显式 --overwrite 才覆盖（攒数据的文件被手滑清空最难发现，见 18:0x 那次）
"""
import glob
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.expanduser(r"~\.qoder\projects\D--moodle")
OUT = os.path.join(HERE, "_lane_round_len_census_1006.txt")
BOARD = "http://127.0.0.1:4820/api/fleet"

SHELL = ("active-leaf", "last-prompt", "workspace-directories", "runtime-config", "attachment")
BUSY = re.compile(r"current model is busy|try again later|overloaded", re.I)
LIMIT = re.compile(r"daily usage limit", re.I)
# 10-06 17:5x 自测抓到漏判："ORD-0576 又交一批，落地回执也取了" 被读成 other（词表只有"交完/已交"）。
# 那正是车道最常见的说法之一，漏了它攒出来的分布就是废的 ⇒ 补 "交一批/取了/入账/上线/落账" 等。
DONE = re.compile(r"(交完|交一批|已交|交出|交付|delivered|landed|做完|做完并交|closed|on the ledger"
                  r"|落地回执|入账|已落账|已在线上|落线|上线了|闭了|已收走|收走了|已落线)", re.I)


def parse_ts(d):
    t = d.get("timestamp")
    if isinstance(t, (int, float)):
        return float(t) / 1000.0 if t > 1e11 else float(t)
    if isinstance(t, str) and len(t) >= 19:
        try:
            return time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
        except ValueError:
            return 0.0
    return 0.0


def last_assistant(path):
    last = None
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if '"assistant"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            last = d
    return last


def text_of(d):
    m = d.get("message") if isinstance(d.get("message"), dict) else {}
    c = m.get("content")
    if isinstance(c, list):
        return u" ".join((x.get("text", u"") if x.get("type") == "text" else u"[tool]")
                         for x in c if isinstance(x, dict))
    return str(c or u"")


def main():
    # 10-06 18:0x 修正：默认就是**追加**。旧默认是"不带 --append 就覆盖"，
    # 我 18:02 手动跑了一次没带它 ⇒ 把攒了五拍的数据冲成一拍（巡逻那腿一直带的是 --append，没错）。
    # 攒数据的文件被手滑清空是最容易发生又最难发现的丢数 ⇒ 覆盖必须显式 --overwrite。
    append = "--overwrite" not in sys.argv
    now = time.time()
    f = json.loads(urllib.request.urlopen(BOARD + u"/api/fleet", timeout=25).read().decode("utf-8"))
    rows = []
    for r in f["rows"]:
        g = glob.glob(os.path.join(BASE, r["id8"] + u"*.jsonl"))
        if not g:
            continue
        p = max(g, key=os.path.getmtime)
        la = last_assistant(p)
        if la is None:
            continue
        t = parse_ts(la)
        if not t:
            continue
        txt = text_of(la)
        idle = (now - t) / 60.0
        kind = (u"busy" if BUSY.search(txt) else
                u"limit" if LIMIT.search(txt) else
                u"tool" if u"[tool]" in txt else
                u"done" if DONE.search(txt) else
                u"other")
        rows.append((r["id8"], round(idle, 1), kind, int(r.get("unread", 0))))

    rows.sort(key=lambda x: -x[1])
    q = [x for x in rows if x[1] >= 45]
    doneq = [x[1] for x in q if x[2] == u"done"]
    busyq = [x[1] for x in q if x[2] in (u"busy", u"limit")]
    L = []
    L.append(u"# 车道一轮时长·逐拍落盘（10-06；值守 42d1a6fa）")
    L.append(u"# 口径：分母＝板子上在册的行；每扇只看它自己 jsonl 的**末条 assistant**（外壳节点不算）。")
    L.append(u"# 形态分类：done＝末条是交活/完成语句｜tool＝末条在跑工具｜busy/limit＝上游拥塞或日限额｜other。")
    L.append(u"# 用途：五·二十七 那条规矩——改第②格 45 分门槛要连续几拍分布 + 真停摆负对照，这里就是攒数据的。")
    # 改门槛要的是"交活型一轮的时长基线"，那**不必等过档样本**——把所有 done 型的静默都算进去。
    # 10-06 18:0x：标题行只报"≥45 那几枚"，车队健康时恒为 0，看着像没数据，其实每扇都记着（逐扇段）。
    alld = sorted(x[1] for x in rows if x[2] == u"done")
    L.append(u"## %s｜在册 %d｜静默≥45 分 %d（其中 done %d｜busy/limit %d）"
             % (time.strftime(u"%m-%d %H:%M:%S"), len(rows), len(q), len(doneq), len(busyq)))
    if alld:
        L.append(u"   交活型全体 %d 扇的静默：中位 %.1f 分｜最小 %.1f｜最大 %.1f（改门槛的基线看这个，"
                 u"不必等过档样本）" % (len(alld), alld[len(alld) // 2], alld[0], alld[-1]))
    if doneq:
        L.append(u"   交活型静默：%s（分 %s）" % (u"、".join(str(int(x)) for x in doneq),
                                              u"最小 %d／中位 %d／最大 %d"
                                              % (min(doneq), sorted(doneq)[len(doneq) // 2], max(doneq))))
    if busyq:
        L.append(u"   停摆型静默（这才是该敲/该报的）：%s" % u"、".join(str(int(x)) for x in busyq))
    # 形态结论：五·四十九已证明阈值走不通（真停摆 40+ 与交活型 42–49 重叠），
    # 唯一可靠的是末条形态 ⇒ 这里直接把分档结论印出来，下一班不必逐行读末条去自己分。
    stall = [x for x in q if x[2] not in (u"done", u"tool")]
    L.append(u"   形态结论：过档 %d 扇 ＝ 交活型间隙 %d｜在清信/在跑工具 %d｜**真停摆或等单 %d**%s"
             % (len(q), sum(1 for x in q if x[2] in (u"done", u"tool")),
                sum(1 for x in q if x[2] == u"tool"), len(stall),
                (u"（%s）" % u"、".join("%s/%s" % (x[0][:8], x[2]) for x in stall)) if stall else u""))
    L.append(u"逐扇：")
    for i, idle, kind, un in rows:
        mark = u" ←≥45" if idle >= 45 else u""
        L.append(u"   %-9s 静 %5.1f 分｜%-6s｜未取 %d%s" % (i, idle, kind, un, mark))
    blob = chr(10).join(L) + chr(10)
    if append and os.path.exists(OUT):
        with io.open(OUT, "a", encoding="utf-8", newline="\n") as f2:
            f2.write(chr(10) + blob)
    else:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(blob)
    print(u"已落 %s（%d 字节）｜在册 %d｜静默≥45 分 %d｜done 型 %d｜busy/limit 型 %d"
          % (os.path.basename(OUT), len(blob.encode("utf-8")), len(rows), len(q), len(doneq), len(busyq)))
    print(chr(10).join(L[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
