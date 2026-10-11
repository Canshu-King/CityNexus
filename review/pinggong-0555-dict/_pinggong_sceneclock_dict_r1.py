import io, sys

P = r"D:/moodle/_qoder_pinggong_0555_dict/frontend/src/i18n/LocaleContext.tsx"
lines = io.open(P, encoding="utf-8").read().split("\n")

EN_ANCHOR = '  "mobility.note": '
ZH_ANCHOR = '  "mobility.note": '
KEYS = [
    ("sceneClock.executionCursor", "the execution cursor", "执行游标"),
    ("sceneClock.journeyStart", "the journey's start", "行程起点"),
    ("sceneClock.serverGaveNoBasis", "the server gave no basis", "服务器没有说明依据"),
]

for k, _, _ in KEYS:
    if any(s.startswith('  "%s":' % k) for s in lines):
        sys.exit("ABORT key already present %s" % k)


def hits(prefix, lo, hi):
    return [i for i in range(lo, hi) if lines[i].startswith(prefix)]


en_i = next(i for i, s in enumerate(lines) if s.startswith("const en: Dict = {"))
en_j = next(i for i, s in enumerate(lines[en_i + 1:], en_i + 1) if s == "};")
zh_i = next(i for i, s in enumerate(lines) if s.startswith("const zhCN: Dict = {"))
zh_j = next(i for i, s in enumerate(lines[zh_i + 1:], zh_i + 1) if s == "};")

e = hits(EN_ANCHOR, en_i, en_j)
z = hits(ZH_ANCHOR, zh_i, zh_j)
if len(e) != 1 or len(z) != 1:
    sys.exit("ABORT anchor hits en=%d zh=%d" % (len(e), len(z)))

# same rank on both sides: right after the same neighbouring key
lines[z[0] + 1:z[0] + 1] = ['  "%s": "%s",' % (k, v) for k, _, v in KEYS]
lines[e[0] + 1:e[0] + 1] = ['  "%s": "%s",' % (k, v) for k, v, _ in KEYS]
print("en_at=%d zh_at=%d" % (e[0] + 2, z[0] + 2 + len(KEYS)))

# module-scope accessor, mirroring the provider's t() fallback order verbatim
dic_i = next(i for i, s in enumerate(lines) if s.startswith("const dictionaries"))
block = [
    "",
    "export function dictionaryCopy(",
    "  locale: TripLocale,",
    "  key: string,",
    "): string {",
    "  return dictionaries[locale][key] ?? dictionaries.en[key] ?? key;",
    "}",
]
if "export function dictionaryCopy" not in "\n".join(lines):
    lines[dic_i + 1:dic_i + 1] = block
    print("accessor_at=%d" % (dic_i + 2))

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("keys_added=3 sides=2")
