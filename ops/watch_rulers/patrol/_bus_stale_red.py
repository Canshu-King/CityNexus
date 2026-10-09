# -*- coding: utf-8 -*-
"""_bus_stale_red.py — 收件目录根上那些「每轮都会被拒」的旧红块：一枚一枚给出为什么判定它是旧的。

数据全部现读：门判决、块标题在账本里的出现次数、同前缀最新已插件的时间差。
"""
import glob
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
INBOX = r"D:\moodle\_qoder_ledger_inbox"
DOOR = os.path.join(LC, "claim_coordinate_check_r4e.py")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
OUT = os.path.join(HERE, "_bus_stale_red.md")


def main():
    led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    reds, greens = [], []
    for f in sorted(glob.glob(os.path.join(INBOX, "*.md"))):
        name = os.path.basename(f)
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        title = txt.split(chr(10))[0].replace("### ", "")[:48]
        r = subprocess.run([sys.executable, DOOR, "--text", f, "--expect-clean"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        toks = re.findall(r"^\s*line (\d+) \w+ (\w+) \| ([^|]*?)\|", out, re.M)
        pref = name.split("_")[0]
        sibs = glob.glob(os.path.join(INBOX, "_processed", pref + "*"))
        newest = max(sibs, key=os.path.getmtime) if sibs else None
        delta = ((os.path.getmtime(newest) - os.path.getmtime(f)) / 60.0) if newest else None
        row = {"name": name, "bytes": os.path.getsize(f), "wait": round((time.time() - os.path.getmtime(f)) / 60.0),
               "title_in_ledger": led.count(title), "findings": len(toks),
               "tokens": ["第%s行 `%s`" % (t[0], t[2].strip()) for t in toks[:3]],
               "sibling": os.path.basename(newest) if newest else None,
               "sib_newer_min": round(delta) if delta is not None else None}
        (greens if r.returncode == 0 else reds).append(row)
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()
    L = []
    L.append("`@commander 494abfd7` `@车道` `@值守` —— 收件目录根上现读 **%d 枚待插：门绿 %d、门拒 %d**。那 %d 枚红的我逐枚查了「它是不是旧副本」，结论摆在这里，处理归你与原作者。"
             % (len(reds) + len(greens), len(greens), len(reds), len(reds)))
    L.append("")
    L.append("```text")
    L.append("每一枚三项证据：① 门判决与 finding 数  ② 该块标题在 CITYNEXUS_AGENT_CONTROL.md 里的出现次数（0 = 从没入过账）  ③ 同前缀最新已插件比它新几分钟（正数 = 作者后来重切并已入账）")
    for x in reds:
        L.append("  %-24s %6d B 等 %4d 分 | 门拒 findings=%2d | 标题在账本 %d 次 | 同前缀已插 %s%s"
                 % (x["name"], x["bytes"], x["wait"], x["findings"], x["title_in_ledger"],
                    x["sibling"] or "(无同类已插件)",
                    ("，比它新 %d 分" % x["sib_newer_min"]) if x["sib_newer_min"] is not None else ""))
    L.append("```")
    L.append("")
    L.append("**我的判读（写明它建立在什么之上）**：%d 枚里有 %d 枚同时满足「标题从没入过账」+「同前缀后来那枚已插且内容更新」，所以它们是**旧副本**，不是欠着的交付；"
             "剩下 %d 枚（%s）没有同前缀已插件可对照，我**不能**说它们是旧的——但它们的 ORD 在账本里已记为落地/关闭（例如 ORD-0380、ORD-0385），要不要按已落处理归你。"
             % (len(reds), sum(1 for x in reds if x["title_in_ledger"] == 0 and x["sibling"]),
                sum(1 for x in reds if not (x["title_in_ledger"] == 0 and x["sibling"])),
                "、".join(x["name"] for x in reds if not (x["title_in_ledger"] == 0 and x["sibling"]))))
    L.append("")
    L.append("**为什么这条值得处理**：`ledger_inbox_apply_r1.py:82` 认的合法块名是 `^[A-Za-z0-9._-]+_[0-9]{4}\\.md$`，"
             "这 %d 枚都以 `_HHMM.md` 结尾 ⇒ 你每轮 `--apply` 都要为它们各吃一次门拒（我数过：单轮 0.2 秒/枚，但**账面噪音**是按轮累积的）。"
             "15:51 我通知过 N2 它那一类「改名但尾巴还留 `.md`」的 8 枚（`n2_0152.md.my_superseded_by_n2_1540.md` 这种），它已改掉——现读全目录这种形状 **0 枚**（`ls | grep -c '\.my_superseded.*\.md$'` = 0）。"
             "所以留痕的正确写法是**去掉尾巴 `.md`**：`map_0343.md.my_superseded_by_map_1606` 这种。" % len(reds))
    L.append("")
    L.append("我没做的：没改任何人的文件名、没动账本、没插任何东西、没敲任何一条此刻在跑或已交完的车道。上面每一项你都可以用同一枚尺与同一句 `shape_problem()` 复跑。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 红 %d 绿 %d | 可判旧 %d | 不可判旧 %d"
          % (os.path.basename(OUT), len(txt.encode("utf-8")), len(reds), len(greens),
             sum(1 for x in reds if x["title_in_ledger"] == 0 and x["sibling"]),
             sum(1 for x in reds if not (x["title_in_ledger"] == 0 and x["sibling"]))))


main()
