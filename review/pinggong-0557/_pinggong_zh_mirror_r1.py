import io, re, sys

P = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
lines = io.open(P, encoding="utf-8").read().split("\n")


def obj_range(marker):
    i = next(k for k, s in enumerate(lines) if s.startswith(marker))
    j = next(k for k, s in enumerate(lines[i + 1:], i + 1) if s == "};")
    return i, j


en_i, en_j = obj_range("const en: Dict = {")
zh_i, zh_j = obj_range("const zhCN: Dict = {")

pat = re.compile(r'^  "(main\.[A-Za-z0-9]+)": (".*"),$')
en_rows = [(m.group(1), m.group(2)) for m in (pat.match(s) for s in lines[en_i + 1:en_j]) if m]
zh_keys = set()
for s in lines[zh_i + 1:zh_j]:
    m = re.match(r'^  "(main\.[A-Za-z0-9]+)":', s)
    if m:
        zh_keys.add(m.group(1))
missing = [(k, v) for k, v in en_rows if k not in zh_keys]
if len(en_rows) != 21:
    sys.exit("ABORT en main.* rows=%d (expected 21)" % len(en_rows))
print("en main.* rows=%d zh has=%d missing=%d" % (len(en_rows), len(zh_keys), len(missing)))

anchor = next(i for i in range(zh_i, zh_j) if lines[i].startswith('  "main.unnamedCommitmentServerGaveNoName"'))
lines[anchor + 1:anchor + 1] = ['  "%s": %s,' % (k, v) for k, v in missing]
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("inserted_at_zh_line=%d count=%d" % (anchor + 2, len(missing)))
