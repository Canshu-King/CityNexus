# -*- coding: utf-8 -*-
"""ORD-0557 arm for lane 键盘工: the :458 fallback row must sit in the dictionary verbatim.

Reads the base tip's source line and the working tree's dictionary; nothing is trusted from
the mover's own word. `--negative` salts the English value in memory only (the tree is not
touched) and requires the same checks to go red, so this file also proves the ruler bites.
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
row = evidence["items"][0]
key = row["key"]


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


def run_checks(salt_en=None):
    """(passed, failed_names). salt_en replaces the English dictionary value in memory."""
    now_src = open(os.path.join(TREE, SRC_REL), encoding="utf-8").read()
    now_dict = open(os.path.join(TREE, DICT_REL), encoding="utf-8").read()
    base_src = git_show(BASE, SRC_REL)
    base_dict = git_show(BASE, DICT_REL)
    now_en, now_zh = dicts(now_dict)
    base_en, base_zh = dicts(base_dict)

    inline = [p for p in text_pairs(base_src) if p[0] == row["base_line"]]
    if len(inline) != 1:
        return [], ["base_line_holds_exactly_one_pair"]

    screen_zh, screen_en = inline[0][1], inline[0][2]
    if salt_en is not None:
        now_en = dict(now_en)
        now_en[key] = salt_en

    checks = {
        "parity_before": set(base_en) == set(base_zh),
        "parity_after": set(now_en) == set(now_zh),
        "key_absent_at_base": key not in base_en and key not in base_zh,
        "key_present_both_sides": key in now_en and key in now_zh,
        "zh_matches_screen": now_zh.get(key) == screen_zh,
        "en_matches_screen": now_en.get(key) == screen_en,
        "draft_and_screen_agree": screen_en == row["en"],
        "site_reads_key_once": now_src.count('t("%s")' % key) == 1,
        "old_inline_gone": PAIR.search(base_src.split("\n")[row["base_line"] - 1]) is not None
                           and ('zh ? "%s"' % screen_zh) not in now_src,
        "inventory_drops_by_one": len(text_pairs(base_src)) - len(text_pairs(now_src)) == 1,
        "only_this_key_added": (set(now_en) - set(base_en)) == (set(now_zh) - set(base_zh)) == {key},
        "no_existing_text_changed": all(now_en[k2] == v for k2, v in base_en.items() if k2 in now_en)
                                    and all(now_zh[k2] == v for k2, v in base_zh.items() if k2 in now_zh),
    }
    return [k2 for k2, v in checks.items() if v], [k2 for k2, v in checks.items() if not v]


def main():
    salt = "--negative" in sys.argv
    passed, failed = run_checks(salt_en="SALTED" if salt else None)
    if salt:
        verdict = "NEGATIVE_CONTROL_BITES" if (failed and "en_matches_screen" in failed) else "NEGATIVE_CONTROL_BLIND"
        sys.stdout.write("%s passed=%d failed=%s\n" % (verdict, len(passed), sorted(failed)))
        sys.exit(0 if verdict == "NEGATIVE_CONTROL_BITES" else 1)
    sys.stdout.write("ARM i18n_0557_copilot_fallback: green=%d red=%d %s\n"
                     % (len(passed), len(failed), sorted(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
