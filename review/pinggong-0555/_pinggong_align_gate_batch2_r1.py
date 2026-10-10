import io, re, subprocess

TIP = "ee8b9c6bb299aac76d8ab969b84f7dfa5c3a173a"
WT = r"D:/moodle/_qoder_pinggong_0555"
DICT = r"D:/moodle/_qoder_pinggong_0555_dict/frontend/src/i18n/LocaleContext.tsx"
OUT = r"D:/moodle/_qoder_pinggong_0555/review/pinggong-0555/align_gate_batch2_r1.txt"

TABLE = [
    ("sceneClock.executionCursor", "执行游标", "the execution cursor"),
    ("sceneClock.journeyStart", "行程起点", "the journey's start"),
    ("sceneClock.serverGaveNoBasis", "服务器没有说明依据", "the server gave no basis"),
    ("sceneClock.frozenEvidenceCarriesExpiry", "这批证据带冻结期", "the frozen evidence carries an expiry"),
    ("sceneClock.noFrozenEvidenceOnThisTrip", "这趟没有冻结证据", "no frozen evidence on this trip"),
    ("sceneClock.noScenarioOnStage", "台上没有场景", "no scenario on stage"),
]

base = subprocess.run(["git", "-C", WT, "show", "%s:frontend/src/lib/sceneClock.ts" % TIP],
                      capture_output=True).stdout.decode("utf-8").split("\n")

dl = io.open(DICT, encoding="utf-8").read().split("\n")


def block(marker):
    i = next(k for k, s in enumerate(dl) if s.startswith(marker))
    j = next(k for k, s in enumerate(dl[i + 1:], i + 1) if s == "};")
    d, order = {}, []
    k = i + 2
    while k < j + 1:
        m = re.match(r'^  "([^"]+)":\s*(.*)$', dl[k - 1])
        if m:
            val = m.group(2)
            if val == "":
                val = dl[k].strip()
                k += 1
            val = val.strip().rstrip(",")
            if len(val) > 1 and val[0] == '"' and val[-1] == '"':
                d[m.group(1)] = (k, val[1:-1].replace('\\"', '"'))
                order.append(m.group(1))
        k += 1
    return d, order


en, en_order = block("const en: Dict = {")
zh, zh_order = block("const zhCN: Dict = {")

L = ["# alignment gate over all six takeable rows of sceneClock (batch 1 + batch 2)"]
L.append("en_keys=%d zh_keys=%d equal=%s" % (len(en), len(zh), len(en) == len(zh)))
L.append("key order identical on both sides=%s" % (en_order == zh_order,))
bad = 0
for key, zh_txt, en_txt in TABLE:
    # where was this pair on screen before? read the base file, both one-line and split-line shapes
    at = [i for i, s in enumerate(base, 1) if zh_txt in s or (
        s.strip() == "? \"%s\"" % zh_txt)]
    got_en, got_zh = en.get(key, (0, None))[1], zh.get(key, (0, None))[1]
    ok = got_en == en_txt and got_zh == zh_txt and at
    if not ok:
        bad += 1
    L.append("key %s | was_on_base sceneClock.ts:%s | en_equal=%s LocaleContext.tsx:%s | zh_equal=%s LocaleContext.tsx:%s | %s" % (
        key, ",".join(map(str, at)) or "NOT-FOUND", got_en == en_txt, en.get(key, (0,))[0],
        got_zh == zh_txt, zh.get(key, (0,))[0], "PASS" if ok else "FAIL"))
    if not ok:
        L.append("   want en=%r zh=%r" % (en_txt, zh_txt))
        L.append("   got  en=%r zh=%r" % (got_en, got_zh))
L.append("PASS=%d FAIL=%d rows=%d" % (len(TABLE) - bad, bad, len(TABLE)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L))
