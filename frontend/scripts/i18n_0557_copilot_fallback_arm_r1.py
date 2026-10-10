# -*- coding: utf-8 -*-
"""ORD-0557 arm for lane 键盘工: every row this batch moved must sit in the dictionary verbatim.

Reads the base tip's source lines and the working tree's dictionary; nothing is trusted from
the mover's own word. `--negative` salts one English value in memory only (disk untouched)
and requires the matching check to go red, so this file also proves the ruler bites.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/features/agent/CopilotDock.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
EV = os.path.join(TREE, "frontend", "scripts", "i18n_0557_copilot_fallback_evidence_r1.json")

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

evidence = json.load(open(EV, encoding="utf-8"))
BASE = evidence["base_tip"]
ITEMS = evidence["items"]


def git_show(rev, path):
    p = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (rev, path)], capture_output=True)
    if p.returncode != 0:
        sys.stdout.write("ABORT git show: " + p.stderr.decode("utf-8", "replace") + "\n")
        sys.exit(3)
    return p.stdout.decode("utf-8")


def dicts(text):
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    out = []
    for chunk in (text[i:j], text[j:k]):
        lines = chunk.split("\n")
        d = {}
        n = 0
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


def text_pairs(src):
    out = []
    for n, l in enumerate(src.split("\n"), 1):
        for m in PAIR.finditer(l):
            if m.group(1) == "zh" and m.group(2) == "en":
                continue
            out.append((n, m.group(1), m.group(2)))
    return out


def run_checks(salt_index=None):
    now_src = open(os.path.join(TREE, SRC_REL), encoding="utf-8").read()
    now_dict = open(os.path.join(TREE, DICT_REL), encoding="utf-8").read()
    base_src = git_show(BASE, SRC_REL)
    base_dict = git_show(BASE, DICT_REL)
    now_en, now_zh = dicts(now_dict)
    base_en, base_zh = dicts(base_dict)
    if salt_index is not None:
        now_en = dict(now_en)
        now_en[ITEMS[salt_index]["key"]] = "SALTED"

    names = [r["key"] for r in ITEMS]
    checks = {
        "parity_before": set(base_en) == set(base_zh),
        "parity_after": set(now_en) == set(now_zh),
        "keys_absent_at_base": all(r["key"] not in base_en and r["key"] not in base_zh for r in ITEMS),
        "keys_present_both_sides": all(r["key"] in now_en and r["key"] in now_zh for r in ITEMS),
        "inventory_drops_by_batch": len(text_pairs(base_src)) - len(text_pairs(now_src)) == len(ITEMS),
        "only_this_batch_added": (set(now_en) - set(base_en)) == (set(now_zh) - set(base_zh)) == set(names),
        "no_existing_text_changed": all(now_en[k2] == v for k2, v in base_en.items() if k2 in now_en)
                                    and all(now_zh[k2] == v for k2, v in base_zh.items() if k2 in now_zh),
    }
    for i, r in enumerate(ITEMS):
        inline = [p for p in text_pairs(base_src) if p[0] == r["base_line"]]
        screen_zh = inline[0][1] if inline else None
        screen_en = inline[0][2] if inline else None
        checks["row%d_base_line_has_one_pair" % (i + 1)] = len(inline) == 1
        checks["row%d_zh_matches_screen" % (i + 1)] = now_zh.get(r["key"]) == screen_zh
        checks["row%d_en_matches_screen" % (i + 1)] = now_en.get(r["key"]) == screen_en
        checks["row%d_site_reads_key_once" % (i + 1)] = now_src.count('t("%s")' % r["key"]) == 1
        checks["row%d_old_inline_gone" % (i + 1)] = ('zh ? "%s"' % screen_zh) not in now_src
        checks["row%d_draft_en_copied_verbatim" % (i + 1)] = screen_en == r["en"]
    green = [k2 for k2, v in checks.items() if v]
    red = [k2 for k2, v in checks.items() if not v]
    return green, red


def main():
    salt = "--negative" in sys.argv
    if salt:
        green, red = run_checks(salt_index=0)
        bites = "row1_en_matches_screen" in red
        sys.stdout.write("%s passed=%d failed=%s\n"
                         % ("NEGATIVE_CONTROL_BITES" if bites else "NEGATIVE_CONTROL_BLIND",
                            len(green), sorted(red)))
        sys.exit(0 if bites else 1)
    green, red = run_checks()
    sys.stdout.write("ARM i18n_0557_copilot_fallback: rows=%d green=%d red=%d %s\n"
                     % (len(ITEMS), len(green), len(red), sorted(red)))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
