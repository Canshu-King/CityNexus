import io, re, sys

PROD = r"D:/moodle/_qoder_pinggong_0555/frontend/src/lib/sceneClock.ts"
DICT = r"D:/moodle/_qoder_pinggong_0555_dict/frontend/src/i18n/LocaleContext.tsx"

PAIRS = [
    ("sceneClock.sealedTravelDataHasNoExpiry",
     '  if (state === "FROZEN_WITHOUT_TTL")\n    return zh\n      ? "这趟的出行数据是封存的，没有到期时间"\n      : "this trip\'s travel data is sealed, with no expiry";',
     '  if (state === "FROZEN_WITHOUT_TTL")\n    return copy("sceneClock.sealedTravelDataHasNoExpiry");'),
    ("sceneClock.evidenceReferenceDoesNotLineUp",
     '  if (state === "EVIDENCE_REFERENCE_INCONSISTENT")\n    return zh\n      ? "证据的引用对不上（服务器说有封存记录，但引用不一致）"\n      : "the evidence reference does not line up (sealed rows exist, but the reference is inconsistent)";',
     '  if (state === "EVIDENCE_REFERENCE_INCONSISTENT")\n    return copy("sceneClock.evidenceReferenceDoesNotLineUp");'),
]

ps = io.open(PROD, encoding="utf-8").read()
harvested = []
for key, old, new in PAIRS:
    if ps.count(old) != 1:
        sys.exit("ABORT prod needle hits=%d for %s" % (ps.count(old), key))
    m = re.search(r'\?\s*"([^"]*)"\s*\n\s*:\s*"([^"]*)"', old)
    if not m:
        sys.exit("ABORT cannot harvest pair from %s" % key)
    harvested.append((key, m.group(1), m.group(2)))
    ps = ps.replace(old, new, 1)

dl = io.open(DICT, encoding="utf-8").read().split("\n")


def rng(marker):
    i = next(k for k, s in enumerate(dl) if s.startswith(marker))
    j = next(k for k, s in enumerate(dl[i + 1:], i + 1) if s == "};")
    return i, j


en_i, en_j = rng("const en: Dict = {")
zh_i, zh_j = rng("const zhCN: Dict = {")
for k, _, _ in harvested:
    if any(s.startswith('  "%s":' % k) for s in dl):
        sys.exit("ABORT key exists: %s" % k)

AFTER_EN = '  "sceneClock.noScenarioOnStage": "no scenario on stage",'
AFTER_ZH = '  "sceneClock.noScenarioOnStage": "台上没有场景",'
ae = [i for i in range(en_i, en_j) if dl[i] == AFTER_EN]
az = [i for i in range(zh_i, zh_j) if dl[i] == AFTER_ZH]
if len(ae) != 1 or len(az) != 1:
    sys.exit("ABORT anchors en=%d zh=%d" % (len(ae), len(az)))
dl[az[0] + 1:az[0] + 1] = ['  "%s": "%s",' % (k, v) for k, v, _ in harvested]
dl[ae[0] + 1:ae[0] + 1] = ['  "%s": "%s",' % (k, v) for k, _, v in harvested]

io.open(PROD, "w", encoding="utf-8", newline="\n").write(ps)
io.open(DICT, "w", encoding="utf-8", newline="\n").write("\n".join(dl))
for k, v, e in harvested:
    print("harvested %s | zh=%s | en=%s" % (k, v, e))
print("BATCH3_ROWS_ROUTED=%d en_at=%d zh_at=%d" % (len(harvested), ae[0] + 2, az[0] + 2 + len(harvested)))
