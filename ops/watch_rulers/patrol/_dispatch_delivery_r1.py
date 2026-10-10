# -*- coding: utf-8 -*-
"""派单送达尺（只读）：号令者账本里『具名派单』有没有真的进到那条车道的流水。

为什么另开一张：2026-09-29 19:02 自动轮报 ORD-0468 无人接，一查是**收件车道从 18:38 起停在
每日额度上**，号令者 18:38/18:41 两次敲门都在两三秒内被闸挡回 ⇒ 单子写在账本上，车上没有。
这类『写了＝派了』的假象只有回读车道流水才拆得穿。

我给自己钉的规矩（这一张尺自己踩过）：
  1) 必须打印**分母**（评估了多少组 单号×车道）。上一版我按『账本最后 900 行』筛块，
     结果那一窗里根本没有号令者的块 ⇒ 报了个『0 组未送达』的空分母假绿。
  2) 必须打印一枚**正对照**（已知送到的那组），证明这尺读得到命中。
  3) 转达只认『同一行里逐字出现该 8 位 id』，且那行必须出自 `### cmdr` 块。
"""
import io
import json
import os
import re
import sys
import time

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道",
}


def jsonl(sid8):
    c = [os.path.join(BASE, f) for f in os.listdir(BASE)
         if f.startswith(sid8) and f.endswith(".jsonl")]
    return max(c, key=os.path.getsize) if c else None


def state(sid8, now):
    p = jsonl(sid8)
    if not p:
        return "无流水"
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 150 * 1024))
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    last = None
    for l in blob.split("\n"):
        l = l.strip()
        if not l.startswith("{"):
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant"):
            continue
        m = o.get("message") or {}
        c = m.get("content")
        t = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
        if t.strip():
            last = t.strip()
    age = (now - os.path.getmtime(p)) / 60.0
    tag = "闸上" if (last and "daily usage limit" in last) else ("在写" if age < 8 else "静默")
    return "%s(%.0f分)" % (tag, age)


def cmdr_blocks(take):
    """最近的号令者块＝从收件口 `_processed/cmdr_HHMM.md.inserted_*` 按插入时间取。

    为什么不用账本行号：账本**不是**按时间追加在文件尾部的——2623 枚 `### ` 标题里，
    今天的块在中部、09-25 的老块在文件尾部（我上一版按『最后 900 行』和『最后 8 枚
    `### CMDR` 标题』两次都取到了 09-25 的块，分母 0 报成『0 组未送达』，是空分母假绿）。
    """
    d = r"D:\moodle\_qoder_ledger_inbox\_processed"
    cands = [f for f in os.listdir(d) if f.lower().startswith("cmdr") and ".inserted_" in f]
    cands.sort(key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True)
    out = []
    for f in cands[:take]:
        path = os.path.join(d, f)
        body = io.open(path, encoding="utf-8", errors="replace").read()
        out.append((f, os.path.getmtime(path), body.split(chr(10))))
    return out


def main():
    take = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    now = time.time()
    cache = {}
    pairs = []
    for fname, bmt, blines in cmdr_blocks(take):
        for i in range(len(blines)):
            l = blines[i]
            if "ORD-04" not in l:
                continue
            idpos = [(m.start(), m.group(1)) for m in re.finditer(r"\b([0-9a-f]{8})\b", l)
                     if m.group(1) in LANES]
            nums = list(re.finditer(r"ORD-0(4\d\d)", l))
            # 20:13 又抓到一类错配：一行里同时列几张单、又好几个 id
            # （原文例：『ORD-0468 与 ORD-0470 在车道 9cc37e57 与 e4f3490f 手上』）。
            # 这种行**按位置配必错**（我就差点把 ORD-0468 报成 newlane 的），所以整行不判；
            # 判定只信『一枚单号对一枚 id、且 40 字内没有别的单号压着』的邻接。
            if len(set(x.group(0) for x in nums)) > 1 and len(set(y for _p, y in idpos)) > 1:
                continue
            for om in nums:
                num = "ORD-0" + om.group(1)
                for ip, sid8 in idpos:
                    if abs(ip - om.start()) <= 16 and not [q for q in nums if q is not om and abs(q.start() - ip) <= 40]:
                        pairs.append((num, sid8, fname, i + 1))
    uniq = {}
    for num, sid8, head, ln in pairs:
        uniq.setdefault((num, sid8), (head, ln))
    print("=== 派单送达 %s：读最近 %d 枚号令者源块（收件口 `_processed/cmdr_*.inserted_*`）===" % (time.strftime("%H:%M:%S"), take))
    blknames = sorted(set(v[0][:40] for v in uniq.values()))
    print("分母：%d 组（单号 × 具名车道）；来自 %d 枚号令者块" % (len(uniq), len(blknames)))
    for bn in blknames:
        print("   块：%s" % bn)
    if not uniq:
        print("!! 分母为 0 ⇒ 这张尺现在什么都不能证明（没读到具名派单行，别把『没有』读成『都送到了』）")
        return 3
    miss = []
    hit_demo = None
    for (num, sid8), (head, ln) in sorted(uniq.items()):
        p = jsonl(sid8)
        if not p:
            continue
        if num not in cache:
            cache[num] = {}
        body = io.open(p, encoding="utf-8", errors="replace").read()
        c = body.count(num)
        cache[num][sid8] = c
        if c == 0:
            miss.append((num, sid8, state(sid8, now), head[:34], ln))
        elif hit_demo is None:
            hit_demo = (num, LANES[sid8], c)
    for num, sid8, st, head, ln in miss:
        print("  !! 未送达 %s → %s(%s) 车道状态 %s｜出自 %s 账本 L%d" % (num, LANES[sid8], sid8, st, head, ln))
    print("正对照（证明这尺读得到命中）：%s" % ("%s 在 %s 流水里命中 %d 次" % hit_demo if hit_demo else "没有一枚命中 ⇒ 尺可疑，先别看数"))
    print("小结：未送达 %d / 评估 %d 组。『未送达』只说明该单号没进过那条流水；"
          "要不要转达由我看那行是否逐字带该 id、以及那条车是不是停在额度上（停闸上的转达只是把字放进它上下文，今晚不会动）。" % (len(miss), len(uniq)))
    print("边界：只读（账本、车道流水与 mtime）；0 次写账本、0 次代插、0 次改别人的枝、0 次重启进程。")
    return 2 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
