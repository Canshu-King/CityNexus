# -*- coding: utf-8 -*-
u"""现尖内联双语分母尺：把 `zh ? "中文" : "English"` 这类面拆成三档，只数能零新键改读字典的那一档。

为什么要再来一把（10-10 00:0x 现读）：号令者播报 ORD-0549「表上已无空位，代码里还剩 22 枚」，
而 `grep -c 'zh ? "'` 在现尖给的是 205 —— 两个数都没错，但它们量的不是同一件事。205 里混着
`zh ? "\\u3001" : ", "` 这种**分隔符三元**（不是旅客可见文案），也混着字典里根本没有对应键、
必须新加键才能搬的（那不是 0549 的形制）。这张单真正缺的是一枚能复跑的现尖分母，
所以这里一次出三档，并把每一枚的 `文件:行` 摊出来，谁伸手之前自己数。

退出码：0 出数 / 2 字典或源码读不到（绝不把读不到折成「没有」）。
用法：python inline_bilingual_inventory_r1.py [--root <frontend/src>] [--json <落盘路径>]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

LOCALE = "i18n/LocaleContext.tsx"
# A dictionary entry:  "key": "value",   with the value allowed to carry escapes.
ENTRY = re.compile(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"')
# A bilingual ternary on the `zh` boolean, either order, double or single quotes.
TERNARY = re.compile(
    r"""\bzh\s*\?\s*(?P<a>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')\s*:\s*(?P<b>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')"""
)
SKIP_BASENAMES = {"LocaleContext.tsx"}


def jstr(lit: str) -> str:
    u"""Turn a source literal (with its quotes) into the string it denotes."""
    try:
        return json.loads(lit)
    except Exception:
        # A single-quoted JS string is not valid JSON; keep it verbatim minus the quotes rather
        # than dropping the site, because a silently skipped site reads as a smaller denominator.
        return lit[1:-1]


def dict_block(text: str, name: str) -> dict:
    u"""Grab `const <name>: Dict = { ... };` by brace balance, then parse its entries."""
    start = text.find("const %s: Dict = {" % name)
    if start < 0:
        raise RuntimeError("dictionary block %r not found" % name)
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                body = text[i + 1 : j]
                out = {}
                unparsed = 0
                for m in ENTRY.finditer(body):
                    out[jstr('"%s"' % m.group(1))] = jstr('"%s"' % m.group(2))
                lines = len([x for x in body.splitlines() if x.strip()])
                if lines - len(out) > 0:
                    unparsed = lines - len(out)
                return {"entries": out, "unparsed_lines": unparsed, "raw_lines": lines}
    raise RuntimeError("unbalanced braces in %r" % name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\moodle\_qoder_tooltip_1008\frontend\src")
    ap.add_argument("--json", default="")
    ap.add_argument("--md", default="")
    a = ap.parse_args()

    locale_path = os.path.join(a.root, LOCALE)
    if not os.path.isfile(locale_path):
        sys.stdout.write(u"读不到字典原件：%s\n" % locale_path)
        return 2
    text = io.open(locale_path, encoding="utf-8").read()
    try:
        en = dict_block(text, "en")
        zh = dict_block(text, "zhCN")
    except RuntimeError as exc:
        sys.stdout.write(u"字典解析失败：%s\n" % exc)
        return 2

    # A pair the dictionary can already answer: same key, both sides present.
    twins = {}
    for key, en_val in en["entries"].items():
        zh_val = zh["entries"].get(key)
        if zh_val is None:
            continue
        twins[(en_val, zh_val)] = key

    files = []
    for dirpath, dirnames, filenames in os.walk(a.root):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "generated")]
        for fn in filenames:
            if fn.endswith(".tsx") and fn not in SKIP_BASENAMES:
                files.append(os.path.join(dirpath, fn))
    files.sort()

    per_file = {}
    twin_sites = []
    counts = {
        "ternaries_total": 0,
        "separator_like": 0,
        "twin_exists": 0,
        "no_twin": 0,
        "reversed_order_twin": 0,
    }
    for path in files:
        src = io.open(path, encoding="utf-8").read().splitlines()
        rel = os.path.relpath(path, a.root).replace("\\", "/")
        mine = {"total": 0, "twin": 0, "separator": 0, "no_twin": 0}
        for no, line in enumerate(src, 1):
            for m in TERNARY.finditer(line):
                first, second = jstr(m.group("a")), jstr(m.group("b"))
                counts["ternaries_total"] += 1
                mine["total"] += 1
                # A separator ternary picks a punctuation mark, not a sentence: not traveller copy.
                if len(first) <= 2 or len(second) <= 2:
                    counts["separator_like"] += 1
                    mine["separator"] += 1
                    continue
                key = twins.get((second, first))
                if key is None:
                    key = twins.get((first, second))
                if key is not None:
                    counts["twin_exists"] += 1
                    mine["twin"] += 1
                    twin_sites.append({"file": rel, "line": no, "key": key, "zh": first if len(first) > len(second) else second})
                else:
                    counts["no_twin"] += 1
                    mine["no_twin"] += 1
        if mine["total"]:
            per_file[rel] = mine

    out = {
        "dictionary": {"en_entries": len(en["entries"]), "zh_entries": len(zh["entries"]),
                       "en_unparsed_lines": en["unparsed_lines"], "zh_unparsed_lines": zh["unparsed_lines"],
                       "pairs_answerable": len(twins)},
        "counts": counts,
        "per_file": per_file,
        "twin_sites": twin_sites,
    }
    blob = json.dumps(out, ensure_ascii=False, indent=1)
    if a.json:
        io.open(a.json, "w", encoding="utf-8", newline="\n").write(blob)
    if a.md:
        # A sheet the delivery block can cite by line: the ruler's own vouching pattern accepts
        # .md and .json paths with a line number, so the numbers land somewhere retrievable
        # instead of being retyped into prose.
        rows = [u"# 现尖内联双语分母（由 inline_bilingual_inventory_r1.py 生成，重跑即覆盖）", u""]
        rows.append(u"- 字典 en 条目 %d｜zhCN 条目 %d｜两侧都有值的键 %d 枚"
                    % (len(en["entries"]), len(zh["entries"]), len(twins)))
        rows.append(u"- 三元总 %d 枚" % counts["ternaries_total"])
        rows.append(u"- 分隔符类（非旅客可见文案）%d 枚" % counts["separator_like"])
        rows.append(u"- 字典已有这段字、零新键可改 %d 枚" % counts["twin_exists"])
        rows.append(u"- 需要新键才搬得动 %d 枚" % counts["no_twin"])
        rows.append(u"- 带三元的文件 %d 枚" % len(per_file))
        rows.append(u"")
        rows.append(u"## 可改那九枚逐枚点名")
        rows.append(u"")
        for s in twin_sites:
            rows.append(u"- %s:%d 键 %s" % (s["file"], s["line"], s["key"]))
        rows.append(u"")
        io.open(a.md, "w", encoding="utf-8", newline="\n").write(u"\n".join(rows))
    sys.stdout.write(u"字典：en 条目 %d、zhCN 条目 %d、两侧都有值的键 %d 枚\n"
                     % (len(en["entries"]), len(zh["entries"]), len(twins)))
    sys.stdout.write(u"三元总 %d 枚｜分隔符类 %d 枚｜字典已有这段字 %d 枚｜需要新键 %d 枚\n"
                     % (counts["ternaries_total"], counts["separator_like"], counts["twin_exists"], counts["no_twin"]))
    sys.stdout.write(u"带三元的文件 %d 枚：\n" % len(per_file))
    for rel in sorted(per_file, key=lambda k: (-per_file[k]["twin"], k)):
        v = per_file[rel]
        sys.stdout.write(u"  %-58s 可改 %2d｜需新键 %2d｜分隔符 %2d｜%s\n"
                         % (rel, v["twin"], v["no_twin"], v["separator"], os.path.join(a.root, rel)))
    if not counts["ternaries_total"]:
        sys.stdout.write(u"注意：扫到 0 枚三元 —— 这是尺没起来，不是代码里没有。\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
