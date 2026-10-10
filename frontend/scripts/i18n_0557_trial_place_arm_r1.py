#!/usr/bin/env python3
"""ORD-0557 arm gate for the trial form's unnamed-city placeholder.

One key, read in two places, Chinese side only.  The standing i18n rulers in this
directory do not list `JourneyTrialSetup.tsx` in their TARGETS, so a green from them
would say nothing about this file; this arm compares bytes instead -- the dictionary
value must equal, character for character, the word the form painted before.

Usage:
    python frontend/scripts/i18n_0557_trial_place_arm_r1.py --base <rev> [--tree .]

Exits 0 when every check passes, 1 otherwise.
"""

import argparse
import os
import re
import subprocess
import sys

FORM = "frontend/src/features/setup/JourneyTrialSetup.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEY = "setup.somePlace"
ZH_LITERAL = "某地"
EN_SENTENCE = '"e.g. station or airport"'
FALLBACK = "value = dictionaries.en[key] ?? key;"
LINES = [1125, 1154]
PAIR_RE = re.compile(r'^\s*"([A-Za-z0-9_.]+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

fails = []
checks = 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    print("%-62s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


def show(rev, path):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, path)], capture_output=True)
    if r.returncode:
        raise SystemExit("cannot read %s:%s" % (rev, path))
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


def dictionary(text, marker):
    """The object literal that opens after `marker`, cut at the first line that is `};`.

    Bounded on purpose: scanning to end-of-file would let the Chinese block's keys leak
    into the English side's set, which is how a one-sided addition can hide."""
    body = text[text.index(marker) + len(marker):]
    out = {}
    for line in body.split("\n"):
        if line.startswith("};"):
            break
        m = PAIR_RE.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--tree", default=".")
    a = ap.parse_args()
    root = os.path.abspath(a.tree)

    form_before = show(a.base, FORM)
    dict_before = show(a.base, DICT)
    form_after = read(root, FORM)
    dict_after = read(root, DICT)

    # 1. The base really did paint that word, twice, and nowhere else in the form.
    check("base: form paints the literal %r twice" % ZH_LITERAL,
          form_before.count('"%s"' % ZH_LITERAL) == 2,
          "hits=%d" % form_before.count('"%s"' % ZH_LITERAL))
    check("base: the two hits sit on lines %s" % LINES,
          [i + 1 for i, l in enumerate(form_before.split("\n")) if '"%s"' % ZH_LITERAL in l] == LINES,
          "at=%s" % [i + 1 for i, l in enumerate(form_before.split("\n")) if '"%s"' % ZH_LITERAL in l])

    # 2. After the move the key is read twice and the literal is gone from the form.
    check("after: form reads t(%r) twice" % KEY, form_after.count('t("%s")' % KEY) == 2,
          "reads=%d" % form_after.count('t("%s")' % KEY))
    check("after: literal is gone from the form", ('"%s"' % ZH_LITERAL) not in form_after)
    check("after: the reads sit on lines %s" % LINES,
          [i + 1 for i, l in enumerate(form_after.split("\n")) if 't("%s")' % KEY in l] == LINES)

    # 3. The Chinese dictionary carries the key exactly once with the same bytes.
    zh_before = dictionary(dict_before, "const zhCN: Dict = {")
    zh_after = dictionary(dict_after, "const zhCN: Dict = {")
    en_before = dictionary(dict_before, "const en: Dict = {")
    en_after = dictionary(dict_after, "const en: Dict = {")
    check("zh: %s present exactly once" % KEY,
          len(re.findall(r'"%s"\s*:' % re.escape(KEY), dict_after)) == 1,
          "occurrences=%d" % len(re.findall(r'"%s"\s*:' % re.escape(KEY), dict_after)))
    check("zh: value byte-identical to the word the form painted", zh_after.get(KEY) == ZH_LITERAL,
          "got=%r" % zh_after.get(KEY))

    # 4. zh_only ruling: the English side stays without the key, and the English arm of
    #    those two placeholders is a different, complete sentence that this order does
    #    not move -- it must still be inline, twice, exactly as it was.
    check("en: %s absent by the zh_only ruling" % KEY, KEY not in en_after)
    check("base and after both carry the English sentence twice",
          form_before.count(EN_SENTENCE) == 2 and form_after.count(EN_SENTENCE) == 2,
          "before=%d after=%d" % (form_before.count(EN_SENTENCE), form_after.count(EN_SENTENCE)))

    # 5. Nothing else in either dictionary moved.
    for label, before, after in (("en", en_before, en_after), ("zh", zh_before, zh_after)):
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        if label == "zh":
            check("zh: only %s was added" % KEY, added == [KEY] and not removed and not changed,
                  "added=%d removed=%d changed=%d" % (len(added), len(removed), len(changed)))
        else:
            check("en: dictionary untouched", not added and not removed and not changed,
                  "added=%d removed=%d changed=%d" % (len(added), len(removed), len(changed)))

    # 6. t()'s English fallback line is unchanged: a Chinese screen missing a key would
    #    otherwise have started reading the key name instead of a word.
    check("t(): English fallback line unchanged from base",
          dict_before.count(FALLBACK) == 1 and dict_after.count(FALLBACK) == 1)

    # 7. The form changed on exactly the two lines and nowhere else.
    b_lines = form_before.split("\n")
    a_lines = form_after.split("\n")
    same_len = len(b_lines) == len(a_lines)
    touched = [i + 1 for i, (x, y) in enumerate(zip(b_lines, a_lines)) if x != y] if same_len else []
    check("form: line count unchanged", same_len, "%d vs %d" % (len(b_lines), len(a_lines)))
    check("form: exactly the two placeholder lines differ", same_len and touched == LINES,
          "touched=%s" % touched)

    print("\nARM i18n_0557_trial_place: %d checks, %d failed" % (checks, len(fails)))
    for f in fails:
        print("  failed: %s" % f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
