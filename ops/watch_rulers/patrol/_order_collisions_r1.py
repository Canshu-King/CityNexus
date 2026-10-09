# -*- coding: utf-8 -*-
"""值守 08:22 · 单号撞车检测（只读账本块头）。

号令者自己今夜已经因为撞号改过三次单号（账本原话：ORD-0419 让给实例 A、ORD-0426 让成 ORD-0428、
顶栏那格从 ORD-0427 改到 ORD-0431），他给自己立的规矩是「开新单前先 grep 一次账本」。
两个实例并行时这条规矩靠自觉，所以这里做成一把常开的尺：
  块头里出现的 ORD 号 → 看它被几个**不同会话**当成本单的交付块在用；
  同一号被两条不同车道各自交块 ⇒ 报 COLLISION（可能是撞号，也可能真是一单两车道分工，所以只报不改判）。
判据只认块头（`### …`），因为正文里的单号常常是在引用别人的单，那不算撞。
"""
import io
import os
import re
import sys
import collections

LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wake_names as WN

HEAD = re.compile(r"^### (.*)$")
ORD = re.compile(r"ORD-(\d{4})")
DATE = re.compile(r"2026-09-(\d{2})")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
    heads = [HEAD.match(l).group(1) for l in lines if HEAD.match(l)]
    today = [h for h in heads if DATE.search(h)]
    by_ord = collections.defaultdict(set)
    titles = collections.defaultdict(list)
    for h in today:
        owner = None
        for c in WN.ID8:
            if c in h:
                owner = c
                break
        # 块头里只出现 `qoder-04xx` / `R-ord04xx` 这类枝名时，那个号也算它认领这一单
        for b in re.finditer(r"(?:qoder-|ord|ORD-)(\d{4})", h):
            pass
        for o in ORD.findall(h):
            if owner:
                by_ord[o].add(owner)
            titles[o].append(h[:70])
    print("今日块头 %d 枚，里面点到的单号 %d 个" % (len(today), len(by_ord)))
    CMDRS = {"494abfd7", "6efab655"}
    coll = [(o, sorted(set(p) - CMDRS)) for o, p in by_ord.items() if len(set(p) - CMDRS) > 1]
    cmdr_only = [(o, sorted(p)) for o, p in by_ord.items()
                 if len(p) == 1 and list(p)[0] in ("494abfd7", "6efab655")]
    print("\n跨车道同号（同一单被两条以上**车道**各自交块；号令者自述块已剔除，他提自己派的号是常态不算撞）%d 个：" % len(coll))
    for o, ps in sorted(coll):
        print("   ORD-%s ← %s" % (o, "、".join("%s(%s)" % (p, WN.ID8.get(p, "?")) for p in ps)))
        for t in titles[o][:3]:
            print("        %s" % t)
    only_cmdr = sorted(o for o, p in by_ord.items() if p and not (set(p) - CMDRS))
    print("\n只出现在号令者块头里的单 %d 个：%s"
          % (len(only_cmdr), "、".join("ORD-" + o for o in only_cmdr[:20])))
    print("  ↑ 这一列**不能**直接读成「没人干」：块头不写单号的车道（例如只写 `qoder-0418 …` 或英文块头）"
          "不在这把尺的抓取范围里。要判有没有人干，用 `_new_dispatch_r1.py`（它会同时看账本块与收件口未插的块）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
