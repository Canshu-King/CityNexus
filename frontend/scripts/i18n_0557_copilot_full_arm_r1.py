# -*- coding: utf-8 -*-
"""ORD-0557 full-batch arm for lane 键盘工: grade the tree against the tip and the draft.

Independent of the mover: it re-reads the tip's source, the draft's rows and the working
tree, and re-derives every claim. `--negative` salts one English value in memory (disk
untouched) and requires the matching check to go red.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/features/agent/CopilotDock.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
EV = os.path.join(TREE, "frontend", "scripts", "i18n_0557_copilot_full_evidence_r1.json")
DRAFT = "D:/moodle/_cn10_fb557draft_1155.txt"

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

ev = json.load(open(EV, encoding="utf-8"))
BASE, ROWS = ev["base_tip"], ev["items"]


def git_show(rev, path):
    p = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (rev, path)], capture_output=True)
    if p.returncode != 0:
        sys.stdout.write("ABORT git show " + p.stderr.decode("utf-8", "replace") + "\n")
        sys.exit(3)
    return p.stdout.decode("utf-8")


def dicts(text):
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    out = []
    for chunk in (text[i:j], text[j:k]):
        lines, d, n = chunk.split("\n"), {}, 0
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


def text_pairs(text):
    out = []
    for n, l in enumerate(text.split("\n"), 1):
        for m in PAIR.finditer(l):
            if m.group(1) == "zh" and m.group(2) == "en":
                continue
            out.append((n, m.group(1), m.group(2)))
    return out


def draft_rows():
    rows = {}
    for i, line in enumerate(open(DRAFT, encoding="utf-8").read().split("\n"), 1):
        if not line.startswith(SRC_REL + ":") or "EXCLUDED" in line:
            continue
        cols = line.split(" | ")
        if len(cols) < 4:
            continue
        rows[i] = {"key": cols[2].strip(), "en": cols[3].strip(),
                   "literal": cols[1].strip(), "line": int(cols[0].split(":")[1])}
    return rows


def run(salt_key=None):
    base_src = git_show(BASE, SRC_REL)
    now_src = open(os.path.join(TREE, SRC_REL), encoding="utf-8").read()
    base_en, base_zh = dicts(git_show(BASE, DICT_REL))
    now_en, now_zh = dicts(open(os.path.join(TREE, DICT_REL), encoding="utf-8").read())
    if salt_key:
        now_en = dict(now_en)
        now_en[salt_key] = "SALTED"
    dr = draft_rows()
    base_pairs = text_pairs(base_src)
    now_pairs = text_pairs(now_src)
    keys = sorted({r["key"] for r in ROWS})
    checks = {
        "parity_before": set(base_en) == set(base_zh),
        "parity_after": set(now_en) == set(now_zh),
        "keys_absent_at_base": all(k not in base_en and k not in base_zh for k in keys),
        "keys_present_both_sides": all(k in now_en and k in now_zh for k in keys),
        "keys_added_exactly": (set(now_en) - set(base_en)) == (set(now_zh) - set(base_zh)) == set(keys),
        "existing_texts_untouched": all(now_en[k] == v for k, v in base_en.items() if k in now_en)
                                    and all(now_zh[k] == v for k, v in base_zh.items() if k in now_zh),
        "inventory_matches_batch": len(base_pairs) - len(now_pairs) == len(ROWS),
        "no_extra_pairs_lost": all(p in now_pairs for p in base_pairs
                                   if p[0] not in {r["base_line"] for r in ROWS}),
    }
    for r in ROWS:
        at_base = [p for p in base_pairs if p[0] == r["base_line"]]
        tag = "row_draft%d_line%d" % (r["draft_row"], r["base_line"])
        checks[tag + "_one_pair_at_base"] = len(at_base) == 1
        checks[tag + "_zh_verbatim_from_screen"] = bool(at_base) and now_zh.get(r["key"]) == at_base[0][1]
        checks[tag + "_en_verbatim_from_screen"] = bool(at_base) and now_en.get(r["key"]) == at_base[0][2]
        checks[tag + "_draft_agrees"] = bool(at_base) and at_base[0][2] == dr[r["draft_row"]]["en"] \
            and dr[r["draft_row"]]["key"] == r["key"]
        checks[tag + "_site_reads_key"] = ('t("%s")' % r["key"]) in now_src.split("\n")[r["new_line"] - 1]
        checks[tag + "_old_pair_gone"] = not any(p[0] == r["base_line"] for p in now_pairs)
    sites = {}
    for n, l in enumerate(now_src.split("\n"), 1):
        for k in keys:
            if 't("%s")' % k in l:
                sites.setdefault(k, []).append(n)
    for k in keys:
        want = sorted(r["new_line"] for r in ROWS if r["key"] == k)
        checks["sites_exact_" + k] = sites.get(k, []) == want
    green = [k for k, v in checks.items() if v]
    return green, [k for k, v in checks.items() if not v]


def main():
    if "--negative" in sys.argv:
        salt_key = ROWS[0]["key"]
        green, red = run(salt_key=salt_key)
        first = "row_draft%d_line%d_en_verbatim_from_screen" % (ROWS[0]["draft_row"], ROWS[0]["base_line"])
        bites = first in red
        sys.stdout.write("%s passed=%d failed=%s\n" % ("NEGATIVE_CONTROL_BITES" if bites else "NEGATIVE_CONTROL_BLIND",
                                                       len(green), sorted(red)[:3]))
        sys.exit(0 if bites else 1)
    green, red = run()
    sys.stdout.write("ARM i18n_0557_copilot_full: keys=%d rows=%d green=%d red=%d %s\n"
                     % (len({r["key"] for r in ROWS}), len(ROWS), len(green), len(red), sorted(red)[:6]))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
