#!/usr/bin/env python3
"""ORD-0557 arm gate for the preventive panel's two last-resort lines.

The standing i18n rulers in this directory only cover the paths in their own
TARGETS lists, so a green from them says nothing about this file.  This arm
compares the *bytes* instead: every value it accepts must equal, character for
character, the literal the panel printed on the line it came from.

Usage:
    python frontend/scripts/i18n_0557_preventive_panel_arm_r1.py --base <rev>

Exits 0 with a per-check verdict; any failed check exits 1.
"""

import argparse
import re
import subprocess
import sys

PANEL = "frontend/src/features/recovery/V14PreventivePanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEYS = ("recovery.noDominantMode", "recovery.noneOnThisJourney")
OLD_LITERALS = {
    "recovery.noDominantMode": "no dominant mode",
    "recovery.noneOnThisJourney": "none on this journey",
}
PAIR_RE = re.compile(r'^\s*"([A-Za-z0-9_.]+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
ENTRY_RE = re.compile(r'"([A-Za-z0-9_.]+)":\s*"((?:[^"\\]|\\.)*)"')
FALLBACK = "value = dictionaries.en[key] ?? key;"

fails = []
checks = 0


def show(rev, path):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, path)], capture_output=True)
    if r.returncode:
        raise SystemExit("cannot read %s:%s -> %s" % (rev, path, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


def check(name, ok, detail=""):
    global checks
    checks += 1
    print("%-58s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


def block(text, start_marker):
    """Return the object literal that starts after start_marker, as a list of lines."""
    at = text.index(start_marker)
    return text[at:].split("\n")


def pairs(lines):
    """key -> value, single-line entries only, first occurrence wins (dict order)."""
    out = {}
    for line in lines:
        m = PAIR_RE.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="rev the branch was cut from")
    ap.add_argument("--tree", default=".", help="worktree root holding the candidate")
    a = ap.parse_args()

    import os

    root = os.path.abspath(a.tree)
    panel_before = show(a.base, PANEL)
    dict_before = show(a.base, DICT)
    with open(os.path.join(root, PANEL), encoding="utf-8") as h:
        panel_after = h.read().replace("\r\n", "\n")
    with open(os.path.join(root, DICT), encoding="utf-8") as h:
        dict_after = h.read().replace("\r\n", "\n")

    # 1. On the base revision each literal is still printed by the panel itself.
    for key in KEYS:
        lit = OLD_LITERALS[key]
        hits = panel_before.count('"%s"' % lit)
        check("base: panel prints the literal %r" % lit, hits == 1, "hits=%d" % hits)

    # 2. After the move the panel reads the key and no longer carries the literal.
    for key in KEYS:
        lit = OLD_LITERALS[key]
        reads = panel_after.count('t("%s")' % key)
        left = panel_after.count('"%s"' % lit)
        check("after: panel reads t(%r) exactly once" % key, reads == 1, "reads=%d" % reads)
        check("after: literal %r is gone from the panel" % lit, left == 0, "left=%d" % left)

    # 3. The English dictionary carries each new key exactly once, with the byte-identical
    #    value the panel used to print.
    en_before = pairs(block(dict_before, "const en: Dict"))
    en_after = pairs(block(dict_after, "const en: Dict"))
    zh_before = pairs(block(dict_before, "const zhCN: Dict"))
    zh_after = pairs(block(dict_after, "const zhCN: Dict"))
    for key in KEYS:
        occurrences = len(re.findall(r'"%s"\s*:' % re.escape(key), dict_after))
        check("en: %s present exactly once" % key, occurrences == 1, "occurrences=%d" % occurrences)
        check("en: value byte-identical to the old literal", en_after.get(key) == OLD_LITERALS[key],
              "got=%r" % en_after.get(key))

    # 4. en_only ruling: the Chinese side stays without these two, and t() resolves a
    #    missing Chinese key through the English dictionary -- that fallback line must
    #    be unchanged from the base, otherwise the Chinese screen would move.
    for key in KEYS:
        check("zh: %s absent by the en_only ruling" % key, key not in zh_after)
    check("t(): English fallback line unchanged from base",
          FALLBACK in dict_after and dict_before.count(FALLBACK) == dict_after.count(FALLBACK),
          "base=%d after=%d" % (dict_before.count(FALLBACK), dict_after.count(FALLBACK)))

    # 5. Nothing else in either dictionary moved.
    for label, before, after in (("en", en_before, en_after), ("zh", zh_before, zh_after)):
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        if label == "en":
            check("en: only the two stamped keys added", added == sorted(KEYS) and not removed and not changed,
                  "added=%d removed=%d changed=%d" % (len(added), len(removed), len(changed)))
        else:
            check("zh: dictionary untouched", not added and not removed and not changed,
                  "added=%d removed=%d changed=%d" % (len(added), len(removed), len(changed)))

    # 6. The panel changed on exactly the two lines and nowhere else.
    b_lines = panel_before.split("\n")
    a_lines = panel_after.split("\n")
    same_len = len(b_lines) == len(a_lines)
    touched = [i + 1 for i, (x, y) in enumerate(zip(b_lines, a_lines)) if x != y] if same_len else []
    check("panel: line count unchanged", same_len, "%d vs %d" % (len(b_lines), len(a_lines)))
    check("panel: exactly the two moved lines differ", same_len and touched == [196, 228],
          "touched=%s" % touched)

    print("\nARM i18n_0557_preventive_panel: %d checks, %d failed" % (checks, len(fails)))
    if fails:
        for f in fails:
            print("  failed: %s" % f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
