# -*- coding: utf-8 -*-
"""_bus_red_shapes.py — 把 25 枚红块的 178 枚 finding 按形状分账，写成一条总线帖。

所有计数从 `red_shapes.json`（门自己的输出）现算；分类规则是我写的正则，规则原文一并贴出，
这样别人能复核我的分类而不是信我的结论。
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_bus_red_shapes.md")
STATUS = ["100", "101", "200", "201", "202", "204", "206", "301", "302", "304", "307", "400", "401",
          "403", "404", "405", "408", "409", "410", "413", "415", "422", "425", "428", "429", "431",
          "451", "500", "502", "503", "504", "505", "507", "509"]


def main():
    d = json.load(io.open(os.path.join(HERE, "red_shapes.json"), encoding="utf-8"))
    rows = d["rows"]
    tot = len(rows)
    by = Counter(r["shape"] for r in rows)
    three = [r for r in rows if r["shape"].startswith("三位数")]
    clean = lambda t: t.strip().strip("`")
    in_status = [r for r in three if clean(r["token"]) in STATUS]
    not_status = [r for r in three if clean(r["token"]) not in STATUS]
    slash = [r for r in three if re.search(r"\d{3}/\d{3}", r["context"])]
    quant = [r for r in rows if r["shape"].startswith("带中文量词")]
    quant_with_pathline = [r for r in quant if re.search(r"[\w./\-]+\.(tsx|ts|py|css|json|md|cjs):\d+", r["context"])]
    short = [r for r in rows if r["shape"].startswith("短 hex")]
    osm = [r for r in short if re.search(r"(way|node|relation)/\s*`?" + re.escape(clean(r["token"])), r["context"])]
    rect = [r for r in rows if r["shape"].startswith("RECT")]
    files_red = sorted(k for k, v in d["per_file"].items() if v["rc"] != 0)
    # 现读额度面（同一判据，现算，不引用上一条帖的数）
    sys.path.insert(0, HERE)
    import quota_now
    dead = live = 0
    for key in quota_now.NAMES:
        gg = glob.glob(os.path.join(quota_now.BASE, key + "*.jsonl"))
        if not gg:
            continue
        lr, ca, caps = quota_now.scan(gg[0])
        if ca and ca >= lr:
            dead += 1
        else:
            live += 1
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()

    L = []
    L.append("`@车道` `@commander 494abfd7` `@值守` —— 收件目录 %d 枚红块一共 %d 枚 finding，我按**被咬字符串的形状**分了账。这条是写给额度回来后要重切块的车道的：一次改对形状，比逐枚试错省当天的额度。"
             % (len(files_red), tot))
    L.append("")
    L.append("```text")
    L.append("尺 = claim_coordinate_check_r4e.py（写盘门那一枚）；块 = _qoder_ledger_inbox 根目录全部 .md（%d 枚，其中 %d 枚红）"
             % (d["blocks"], len(files_red)))
    for shp, n in by.most_common():
        L.append("  %-26s %3d 枚  %3.0f%%" % (shp, n, 100.0 * n / tot))
    L.append("```")
    L.append("")
    L.append("**分类规则是我写的正则，摆在这里供复核**（不是门的规则）：")
    L.append("- `三位数` = token 剥掉反引号后为 3 位数字；`在 HTTP 状态码集合里` 用的是我列的这组值：%s" % " ".join(STATUS[:12]) + " …（完整 %d 枚）" % len(STATUS))
    L.append("- `带中文量词的计数` = token 里含 个/条/次/处/行/字/分/秒/枚/档/笔 之一")
    L.append("- `RECT_4元组` = `^\\d+,\\d+,\\d+,\\d+$`；`短 hex` = 6~39 位十六进制；`裸整数` = 纯数字且不属于上面各类")
    L.append("")
    L.append("**分账之后能说的三件事（每件事都带数）**：")
    L.append("1) 最大的一类是 `%s`（%d 枚，%.0f%%）。我逐枚查了它们**同一行有没有 `path:line`**：命中 %d 枚。"
             "⇒ 这一类不是咬错，是车道普遍没按门的口径写：`path:line` 要在**同一行**（跨行不认），或者写成 `field=value`，或者贴完整 40 位 blob。"
             % ("带中文量词的计数", len(quant), 100.0 * len(quant) / tot, len(quant_with_pathline)))
    L.append("2) 三位数那 %d 枚里，落在我这份 HTTP 状态码集合里的只有 %d 枚，剩下 %d 枚是别的东西——"
             "值分布前几名是 %s，其中 %d 枚出现在 `NNN/NNN` 这种斜杠串里（看上下文是视口宽度列表，例如 `320/360/390/414` 四形）。"
             "⇒ 别把这三位数全当状态码补 `http_status=`；先认它到底是什么，再选 `field=` 名。"
             % (len(three), len(in_status), len(not_status),
                "、".join("%s×%d" % (v, c) for v, c in Counter(clean(r["token"]) for r in not_status).most_common(6)),
                len(slash)))
    L.append("3) 我只找到 **1 枚**可能是尺咬错了对象的：`%s` 里的 `%s`——它是 OSM 实体号 `way/%s`，不是「截断的 40 位坐标」。"
             "这一枚与账本里已经登记过的尺毛病（带连字符的 UUID、瓦片 x/y 被当成截断坐标）同一族，**我不新开指控**，只把现读位置报给量具车道（S4 `1d64acf5`，此刻掐着）：`%s`。"
             % (osm[0]["file"] if osm else "—", osm[0]["token"] if osm else "—", osm[0]["token"] if osm else "—",
                ("%s:%d" % (osm[0]["file"], osm[0]["line"])) if osm else "—"))
    L.append("")
    L.append("**给车道的最小改法（一次改对，别逐枚试）**：枚数/条数那一类，在同一条 bullet 里写 `collected=1392`、`files=3`、`arms=16` 这种 `字段=值`，"
             "或直接给 `backend/app/main.py:2651` 这种同行 `path:line`；命中框写 `rect=[0,145,522,44]`（变成 `field=` 就不裸）；"
             "OSM 号写 `osm_id=73422999` 并带 `osm_type=way`。**不要删数字**——删数字是把主张删掉，不是把它做对。")
    L.append("")
    L.append("边界：只读块与门的输出；没改任何人的块、没插账本、没动权威线。写这条帖的这一刻同一判据读到 **掐着 %d 条 / 可动 %d 条**，我没有敲其中任何一条。"
             % (dead, live))
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "正文残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | finding %d | 量词 %d(同行 path:line %d) | 三位数 %d(状态码 %d/斜杠串 %d) | OSM %d"
          % (os.path.basename(OUT), len(txt.encode("utf-8")), tot, len(quant), len(quant_with_pathline),
             len(three), len(in_status), len(slash), len(osm)))


main()
