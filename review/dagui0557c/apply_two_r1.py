import io, re, sys

SRC = "frontend/src/features/simulation/SimulationPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')

TWO = [
    (839, u'<dt>{zh ? "依据" : "Basis"}</dt>', u'<dt>{t("simulation.basis")}</dt>',
     "simulation.basis", "Basis", u"依据"),
    (845, u'<dt>{zh ? "证据" : "Evidence"}</dt>', u'<dt>{t("simulation.evidence")}</dt>',
     "simulation.evidence", "Evidence", u"证据"),
]

# 1. product side, asserted per line number read now
with io.open(SRC, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")
bad = [(n, lines[n - 1].count(old)) for n, old, _new, _k, _en, _zh in TWO
       if n > len(lines) or lines[n - 1].count(old) != 1]
if bad:
    for n, c in bad:
        sys.stdout.write("ABORT line=%d hits=%d\n" % (n, c))
    sys.exit(3)
for n, old, new, _k, _en, _zh in TWO:
    lines[n - 1] = lines[n - 1].replace(old, new, 1)
with io.open(SRC, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
sys.stdout.write("product_edits=%d\n" % len(TWO))

# 2. dictionary side: recompute each block end, refuse a point inside an open comment
with io.open(DICT, encoding="utf-8", newline="") as f:
    d = f.read().split("\n")


def side_counts(rows):
    text = "\n".join(rows)
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    out = []
    for ch in (text[i:j], text[j:k]):
        n = 0
        for line in ch.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            if KEY.match(line):
                n += 1
        out.append(n)
    return out


def close_index(rows, start_pat):
    starts = [n for n, l in enumerate(rows) if l.startswith(start_pat)]
    assert len(starts) == 1, start_pat
    for n in range(starts[0] + 1, len(rows)):
        if rows[n] == "};":
            return n
    raise AssertionError("no close")


def open_comments(rows, idx):
    text = "\n".join(rows[:idx])
    return text.count("/*") - text.count("*/")


for k, en, zh in [(t[3], t[4], t[5]) for t in TWO]:
    assert sum(1 for l in d if l.startswith('  "%s":' % k)) == 0, "already present: " + k

before = side_counts(d)
zh_at = close_index(d, "const zhCN: Dict")
assert open_comments(d, zh_at) == 0, "zh point inside a comment"
d[zh_at:zh_at] = [""] + [u"  // ── ORD-0557 stage header, two remaining rows ──"] + \
    ['  "%s": "%s",' % (t[3], t[5]) for t in TWO]
en_at = close_index(d, "const en: Dict")
assert open_comments(d, en_at) == 0, "en point inside a comment"
d[en_at:en_at] = [""] + [u"  // ── ORD-0557 stage header, two remaining rows ──"] + \
    ['  "%s": "%s",' % (t[3], t[4]) for t in TWO]
after = side_counts(d)
assert after[0] == before[0] + 2 and after[1] == before[1] + 2, (before, after)
for t in TWO:
    hits = [n + 1 for n, l in enumerate(d) if l.startswith('  "%s":' % t[3])]
    assert len(hits) == 2, (t[3], hits)
with io.open(DICT, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(d))
sys.stdout.write("dict en=%d->%d zh=%d->%d both_sides=2 comment_free=1\n"
                 % (before[0], after[0], before[1], after[1]))
