#!/usr/bin/env python
"""ORD-0555 lane instrument for PlanWithAiSheet.tsx: move the table's fifteen inline bilingual
ternaries onto new planning.* dictionary keys.

Screen text must not change, so the zh and en values are never hand-typed here: they are cut out
of the exact "before" snippet read from the source file, and after the move the dictionary entries
are re-read from the file and compared character-for-character against that same cut.

Usage (cwd anywhere, paths derive from this file):
    python i18n_0555_plan_with_ai_r1.py --side dict --batch 1
    python i18n_0555_plan_with_ai_r1.py --side product --batch 1
    python i18n_0555_plan_with_ai_r1.py --verify --batch 1
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(HERE))
PRODUCT = os.path.join(ROOT, "frontend", "src", "features", "planning", "PlanWithAiSheet.tsx")
DICT = os.path.join(ROOT, "frontend", "src", "i18n", "LocaleContext.tsx")

EN_ANCHOR = '  "planai.importPlacesCta": "Paste your own places and import them into this trip",'
ZH_ANCHOR = '  "planai.importPlacesCta": "粘贴你自己的地点，导入这趟行程",'

TERNARY = re.compile(r'^zh \? "(?P<zh>[^"]*)" : "(?P<en>[^"]*)"$')

# (new key, before-snippet read verbatim off the tip)
ENTRIES = [
    ("planning.noPlanThisTimeTheDataIsShortNotYourWording",
     'zh ? "这次排不出方案：数据不够，不是你说的不对" : "No plan this time: the data is short, not your wording"'),
    ("planning.stoppedBeforeVerification",
     'zh ? "已中止后续核对" : "Stopped before verification"'),
    ("planning.thisOneSResultIsUnknownNotItDidNotHappen",
     'zh ? "这一笔的结果未知（不是没发生）" : "This one\'s result is unknown (not: it did not happen)"'),
    ("planning.theServerCouldNotBeReached",
     'zh ? "连不上服务端" : "The server could not be reached"'),
    ("planning.theRequestWasRefused",
     'zh ? "这个要求被明确拒绝" : "The request was refused"'),
    ("planning.theServerFailedToFinish",
     'zh ? "服务端处理失败" : "The server failed to finish"'),
    ("planning.weCouldNotConfirmThisRun",
     'zh ? "无法确认这次的结果" : "We could not confirm this run"'),
    ("planning.noUsablePlansWereProduced",
     'zh ? "没有生成可行方案" : "No usable plans were produced"'),
    ("planning.aIIsUnavailableRightNow",
     'zh ? "AI 暂时不可用" : "AI is unavailable right now"'),
    ("planning.planning",
     'zh ? "正在规划…" : "Planning…"'),
    ("planning.workingOnYourRequest",
     'zh ? "正在处理你的需求。" : "Working on your request."'),
    ("planning.couldNotFinishPlanning",
     'zh ? "暂时无法完成规划" : "Could not finish planning"'),
    ("planning.tryACityWeHaveDataFor",
     'zh ? "换一座有数据的城市" : "Try a city we have data for"'),
    ("planning.tryAgainWithTheSameWords",
     'zh ? "照原话再试一次" : "Try again with the same words"'),
    ("planning.planning2",
     '(zh ? "规划中…" : "Planning…")'),
]


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def batch_entries(batch):
    if batch == 0:
        return ENTRIES
    start = (batch - 1) * 5
    return ENTRIES[start:start + 5]


def split_pair(before):
    """Pull the two literals out of the exact before-snippet; nothing here is re-typed."""
    body = before.strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    m = TERNARY.match(body)
    if not m:
        raise SystemExit("ABORT cannot cut a zh/en pair out of: %r" % before)
    return m.group("zh"), m.group("en")


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def entry_line(key, value):
    return '  "%s": "%s",' % (key, value)


def do_dict(batch):
    text = read(DICT)
    nl = eol(text)
    entries = batch_entries(batch)
    anchor_en, anchor_zh = EN_ANCHOR, ZH_ANCHOR
    for key, before in entries:
        zh, en = split_pair(before)
        if text.count('"%s":' % key):
            raise SystemExit("ABORT key already in dictionary: %s" % key)
        for label, anchor, value in (("en", anchor_en, en), ("zh", anchor_zh, zh)):
            if text.count(anchor) != 1:
                raise SystemExit("ABORT anchor count %d for %r" % (text.count(anchor), anchor))
            new_line = entry_line(key, value)
            text = text.replace(anchor, anchor + nl + new_line, 1)
            if label == "en":
                anchor_en = new_line
            else:
                anchor_zh = new_line
    write(DICT, text)
    print("wrote %s keys, %s lines on each side" % (len(entries), len(entries)))
    return 0


def do_product(batch):
    text = read(PRODUCT)
    entries = batch_entries(batch)
    for key, before in entries:
        if text.count(before) != 1:
            raise SystemExit("ABORT before-snippet occurs %d times: %s" % (text.count(before), key))
        text = text.replace(before, 't("%s")' % key, 1)
    write(PRODUCT, text)
    print("moved %s reading points onto t()" % len(entries))
    return 0


def verify(batch):
    prod = read(PRODUCT)
    dic = read(DICT)
    bad = 0
    rows = []
    for key, before in batch_entries(batch):
        zh, en = split_pair(before)
        call = 't("%s")' % key
        prod_line = line_of(prod, prod.find(call)) if call in prod else -1
        left = prod.count(before)
        en_pos = dic.find(entry_line(key, en))
        zh_pos = dic.find(entry_line(key, zh))
        ok = prod_line > 0 and en_pos > 0 and zh_pos > 0 and left == 0
        if not ok:
            bad += 1
        rows.append("%-58s prod_line=%-5s leftover_before=%-2s dict_en=%-6s dict_zh=%-6s wording=%s" % (
            key,
            prod_line if prod_line > 0 else "absent",
            left,
            line_of(dic, en_pos) if en_pos > 0 else "absent",
            line_of(dic, zh_pos) if zh_pos > 0 else "absent",
            "identical" if ok else "REFUSED"))
    print("\n".join(rows))
    print("checked %s entries | refused %s" % (len(batch_entries(batch)), bad))
    return 1 if bad else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["dict", "product"])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--batch", type=int, required=True, choices=[0, 1, 2, 3])
    a = ap.parse_args()
    for p in (PRODUCT, DICT):
        if not os.path.isfile(p):
            raise SystemExit("ABORT no source at %s (lane root=%s)" % (p, ROOT))
    if a.verify:
        return verify(a.batch)
    if a.side == "dict":
        return do_dict(a.batch)
    if a.side == "product":
        return do_product(a.batch)
    raise SystemExit("ABORT give --side or --verify")


if __name__ == "__main__":
    sys.exit(main())
