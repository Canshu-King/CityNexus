"""Cross-line-aware dictionary parity recount (ORD-0555, lane 比价工).

The shared ruler frontend/scripts/i18n_detail2_parity_r1.py matches
`"key": "value",` line by line, so a key whose value is written on the FOLLOWING
line is invisible to it. That defect is reported in the ledger by another lane;
this script only re-measures, it does not touch the shared ruler.

Usage: python dict_parity_recount_r1.py <path to LocaleContext.tsx> [label]
"""
import re
import sys

KEY_START = re.compile(r'^\s*"([^"]+)"\s*:\s*')


def sides(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    marks = {}
    for n, line in enumerate(lines, 1):
        if line.startswith("const en: Dict"):
            marks["en"] = n
        elif line.startswith("const zhCN: Dict"):
            marks["zh"] = n
        elif line.startswith("const dictionaries"):
            marks["end"] = n
    out = {"en": {}, "zh": {}}
    for side in ("en", "zh"):
        start = marks[side]
        stop = marks["zh"] if side == "en" else marks["end"]
        for n in range(start + 1, stop):
            m = KEY_START.match(lines[n - 1])
            if m:
                out[side].setdefault(m.group(1), []).append(n)
    return out


def main():
    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else path
    s = sides(path)
    en, zh = set(s["en"]), set(s["zh"])
    print("subject: %s" % label)
    print("en keys parsed: %d" % len(en))
    print("zh keys parsed: %d" % len(zh))
    print("sets equal: %s" % (en == zh))
    for k in sorted(en ^ zh):
        print("  only one side: %s" % k)
    dup = {k: v for k, v in list(s["en"].items()) + list(s["zh"].items()) if len(v) > 1}
    print("keys written more than once on any side: %d" % len(dup))
    for k, v in sorted(dup.items()):
        print("  %s at lines %s" % (k, v))
    lines = open(path, encoding="utf-8").read().split("\n")
    print("cross-line key names (name line has no value on it): ")
    found = []
    for n, line in enumerate(lines, 1):
        m = KEY_START.match(line)
        if m and not re.search(r':\s*"', line):
            found.append((n, m.group(1)))
    for n, k in found:
        print("  line %d: %s" % (n, k))
    print("cross-line count: %d" % len(found))
    print("RESULT: %s" % ("DICT_PARITY_RECOUNT_OK" if en == zh else "DICT_PARITY_RECOUNT_BREAK"))
    return 0 if en == zh else 1


if __name__ == "__main__":
    sys.exit(main())
