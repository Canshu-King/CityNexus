import io, re, subprocess

DICT = r"D:/moodle/_qoder_pinggong_0555_verify/frontend/src/i18n/LocaleContext.tsx"
BASE_PROD = r"D:/moodle/_qoder_pinggong_0555/frontend/src/lib/sceneClock.ts"
TIP = "ee8b9c6bb299aac76d8ab969b84f7dfa5c3a173a"
WT = r"D:/moodle/_qoder_pinggong_0555"
OUT = r"D:/moodle/_qoder_pinggong_0555_verify/review/pinggong-0555/align_gate_r1.txt"

dl = io.open(DICT, encoding="utf-8").read().split("\n")


def block(marker):
    i = next(k for k, s in enumerate(dl) if s.startswith(marker))
    j = next(k for k, s in enumerate(dl[i + 1:], i + 1) if s == "};")
    d = {}
    for k, s in enumerate(dl[i + 1:j], i + 2):
        m = re.match(r'^  "([^"]+)":\s*(.*)$', s)
        if not m:
            continue
        val = m.group(2)
        if val == "":
            val = dl[k].strip()
        val = val.strip().rstrip(",")
        if len(val) > 1 and val[0] == '"' and val[-1] == '"':
            d[m.group(1)] = (k, val[1:-1].replace('\\"', '"'))
    return d


en, zh = block("const en: Dict = {"), block("const zhCN: Dict = {")

# what was on screen before, taken from the authoritative tip
old = subprocess.run(["git", "-C", WT, "show", "%s:frontend/src/lib/sceneClock.ts" % TIP],
                     capture_output=True).stdout.decode("utf-8").split("\n")
before = {}
for i, s in enumerate(old, 1):
    m = re.search(r'zh \? "([^"]*)" : "([^"]*)"', s)
    if m and i <= 180:
        before[i] = (m.group(1), m.group(2))

KEYS = {178: "sceneClock.executionCursor", 179: "sceneClock.journeyStart", 180: "sceneClock.serverGaveNoBasis"}

L = ["# alignment gate for ORD-0555 batch 1 (predicate mirrors LocaleContext's own t/dictionaryCopy)"]
L.append("en_keys=%d zh_keys=%d equal=%s" % (len(en), len(zh), len(en) == len(zh)))
L.append("rows_before_on_tip=%s" % sorted(before))
bad = 0
for line, (zh_txt, en_txt) in sorted(before.items()):
    k = KEYS.get(line + 1) or KEYS.get(line)
    got_zh = zh.get(k, (0, None))[1]
    got_en = en.get(k, (0, None))[1]
    ok = got_zh == zh_txt and got_en == en_txt
    if not ok:
        bad += 1
    L.append("line %d | key %s | zh_equal=%s en_equal=%s | %s" % (
        line, k, got_zh == zh_txt, got_en == en_txt, "PASS" if ok else "FAIL"))
    if not ok:
        L.append("   want zh=%r en=%r" % (zh_txt, en_txt))
        L.append("   got  zh=%r en=%r" % (got_zh, got_en))
missing = [k for k in KEYS.values() if k not in en or k not in zh]
L.append("keys_missing_on_either_side=%s" % (missing or "none"))
L.append("PASS=%d FAIL=%d" % (len(before) - bad, bad))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L))
