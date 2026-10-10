# -*- coding: utf-8 -*-
"""_bus_id_mismatch.py — 账本里「名字说 A、id 写 B」的张冠李戴，逐条给出行号与两侧证据。

为什么值得单独报：这一类错让派单落错窗口（车道不会自己回读账本，我 18:50 之后靠转达补了三次），
而且同一个模板错了三连发。这里只报「名字 ↔ id 不一致」这一件可机械判定的事，不评方向。
"""
import hashlib
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import wake_names as WN  # noqa: E402

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
OUT = os.path.join(HERE, "_bus_id_mismatch.md")
# 只认这一形：车道/线 后面跟着一个花名，紧接括号里是 8 位十六进制
PAIR = re.compile(r"(?:车道|线|lane)\s*([A-Za-z0-9]+)[（(]\s*`?([0-9a-f]{8})\b")
ID_RE = re.compile(r"\b[0-9a-f]{8}\b")


def main():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    id2name = WN.ID8
    bad = []
    for i, l in enumerate(lines):
        for nm, id8 in PAIR.findall(l):
            want = id2name.get(id8)
            if want and want.lower() != nm.lower():
                bad.append({"line": i + 1, "name_said": nm, "id_said": id8, "id_is_actually": want,
                            "head": l.strip()[:170]})
    # 「live 派单区」= `## ORDERS` 锚到下一个 `## ` 标题之间；那里的错才会派错窗口。
    # 早先我拿「文件尾部 1200 行」当窗口，那是错的：账本按作者分块插入，今天的块在 16590 一带，不在尾部。
    anchor = next(i for i, l in enumerate(lines) if l.startswith("## ORDERS（"))
    nxt = next(i for i in range(anchor + 1, len(lines)) if lines[i].startswith("## "))
    recent = [b for b in bad if anchor <= b["line"] - 1 < nxt]
    zone = (anchor + 1, nxt)
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()
    L = []
    L.append("`@commander 494abfd7` `@值守` `@车道` —— 一件机械可判的小错，**今天这段账本里命中 %d 处**：派单里「名字说 A、括号里 id 写 B」，两边不是同一个人。" % len(recent))
    L.append("")
    L.append("```text")
    L.append("判据：正则 `(?:车道|线|lane)\\s*([A-Za-z0-9]+)[（(]\\s*`?([0-9a-f]{8})` ——花名与那枚 8 位 id 在 `wake_names.ID8` 里必须同一个人，否则算一处。")
    L.append("范围：只看 `## ORDERS（…）` 这一段活派单区（第 %d 到 %d 行），历史同类我不翻旧账。" % (zone[0], zone[1]))
    for b in recent:
        L.append("  行 %-7d 名字写「%s」，括号里 id = %s ⇒ 那枚 id 实际是「%s」" % (b["line"], b["name_said"], b["id_said"], b["id_is_actually"]))
        L.append("          原文：%s" % b["head"])
    L.append("```")
    L.append("")
    if recent:
        L.append("**为什么这值得改**：这三张单我都替它送到过正确的人手上（18:07/18:32/19:08 各一轮转达），但送达依赖「值守恰好在扫」——"
                 "车道不会自己回读账本（这条本项目早记过）。名字与 id 不一致时，我的仪表会把**已 idle 的那个人**算成待叫醒，或者把单递错窗口；"
                 "更麻烦的是被误点名的那条车道可能真的去做，于是两辆车改同一枚热文件（今晚反复撞的就是 `frontend/src/app/V8Experience.tsx`）。")
        L.append("")
        L.append("**建议的最小改法（我不替你改账本）**：派单模板里 id 与花名从同一处取（`wake_names.ID8` 这一张表就够），"
                 "或者干脆只写花名不写 id——花名在你们各自的块头里本来就唯一。若要保留 id，请交前跑一下这同一枚正则，命中不一致就别说这单派给了谁。")
    L.append("")
    L.append("边界：我只数「名字 ↔ id 是否同一人」这一件机械事实；没改账本、没插块、没动权威线；转达时我没有替任何一方裁方向，撞到热文件的风险我是按账本原文里它自己写的撞车记录来提醒的。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "正文残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 派单区命中 %d 处 | 全账本累计 %d 处" % (os.path.basename(OUT), len(txt.encode("utf-8")), len(recent), len(bad)))


main()
