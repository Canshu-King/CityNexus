# -*- coding: utf-8 -*-
"""ORD-0576 batch for lane 键盘工: main.tsx's four visible strings onto both dictionary sides.

The four are read off the tip's own bytes: three `<option>` labels written on one line each,
and the composer's prefilled command (a module-level const today). All four read the same in
Chinese and in English today, so both sides get the same string -- this moves words behind a
key, it does not translate them.

Every check runs on in-memory text; the two files are written only when all checks pass.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/main.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
SRC = os.path.join(TREE, SRC_REL)
DICT = os.path.join(TREE, DICT_REL)
OUT = os.path.join(TREE, "frontend", "scripts", "i18n_0576_main_move_evidence_r1.json")
FAMILY = "main."
OPTIONS = [(1297, "ADVISORY", "main.modeAdvisory"),
           (1298, "ASSISTED", "main.modeAssisted"),
           (1299, "AUTONOMOUS", "main.modeAutonomous")]
CONST_LINES = (56, 57)
CONST_USE = 192
PREFILL_KEY = "main.demoAgentCommand"

OPTION_RE = re.compile(r'^(\s*)<option value="([A-Z]+)">([^<>{}]+)</option>$')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE = re.compile(r'^"((?:[^"\\]|\\.)*)"\s*,?\s*$')
CJK = re.compile(u"[\u3400-\u9fff]")


def die(reason):
    sys.stdout.write("ABORT: " + reason + "\n")
    sys.exit(3)


def split_sides(text):
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    return {"en": text[i:j], "zh": text[j:k]}


def parse(chunk):
    lines, d, n = chunk.split("\n"), {}, 0
    while n < len(lines):
        m = ENTRY.match(lines[n])
        if not m or lines[n].lstrip().startswith("//"):
            n += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest:
            v = VALUE.match(rest)
            d[key] = v.group(1) if v else rest
            n += 1
            continue
        if n + 1 < len(lines):
            v = VALUE.match(lines[n + 1].strip())
            if v:
                d[key] = v.group(1)
                n += 2
                continue
        n += 1
    return d


def main():
    base_tip = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"],
                              capture_output=True).stdout.decode("ascii").strip()
    src_text = open(SRC, encoding="utf-8").read()
    if "\r" in src_text:
        die("main.tsx has CR bytes")
    lines = src_text.split("\n")
    dict_text = open(DICT, encoding="utf-8").read()
    sides = split_sides(dict_text)
    en_d, zh_d = parse(sides["en"]), parse(sides["zh"])
    if set(en_d) != set(zh_d):
        die("dictionary key sets already asymmetric: %s" % sorted(set(en_d) ^ set(zh_d))[:6])

    rows, seen_text = [], set()
    for line_no, value, key in OPTIONS:
        m = OPTION_RE.match(lines[line_no - 1])
        if not m:
            die("line %d is not a one-line <option value=\"%s\">LABEL</option>" % (line_no, value))
        if m.group(2) != value:
            die("line %d names %s, the order says %s" % (line_no, m.group(2), value))
        text = m.group(3).strip()
        if not CJK.search(text):
            die("line %d holds no Chinese for a traveller to read" % line_no)
        if text in seen_text or key in en_d or key in zh_d:
            die("label or key already taken at line %d" % line_no)
        seen_text.add(text)
        rows.append({"kind": "option label", "key": key, "base_line": line_no, "new_line": line_no,
                     "zh": text, "en": text,
                     "geometry": "标签、文字、闭括号在同一行；改后该行只剩 {t(键)}",
                     "before": lines[line_no - 1].strip(),
                     "after": '%s<option value="%s">{t("%s")}</option>' % (m.group(1), value, key)})
        lines[line_no - 1] = '%s<option value="%s">{t("%s")}</option>' % (m.group(1), value, key)

    const_name = re.search(r"^const (defaultAgentCommand) =$", lines[CONST_LINES[0] - 1])
    const_lit = re.match(r'^\s*"((?:[^"\\]|\\.)*)";$', lines[CONST_LINES[1] - 1])
    if not const_name or not const_lit:
        die("the prefilled command const is not the two-line shape named at lines %s" % (CONST_LINES,))
    pre_text = const_lit.group(1)
    if not CJK.search(pre_text):
        die("the prefilled command holds no Chinese")
    if PREFILL_KEY in en_d or PREFILL_KEY in zh_d:
        die("key %s already in the dictionary" % PREFILL_KEY)
    uses = [n + 1 for n, l in enumerate(lines) if "defaultAgentCommand" in l]
    if uses != [CONST_LINES[0], CONST_USE]:
        die("defaultAgentCommand appears at %s, expected its name line and one use" % uses)
    if "useState(defaultAgentCommand)" not in lines[CONST_USE - 1]:
        die("line %d is not the useState call" % CONST_USE)
    if "const t = useT();" not in "\n".join(lines[:CONST_USE - 1]):
        die("no useT() before the consume line, so t() is not in scope there")
    before_use = lines[CONST_USE - 1]
    after_use = before_use.replace("useState(defaultAgentCommand)", 'useState(t("%s"))' % PREFILL_KEY)
    lines[CONST_USE - 1] = after_use
    rows.append({"kind": "prefilled command", "key": PREFILL_KEY, "base_line": CONST_USE,
                 "new_line": CONST_USE - 2, "zh": pre_text, "en": pre_text,
                 "geometry": "原来是模块级常量两行（名一行、字一行）加一处 useState；常量整块删掉，只剩 useState 读键",
                 "before": before_use.strip(), "after": after_use.strip(),
                 "const_removed": "%s:%d-%d" % (SRC_REL, CONST_LINES[0], CONST_LINES[1])})
    del lines[CONST_LINES[0] - 1:CONST_LINES[1]]
    if any("defaultAgentCommand" in l for l in lines):
        die("defaultAgentCommand is still referenced after the move")

    new_src = "\n".join(lines)
    for r in rows:
        if new_src.count('t("%s")' % r["key"]) != 1:
            die("%s is not read exactly once" % r["key"])
        if '"%s"' % r["zh"] in new_src or (">%s<" % r["zh"]) in new_src:
            die("the old literal for %s is still in main.tsx" % r["key"])

    anchors = {}
    for side in ("en", "zh"):
        last = None
        for line in sides[side].split("\n"):
            m = ENTRY.match(line)
            if m and m.group(1).startswith(FAMILY):
                last = line
        if last is None:
            die("no %s key on the %s side" % (FAMILY, side))
        anchor = last + "\n"
        if dict_text.count(anchor) != 1:
            die("the %s anchor is not unique" % side)
        anchors[side] = anchor
    for r in rows:
        dict_text = dict_text.replace(anchors["en"], anchors["en"] + '  "%s": "%s",\n' % (r["key"], r["en"]), 1)
    for r in rows:
        dict_text = dict_text.replace(anchors["zh"], anchors["zh"] + '  "%s": "%s",\n' % (r["key"], r["zh"]), 1)

    new_sides = split_sides(dict_text)
    a_en, a_zh = parse(new_sides["en"]), parse(new_sides["zh"])
    if set(a_en) != set(a_zh):
        die("parity broken after insert")
    if (set(a_en) - set(en_d)) != {r["key"] for r in rows} or (set(a_zh) - set(zh_d)) != {r["key"] for r in rows}:
        die("a side gained the wrong key set")
    for k, v in en_d.items():
        if a_en.get(k) != v:
            die("existing en key %s changed text" % k)
    for k, v in zh_d.items():
        if a_zh.get(k) != v:
            die("existing zh key %s changed text" % k)

    def place(side, key, val):
        offset = len(dict_text[:dict_text.index(new_sides[side])].split("\n"))
        for n, line in enumerate(new_sides[side].split("\n"), 1):
            if line == '  "%s": "%s",' % (key, val):
                return offset + n - 1
        die("%s not placed on the %s side" % (key, side))

    sl = new_src.split("\n")
    for r in rows:
        r["dict_en_line"] = place("en", r["key"], r["en"])
        r["dict_zh_line"] = place("zh", r["key"], r["zh"])
        sites = [n + 1 for n, l in enumerate(sl) if 't("%s")' % r["key"] in l]
        if len(sites) != 1:
            die("%s read at %s" % (r["key"], sites))
        r["new_line"] = sites[0]

    open(SRC, "w", encoding="utf-8", newline="\n").write(new_src)
    open(DICT, "w", encoding="utf-8", newline="\n").write(dict_text)
    base_src = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (base_tip, SRC_REL)],
                              capture_output=True).stdout.decode("utf-8")

    def cjk_lines(t):
        return len([l for l in t.split("\n") if CJK.search(l) and not l.lstrip().startswith(("*", "//"))])

    json.dump({"base_tip": base_tip, "family": FAMILY, "items": rows,
               "cjk_lines_before": cjk_lines(base_src), "cjk_lines_after": cjk_lines(new_src)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.stdout.write("MOVED %d rows; CJK-bearing lines %d -> %d\n"
                     % (len(rows), cjk_lines(base_src), cjk_lines(new_src)))
    for r in rows:
        sys.stdout.write("  %s ｜ 源 %d->%d ｜ 字典 en %d / zh %d ｜ %r\n"
                         % (r["key"], r["base_line"], r["new_line"], r["dict_en_line"],
                            r["dict_zh_line"], r["zh"][:30]))


if __name__ == "__main__":
    main()
