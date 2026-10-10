# -*- coding: utf-8 -*-
"""ORD-0557 batch one for lane 键盘工: CopilotDock 兜底行表里 :458 那一枚.

The zh text is read off the source line; the en text is taken from the CN draft column and
then asserted against the source, so a mis-copy between draft and screen shows up here
instead of on the traveller's screen. Refuses to write unless every check passes.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/features/agent/CopilotDock.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
SRC = os.path.join(TREE, SRC_REL)
DICT = os.path.join(TREE, DICT_REL)
OUT = os.path.join(TREE, "frontend", "scripts", "i18n_0557_copilot_fallback_evidence_r1.json")

BASE_TIP = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"],
                          capture_output=True).stdout.decode("ascii").strip()

# (line on the base tip, key from the draft, en text exactly as the draft column spells it)
ITEMS = [
    (242, "agent.streamUnparseable", "A runtime event could not be read"),
    (253, "agent.streamReconnecting", "Reconnecting to runtime events"),
    (458, "agent.needsConfirmation", "Needs your confirmation"),
]
DRAFT_SOURCE = "D:/moodle/_cn10_fb557draft_1155.txt"

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE_ON_LINE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def die(reason):
    sys.stdout.write("ABORT: " + reason + "\n")
    sys.exit(3)


def dicts(text):
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    out = {}
    for name, chunk in (("en", text[i:j]), ("zh", text[j:k])):
        lines = chunk.split("\n")
        d = {}
        order = []
        n = 0
        while n < len(lines):
            m = ENTRY.match(lines[n])
            if not m or lines[n].lstrip().startswith("//"):
                n += 1
                continue
            key, rest = m.group(1), m.group(2).strip()
            if rest:
                v = VALUE_ON_LINE.match(rest)
                d[key] = v.group(1) if v else rest
                order.append(key)
                n += 1
                continue
            if n + 1 < len(lines):
                v = VALUE_ON_LINE.match(lines[n + 1])
                if v:
                    d[key] = v.group(1)
                    order.append(key)
                    n += 2
                    continue
            n += 1
        out[name] = d
        out[name + "_order"] = order
    return out


def text_pairs(lines):
    out = []
    for n, l in enumerate(lines, 1):
        for m in PAIR.finditer(l):
            if m.group(1) == "zh" and m.group(2) == "en":
                continue
            out.append((n, m.group(1), m.group(2)))
    return out


def main():
    src = open(SRC, encoding="utf-8").read()
    if "\r" in src:
        die("source has CR bytes")
    base_pairs = text_pairs(src.split("\n"))
    lines = src.split("\n")

    # the draft must actually name this row, otherwise I am inventing a key
    draft_lines = open(DRAFT_SOURCE, encoding="utf-8").read().split("\n")
    rows = []
    for line_no, key, draft_en in ITEMS:
        hits = [l for l in draft_lines if l.startswith("%s:%d |" % (SRC_REL, line_no))]
        if len(hits) != 1:
            die("draft has %d rows for line %d, expected one" % (len(hits), line_no))
        cols = hits[0].split(" | ")
        if cols[2].strip() != key:
            die("draft key for line %d is %r, script says %r" % (line_no, cols[2], key))

        idx = line_no - 1
        found = list(PAIR.finditer(lines[idx]))
        if len(found) != 1:
            die("line %d holds %d pairs" % (line_no, len(found)))
        m = found[0]
        zh_text, en_text = m.group(1), m.group(2)
        if en_text != draft_en:
            die("screen en %r differs from draft en %r" % (en_text, draft_en))
        before = lines[idx]
        after = before[: m.start()] + 't("%s")' % key + before[m.end():]
        lines[idx] = after
        rows.append({"key": key, "base_line": line_no, "new_line": line_no,
                     "zh": zh_text, "en": en_text, "draft_row": hits[0],
                     "before": before.strip(), "after": after.strip()})

    new_src = "\n".join(lines)
    open(SRC, "w", encoding="utf-8", newline="\n").write(new_src)

    dict_text = open(DICT, encoding="utf-8").read()
    if "\r" in dict_text:
        die("dictionary has CR bytes")
    parsed = dicts(dict_text)
    if set(parsed["en"]) != set(parsed["zh"]):
        die("dictionary key sets already asymmetric before I add: %s"
            % sorted(set(parsed["en"]) ^ set(parsed["zh"]))[:6])
    for r in rows:
        if r["key"] in parsed["en"] or r["key"] in parsed["zh"]:
            die("key %s already in the dictionary at this tip" % r["key"])

    anchors = {}
    i = dict_text.index("const en: Dict = {")
    j = dict_text.index("const zhCN: Dict = {")
    k = dict_text.index("const dictionaries")
    for side, chunk in (("en", dict_text[i:j]), ("zh", dict_text[j:k])):
        last = None
        for line in chunk.split("\n"):
            m = ENTRY.match(line)
            if m and m.group(1).startswith("agent."):
                last = line
        if last is None:
            die("no agent entry found on the %s side" % side)
        # the anchor keeps its newline: without it the new entry gets glued onto the
        # anchor's own line and the dictionary reads as one broken row
        anchor = last + "\n"
        if dict_text.count(anchor) != 1:
            die("anchor not unique on the %s side: count=%d" % (side, dict_text.count(anchor)))
        anchors[side] = anchor

    for r in rows:
        for side in ("en", "zh"):
            add = '  "%s": "%s",\n' % (r["key"], r[side])
            dict_text = dict_text.replace(anchors[side], anchors[side] + add, 1)
    open(DICT, "w", encoding="utf-8", newline="\n").write(dict_text)

    after_dict = open(DICT, encoding="utf-8").read()
    after_parsed = dicts(after_dict)
    after_src = open(SRC, encoding="utf-8").read()
    dl = after_dict.split("\n")
    sl = after_src.split("\n")

    for r in rows:
        r["dict_en_line"] = [n + 1 for n, l in enumerate(dl) if l == '  "%s": "%s",' % (r["key"], r["en"])][0]
        r["dict_zh_line"] = [n + 1 for n, l in enumerate(dl) if l == '  "%s": "%s",' % (r["key"], r["zh"])][0]
        r["new_line"] = [n + 1 for n, l in enumerate(sl) if 't("%s")' % r["key"] in l][0]
        if after_src.count('t("%s")' % r["key"]) != 1:
            die("site for %s not read exactly once" % r["key"])
        if after_parsed["en"].get(r["key"]) != r["en"] or after_parsed["zh"].get(r["key"]) != r["zh"]:
            die("value not round-trippable for %s" % r["key"])

    if set(after_parsed["en"]) != set(after_parsed["zh"]):
        die("parity broken after insert")
    now_pairs = text_pairs(sl)
    if len(base_pairs) - len(now_pairs) != len(rows):
        die("inline text pair inventory moved by %d, expected %d"
            % (len(base_pairs) - len(now_pairs), len(rows)))
    for n, zh_t, en_t in base_pairs:
        if (n, zh_t, en_t) not in now_pairs and not any(r["base_line"] == n for r in rows):
            die("pair at line %d vanished without being mine" % n)

    json.dump({"base_tip": BASE_TIP, "draft_source": DRAFT_SOURCE, "items": rows,
               "inline_text_pairs_before": len(base_pairs),
               "inline_text_pairs_after": len(now_pairs)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.stdout.write("MOVED %d row(s); inline text pairs %d -> %d\n"
                     % (len(rows), len(base_pairs), len(now_pairs)))
    for r in rows:
        sys.stdout.write("  %s | src %d->%d | dict en %d zh %d\n"
                         % (r["key"], r["base_line"], r["new_line"],
                            r["dict_en_line"], r["dict_zh_line"]))


if __name__ == "__main__":
    main()
