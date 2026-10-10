#!/usr/bin/env python3
"""ORD-0557 follow-up table · arm gate for the inbox workbench's last-resort words.

Three inline `zh ? "…" : "…"` fallbacks in `JourneyInboxWorkbench.tsx` now read two
dictionary keys.  The standing i18n rulers do not list this file in their TARGETS, so a
green from them says nothing here; this arm compares bytes: each dictionary value, on each
side, must equal the string that arm printed before the key existed.

It also checks the threading, because these three live in module-scope functions that have
no hook: every function that now reads a key must take `t`, and every call site must pass it.

Usage:
    python frontend/scripts/i18n_0557_inbox_labels_arm_r1.py --base <rev> [--tree .]

Exits 0 when every check passes, 1 otherwise.
"""

import argparse
import os
import re
import subprocess
import sys

FORM = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEYS = {
    "inbox.handled": {"zh": "已处理", "en": "Handled"},
    "inbox.toConfirm": {"zh": "待确认", "en": "To confirm"},
}
MOVED_LINES = [253, 258, 279]
THREADED = ["decisionLabel", "timeLabel", "renderFact"]
# :283 keeps its own pair of words -- it belongs to the next batch, so it must still be inline.
DEFERRED = ("已记录", "Recorded")
# three signatures, three moved reads, one internal call, three render call sites
EXPECTED_TOUCHED = [251, 253, 256, 258, 278, 279, 288, 996, 1006, 1007]

PAIR_RE = re.compile(r'^\s*"([A-Za-z0-9_.]+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

fails = []
checks = 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    print("%-64s %s %s" % (name, "ok" if ok else "FAIL", detail))
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
    """Entries of one dictionary object, cut at the line that closes it -- the two sides
    must not be allowed to read into each other."""
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

    # 1. Before: all three lines really were inline zh/en pairs.
    for key, pair in KEYS.items():
        shape = 'zh ? "%s" : "%s"' % (pair["zh"], pair["en"])
        where = [i + 1 for i, line in enumerate(form_before.split("\n")) if shape in line]
        expected = [line for line in MOVED_LINES if shape in form_before.split("\n")[line - 1]]
        check("base: pair %s/%s is inline on the moved lines" % (pair["zh"], pair["en"]),
              bool(where) and bool(expected) and all(w in where for w in expected),
              "at=%s" % where)

    # 2. After: the keys are read at those lines and the pairs are gone from the file.
    handled_reads = form_after.count('t("inbox.handled")')
    toconfirm_reads = form_after.count('t("inbox.toConfirm")')
    check("after: t(\"inbox.handled\") read once", handled_reads == 1, "reads=%d" % handled_reads)
    check("after: t(\"inbox.toConfirm\") read twice (two places, one key)",
          toconfirm_reads == 2, "reads=%d" % toconfirm_reads)
    for key, pair in KEYS.items():
        for side in ("zh", "en"):
            check("after: literal %r gone from the workbench" % pair[side],
                  '"%s"' % pair[side] not in form_after)
    moved_at = [i + 1 for i, line in enumerate(form_after.split("\n"))
                if 't("inbox.handled")' in line or 't("inbox.toConfirm")' in line]
    check("after: the reads sit on lines %s" % MOVED_LINES, moved_at == MOVED_LINES, "at=%s" % moved_at)

    # 3. Dictionary: each key exactly once per side, byte-identical value on both sides.
    en_before = dictionary(dict_before, "const en: Dict = {")
    en_after = dictionary(dict_after, "const en: Dict = {")
    zh_before = dictionary(dict_before, "const zhCN: Dict = {")
    zh_after = dictionary(dict_after, "const zhCN: Dict = {")
    for key, pair in KEYS.items():
        check("en: %s once with the string the en arm printed" % key,
              len(re.findall(r'"%s"\s*:' % re.escape(key), dict_after)) == 2
              and en_after.get(key) == pair["en"] and zh_after.get(key) == pair["zh"],
              "en=%r zh=%r" % (en_after.get(key), zh_after.get(key)))
        check("base: %s was not already in either side" % key,
              key not in en_before and key not in zh_before)

    # 4. Nothing else moved in either dictionary.
    for label, before, after in (("en", en_before, en_after), ("zh", zh_before, zh_after)):
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        check("%s: only the two stamped keys added" % label,
              added == sorted(KEYS) and not removed and not changed,
              "added=%d removed=%d changed=%d" % (len(added), len(removed), len(changed)))

    # 5. The threading: every function that now reads a key takes t, and every call site
    #    passes it -- a module-scope function cannot call useT() itself.
    for name in THREADED:
        definition = [line for line in form_after.split("\n") if line.startswith("function %s(" % name)]
        check("%s takes t in its signature" % name,
              len(definition) == 1 and "t: (key: string) => string" in definition[0],
              definition[0][:78] if definition else "no definition found")
    calls = re.findall(r"\b(decisionLabel|timeLabel|renderFact)\((.*?)\)[,;}\s]", form_after)
    passed = [c for c in re.finditer(r"\b(decisionLabel|timeLabel|renderFact)\(", form_after)
              if c.group(0).startswith("decisionLabel(")]
    check("every call site passes three arguments",
          len(re.findall(r"decisionLabel\([^)]*, zh, t\)", form_after)) == 2
          and len(re.findall(r"timeLabel\([^)]*, zh, t\)", form_after)) == 1
          and len(re.findall(r"renderFact\([^)]*, zh, t\)", form_after)) == 1,
          "decision=%d time=%d render=%d" % (
              len(re.findall(r"decisionLabel\([^)]*, zh, t\)", form_after)),
              len(re.findall(r"timeLabel\([^)]*, zh, t\)", form_after)),
              len(re.findall(r"renderFact\([^)]*, zh, t\)", form_after))))
    check("no call site left on the old two-argument shape",
          len(re.findall(r"\b(decisionLabel|timeLabel|renderFact)\([^)]*, zh\)", form_after)) == 0,
          "left=%d" % len(re.findall(r"\b(decisionLabel|timeLabel|renderFact)\([^)]*, zh\)", form_after)))

    # 6. The deferred pair (:283) is untouched, so this batch really is three places only.
    for word in DEFERRED:
        check("deferred: %r still inline until the next branch" % word,
              ('"%s"' % word) in form_after and ('"%s"' % word) in form_before)

    # 7. Byte discipline: only the ten known lines of the workbench differ, line count same.
    b_lines = form_before.split("\n")
    a_lines = form_after.split("\n")
    same_len = len(b_lines) == len(a_lines)
    touched = [i + 1 for i, (x, y) in enumerate(zip(b_lines, a_lines)) if x != y] if same_len else []
    check("workbench: line count unchanged", same_len, "%d vs %d" % (len(b_lines), len(a_lines)))
    check("workbench: the only changed lines are signatures, reads and call sites",
          same_len and touched == EXPECTED_TOUCHED, "touched=%s" % touched)
    check("workbench: moneyLabel untouched -- its row is dead code, reported not moved",
          'zh ? "金额待确认" : "Amount to confirm"' in form_after
          and 'zh ? "金额待确认" : "Amount to confirm"' in form_before)

    print("\nARM i18n_0557_inbox_labels: %d checks, %d failed" % (checks, len(fails)))
    for f in fails:
        print("  failed: %s" % f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
