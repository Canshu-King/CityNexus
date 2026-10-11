import io, re, sys

P = r"D:/moodle/_qoder_pinggong_0555_dict/frontend/src/i18n/LocaleContext.tsx"
lines = io.open(P, encoding="utf-8").read().split("\n")


def rng(marker):
    i = next(k for k, s in enumerate(lines) if s.startswith(marker))
    j = next(k for k, s in enumerate(lines[i + 1:], i + 1) if s == "};")
    return i, j


en_i, en_j = rng("const en: Dict = {")
zh_i, zh_j = rng("const zhCN: Dict = {")
KEY = re.compile(r'^  "(main\.[A-Za-z0-9]+)": (".*"),$')

en_rows = [(m.group(1), m.group(2)) for m in (KEY.match(s) for s in lines[en_i + 1:en_j]) if m]
zh_at = {}
for k in range(zh_i + 1, zh_j + 1):
    m = KEY.match(lines[k - 1])
    if m:
        zh_at[m.group(1)] = k - 1
if len(en_rows) != 21 or len(zh_at) != 21:
    sys.exit("ABORT en=%d zh=%d (expected 21 both)" % (len(en_rows), len(zh_at)))

positions = sorted(zh_at.values())
# write the same sequence the en side uses, keeping each side's own value bytes
order = [k for k, _ in en_rows]
vals = {k: v for k, v in ((m.group(1), m.group(2)) for m in
                          (KEY.match(lines[p]) for p in positions) if m)}
for pos, key in zip(positions, order):
    lines[pos] = '  "%s": %s,' % (key, vals[key])
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("reordered zh rows=%d to match en order" % len(order))
print("zh_first=%s zh_last=%s" % (order[0], order[-1]))
