# -*- coding: utf-8 -*-
"""ORD-0576 arm for lane 键盘工's main.tsx batch (v2): each moved string must resolve, in
BOTH locales, to exactly the bytes the base tip's own file painted.

Independent of the mover: it re-reads the base tip's source, the working tree, and both
dictionaries, and re-derives every claim. `--negative` salts one dictionary value in memory
(the disk is untouched) and requires the matching byte-equality check to go red.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/main.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
EV = os.path.join(TREE, "frontend", "scripts", "i18n_0576_main_move_evidence_r1.json")
CJK = re.compile(u"[\u3400-\u9fff]")
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')
VALUE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
OPTION_RE = re.compile(r'^\s*<option value="([A-Z]+)">([^<>{}]*)</option>$')
CONST_RE = re.compile(r'const defaultAgentCommand =\n\s*"((?:[^"\\]|\\.)*)";')

ev = json.load(open(EV, encoding="utf-8"))
BASE, ROWS = ev["base_tip"], ev["items"]
COORDS = []   # 每枚键在字典两侧被内容定位到的行号，跑完打出来


def arm_ranges(lines):
    """Line numbers belonging to each dictionary arm, so a value that is identical on both
    sides is still counted once per side."""
    out = {}
    for name, marker in (("en", "const en: Dict = {"), ("zh", "const zhCN: Dict = {")):
        start = lines.index(marker)
        end = start
        while lines[end] != "};":
            end += 1
        out[name] = set(range(start + 1, end + 1))
    return out


def show(rev, path):
    p = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (rev, path)], capture_output=True)
    if p.returncode != 0:
        sys.stdout.write("ABORT git show " + p.stderr.decode("utf-8", "replace") + "\n")
        sys.exit(3)
    return p.stdout.decode("utf-8")


def read(path):
    return open(os.path.join(TREE, path.replace("/", os.sep)), encoding="utf-8").read()


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
        out.append(d)
    return out[0], out[1]


def base_painted(rev):
    """What each of the four sites showed the traveller on the base tip (same in both locales)."""
    src = show(rev, SRC_REL)
    out = {}
    for n, l in enumerate(src.split("\n"), 1):
        m = OPTION_RE.match(l)
        if m and CJK.search(m.group(2)):
            out["OPTION:" + m.group(1)] = m.group(2)
    lit = CONST_RE.search(src)
    if lit:
        out["PREFILL"] = lit.group(1)
    return out


def resolve(pair, locale_key, key):
    """The runtime's own fallback order: this locale, then English, then the key itself."""
    en, zh = pair
    table = zh if locale_key == "zh-CN" else en
    return table.get(key) or en.get(key) or key


def run(salt=None):
    painted = base_painted(BASE)
    now_src = read(SRC_REL)
    now = dicts(read(DICT_REL))
    base = dicts(show(BASE, DICT_REL))
    now_en, now_zh = now
    base_en, base_zh = base
    if salt:
        now_en = dict(now_en)
        now_en[salt] = "SALTED"
        now = (now_en, now_zh)
    keys = [r["key"] for r in ROWS]
    checks = {
        "parity_before": set(base_en) == set(base_zh),
        "parity_after": set(now[0]) == set(now[1]),
        "keys_absent_at_base": all(k not in base_en and k not in base_zh for k in keys),
        "keys_present_both_sides": all(k in now[0] and k in now[1] for k in keys),
        # generation-proof: after the lane merges a newer tip, the added set legitimately holds
        # other batches' and other lanes' keys too. What must hold is that my keys are all
        # additions, both arms gained the same set, and no base text moved (checked next).
        "this_batches_keys_are_additions": set(keys) <= (set(now[0]) - set(base_en))
            and set(keys) <= (set(now[1]) - set(base_zh))
            and (set(now[0]) - set(base_en)) == (set(now[1]) - set(base_zh)),
        "existing_texts_untouched": all(now[0][k] == v for k, v in base_en.items() if k in now[0])
                                    and all(now[1][k] == v for k, v in base_zh.items() if k in now[1]),
        "prefill_const_gone": "defaultAgentCommand" not in now_src,
        "cjk_lines_dropped_by_batch": ev["cjk_lines_before"] - ev["cjk_lines_after"] == len(ROWS),
    }
    for r in ROWS:
        want = painted.get("PREFILL") if r["kind"] == "prefilled command" \
            else painted.get("OPTION:" + re.search(r'value="([A-Z]+)"', r["before"]).group(1))
        tag = "row_" + r["key"]
        line = now_src.split("\n")[r["new_line"] - 1]
        checks[tag + "_base_painted_one_string"] = want is not None
        checks[tag + "_zh_reads_same_bytes"] = resolve(now, "zh-CN", r["key"]) == want
        checks[tag + "_en_reads_same_bytes"] = resolve(now, "en", r["key"]) == want
        checks[tag + "_both_sides_equal_today"] = r["zh"] == r["en"] == want
        checks[tag + "_site_reads_key"] = 't("%s")' % r["key"] in line
        checks[tag + "_read_once"] = now_src.count('t("%s")' % r["key"]) == 1
        checks[tag + "_literal_not_left_in_source"] = want not in now_src
        # The old form compared the dictionary line against a number pinned in the evidence
        # file, which goes stale the moment anyone appends above it -- that is what made four
        # rows red after a re-cut while the bytes were fine. Locate the entry by content, but
        # per side: these four keys carry the SAME string on both arms (nothing on screen
        # differs between locales today), so searching the whole file would always find two
        # copies and the check would be vacuous in the wrong direction.
        dict_now = read(DICT_REL).split("\n")
        side = arm_ranges(dict_now)
        en_hit = [i + 1 for i, l in enumerate(dict_now)
                  if i + 1 in side["en"] and l == '  "%s": "%s",' % (r["key"], r["en"])]
        zh_hit = [i + 1 for i, l in enumerate(dict_now)
                  if i + 1 in side["zh"] and l == '  "%s": "%s",' % (r["key"], r["zh"])]
        checks[tag + "_dict_entry_located_once"] = len(en_hit) == 1 and len(zh_hit) == 1
        COORDS.append((r["key"], en_hit[:1], zh_hit[:1]))
    return [k for k, v in checks.items() if v], [k for k, v in checks.items() if not v]


def main():
    if "--negative" in sys.argv:
        green, red = run(salt=ROWS[0]["key"])
        want = "row_%s_en_reads_same_bytes" % ROWS[0]["key"]
        bites = want in red
        sys.stdout.write("%s passed=%d failed=%s\n"
                         % ("NEGATIVE_CONTROL_BITES" if bites else "NEGATIVE_CONTROL_BLIND",
                            len(green), sorted(red)[:3]))
        sys.exit(0 if bites else 1)
    green, red = run()
    sys.stdout.write("ARM i18n_0576_main: rows=%d green=%d red=%d %s\n"
                     % (len(ROWS), len(green), len(red), sorted(red)[:8]))
    for key, en_hit, zh_hit in COORDS:
        sys.stdout.write("  %-24s 字典 en 行 %s 与 zh 行 %s（按内容定位）\n"
                         % (key, en_hit[0] if en_hit else "-", zh_hit[0] if zh_hit else "-"))
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
