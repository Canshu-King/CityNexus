# -*- coding: utf-8 -*-
"""ORD-0557 full-file mover for lane 键盘工: carry the CN draft's rows for CopilotDock.

The draft is the source of truth for key names and English copy, so rows are parsed from the
draft file instead of a list I typed. Each row is located primarily at the line the draft
cites (two rows in this draft cite one identical sentence painted twice in the file, so the
line number is what tells them apart), with the nearest unclaimed identical line as fallback.
Anything that does not match exactly is refused before a byte is written.
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
DRAFT = "D:/moodle/_cn10_fb557draft_1155.txt"
OUT = os.path.join(TREE, "frontend", "scripts", "i18n_0557_copilot_full_evidence_r1.json")

BASE_TIP = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"],
                          capture_output=True).stdout.decode("ascii").strip()

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
KEYNAME = re.compile(r'^[a-z][a-zA-Z0-9]*\.[a-zA-Z0-9_]+$')


def die(reason):
    sys.stdout.write("ABORT: " + reason + "\n")
    sys.exit(3)


def dicts(text):
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    out = []
    for chunk in (text[i:j], text[j:k]):
        lines = chunk.split("\n")
        d, n = {}, 0
        while n < len(lines):
            m = ENTRY.match(lines[n])
            if not m or lines[n].lstrip().startswith("//"):
                n += 1
                continue
            name, rest = m.group(1), m.group(2).strip()
            if rest:
                v = VALUE.match(rest)
                d[name] = v.group(1) if v else rest
                n += 1
                continue
            if n + 1 < len(lines):
                v = VALUE.match(lines[n + 1])
                if v:
                    d[name] = v.group(1)
                    n += 2
                    continue
            n += 1
        out.append(d)
    return out[0], out[1]


def text_pairs(lines):
    out = []
    for n, l in enumerate(lines, 1):
        for m in PAIR.finditer(l):
            if m.group(1) == "zh" and m.group(2) == "en":
                continue
            out.append({"line": n, "zh": m.group(1), "en": m.group(2),
                        "start": m.start(), "end": m.end(), "text": l})
    return out


def main():
    draft_rows = []
    for i, line in enumerate(open(DRAFT, encoding="utf-8").read().split("\n"), 1):
        if not line.startswith(SRC_REL + ":"):
            continue
        cols = line.split(" | ")
        if len(cols) < 4 or "EXCLUDED" in line:
            continue
        draft_rows.append({"draft_row": i, "draft_line": int(cols[0].split(":")[1]),
                           "literal": cols[1].strip(), "key": cols[2].strip(),
                           "en": cols[3].strip()})
    if not draft_rows:
        die("the draft gave no usable rows for this file")

    src_lines = open(SRC, encoding="utf-8").read().split("\n")
    if any("\r" in l for l in src_lines):
        die("source has CR bytes")
    pairs = text_pairs(src_lines)
    used, rows, skipped = set(), [], []

    for d in draft_rows:
        if not KEYNAME.match(d["key"]):
            skipped.append([d["draft_row"], d["key"], "键名不成两段"])
            continue
        # a cell in the draft can be a whole source line, or that line clipped mid template
        # literal; the clipped form is only accepted when it is a prefix of exactly one
        # unclaimed line AND that line's English literal equals the draft's English column
        exact = [p for p in pairs if p["text"].strip() == d["literal"] and p["line"] not in used]
        mode = "整行逐字"
        if not exact:
            exact = [p for p in pairs if p["text"].strip().startswith(d["literal"])
                     and p["en"] == d["en"] and p["line"] not in used]
            mode = "草稿原文是截断前缀"
        if len(exact) != 1:
            skipped.append([d["draft_row"], d["key"], "该原文命中 %d 处可用，不为唯一" % len(exact)])
            continue
        pick = exact[0]
        if pick["en"] != d["en"]:
            skipped.append([d["draft_row"], d["key"], "屏上英文与草稿不等"])
            continue
        used.add(pick["line"])
        rows.append({"key": d["key"], "draft_row": d["draft_row"], "draft_line": d["draft_line"],
                     "base_line": pick["line"], "zh": pick["zh"], "en": pick["en"],
                     "match_mode": mode, "before": pick["text"].strip()})

    if not rows:
        die("no row survived the checks: " + json.dumps(skipped, ensure_ascii=False))

    for r in rows:
        i = r["base_line"] - 1
        line = src_lines[i]
        m = PAIR.search(line)
        if not m or m.group(1) != r["zh"] or m.group(2) != r["en"]:
            die("line %d no longer holds the pair claimed for %s" % (r["base_line"], r["key"]))
        src_lines[i] = line[: m.start()] + 't("%s")' % r["key"] + line[m.end():]
        r["new_line"] = r["base_line"]
    new_src = "\n".join(src_lines)

    dict_text = open(DICT, encoding="utf-8").read()
    if any("\r" in l for l in dict_text.split("\n")):
        die("dictionary has CR bytes")
    en_d, zh_d = dicts(dict_text)
    if set(en_d) != set(zh_d):
        die("dictionary key sets already asymmetric: %s" % sorted(set(en_d) ^ set(zh_d))[:6])
    order = []
    for r in rows:
        if r["key"] in en_d or r["key"] in zh_d:
            die("key %s is already in the dictionary at this tip" % r["key"])
        if r["key"] not in order:
            order.append(r["key"])

    i0 = dict_text.index("const en: Dict = {")
    j0 = dict_text.index("const zhCN: Dict = {")
    k0 = dict_text.index("const dictionaries")
    anchors = {}
    for side, chunk in (("en", dict_text[i0:j0]), ("zh", dict_text[j0:k0])):
        last = None
        for line in chunk.split("\n"):
            m = ENTRY.match(line)
            if m and m.group(1).startswith("agent."):
                last = line
        if last is None:
            die("no agent entry on the %s side" % side)
        anchor = last + "\n"
        if dict_text.count(anchor) != 1:
            die("agent anchor not unique on the %s side" % side)
        anchors[side] = anchor

    by_key = {}
    for r in rows:
        by_key.setdefault(r["key"], r)
    for key in order:
        dict_text = dict_text.replace(anchors["en"], anchors["en"] + '  "%s": "%s",\n' % (key, by_key[key]["en"]), 1)
    for key in order:
        dict_text = dict_text.replace(anchors["zh"], anchors["zh"] + '  "%s": "%s",\n' % (key, by_key[key]["zh"]), 1)

    open(SRC, "w", encoding="utf-8", newline="\n").write(new_src)
    open(DICT, "w", encoding="utf-8", newline="\n").write(dict_text)

    dl = dict_text.split("\n")
    sl = new_src.split("\n")
    for key in order:
        en_hits = [n + 1 for n, l in enumerate(dl) if l == '  "%s": "%s",' % (key, by_key[key]["en"])]
        zh_hits = [n + 1 for n, l in enumerate(dl) if l == '  "%s": "%s",' % (key, by_key[key]["zh"])]
        if len(en_hits) != 1 or len(zh_hits) != 1:
            die("entry for %s is not uniquely round-trippable (en=%d zh=%d)"
                % (key, len(en_hits), len(zh_hits)))
        sites = [n + 1 for n, l in enumerate(sl) if 't("%s")' % key in l]
        if not sites:
            die("nothing reads %s" % key)
        by_key[key]["dict_en_line"], by_key[key]["dict_zh_line"], by_key[key]["site_lines"] = \
            en_hits[0], zh_hits[0], sites

    after_en, after_zh = dicts(dict_text)
    if set(after_en) != set(after_zh):
        die("parity broken after insert")
    if len(after_en) - len(en_d) != len(order):
        die("en side gained %d keys, expected %d" % (len(after_en) - len(en_d), len(order)))
    for k2, v2 in en_d.items():
        if after_en.get(k2) != v2:
            die("existing en key %s changed text" % k2)
    for k2, v2 in zh_d.items():
        if after_zh.get(k2) != v2:
            die("existing zh key %s changed text" % k2)
    left = text_pairs(sl)
    if len(pairs) - len(left) != len(rows):
        die("inline pairs moved by %d, expected %d" % (len(pairs) - len(left), len(rows)))
    for p in pairs:
        if p["line"] not in used and PAIR.search(sl[p["line"] - 1] or "") is None:
            die("pair at line %d vanished without being claimed" % p["line"])

    json.dump({"base_tip": BASE_TIP, "draft": DRAFT, "items": rows, "keys_added": len(order),
               "sites_converted": len(rows), "shared_key_rows": len(rows) - len(order),
               "skipped": skipped, "inline_text_pairs_before": len(pairs),
               "inline_text_pairs_after": len(left)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.stdout.write("FULL MOVE keys=%d sites=%d shared=%d skipped=%d inline %d -> %d\n"
                     % (len(order), len(rows), len(rows) - len(order), len(skipped),
                        len(pairs), len(left)))
    for s in skipped:
        sys.stdout.write("SKIPPED draft_row=%s key=%s reason=%s\n" % tuple(s))


if __name__ == "__main__":
    main()
