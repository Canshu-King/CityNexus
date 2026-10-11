import io, re, sys

DICT = r"D:/moodle/_qoder_pinggong_0555_dict/frontend/src/i18n/LocaleContext.tsx"
PROD = r"D:/moodle/_qoder_pinggong_0555/frontend/src/lib/sceneClock.ts"

KEYS = [
    ("sceneClock.frozenEvidenceCarriesExpiry",
     '这批证据带冻结期', "the frozen evidence carries an expiry"),
    ("sceneClock.noFrozenEvidenceOnThisTrip",
     '这趟没有冻结证据', "no frozen evidence on this trip"),
    ("sceneClock.noScenarioOnStage",
     '台上没有场景', "no scenario on stage"),
]

dl = io.open(DICT, encoding="utf-8").read().split("\n")


def rng(marker):
    i = next(k for k, s in enumerate(dl) if s.startswith(marker))
    j = next(k for k, s in enumerate(dl[i + 1:], i + 1) if s == "};")
    return i, j


en_i, en_j = rng("const en: Dict = {")
zh_i, zh_j = rng("const zhCN: Dict = {")
for k, _, _ in KEYS:
    if any(s.startswith('  "%s":' % k) for s in dl):
        sys.exit("ABORT key already present: %s" % k)

anchor_en = '  "sceneClock.serverGaveNoBasis": "the server gave no basis",'
anchor_zh = '  "sceneClock.serverGaveNoBasis": "服务器没有说明依据",'
ae = [i for i in range(en_i, en_j) if dl[i] == anchor_en]
az = [i for i in range(zh_i, zh_j) if dl[i] == anchor_zh]
if len(ae) != 1 or len(az) != 1:
    sys.exit("ABORT anchor hits en=%d zh=%d" % (len(ae), len(az)))

dl[az[0] + 1:az[0] + 1] = ['  "%s": "%s",' % (k, v) for k, v, _ in KEYS]
dl[ae[0] + 1:ae[0] + 1] = ['  "%s": "%s",' % (k, v) for k, _, v in KEYS]
io.open(DICT, "w", encoding="utf-8", newline="\n").write("\n".join(dl))
print("dict en_at=%d zh_at=%d" % (ae[0] + 2, az[0] + 2 + len(KEYS)))

ps = io.open(PROD, encoding="utf-8").read()
OPS = [
    ('  if (state === "REFERENCED")\n    return zh ? "这批证据带冻结期" : "the frozen evidence carries an expiry";',
     '  if (state === "REFERENCED")\n    return copy("sceneClock.frozenEvidenceCarriesExpiry");'),
    ('  if (state === "NO_FROZEN_EVIDENCE")\n    return zh ? "这趟没有冻结证据" : "no frozen evidence on this trip";',
     '  if (state === "NO_FROZEN_EVIDENCE")\n    return copy("sceneClock.noFrozenEvidenceOnThisTrip");'),
    ('  if (state === "NO_SCENARIO") return zh ? "台上没有场景" : "no scenario on stage";',
     '  if (state === "NO_SCENARIO") return copy("sceneClock.noScenarioOnStage");'),
]
for old, new in OPS:
    if ps.count(old) != 1:
        sys.exit("ABORT prod needle hits=%d for %r" % (ps.count(old), old[:50]))
    ps = ps.replace(old, new, 1)

# evidenceWord needs the same local copy() the batch-1 function already uses
sig = 'export function evidenceWord(state: string | null, zh: boolean): string {'
if ps.count(sig) != 1:
    sys.exit("ABORT evidenceWord signature hits=%d" % ps.count(sig))
ps = ps.replace(sig, sig + '\n  const copy = (key: string) => dictionaryCopy(zh ? "zh-CN" : "en", key);', 1)
io.open(PROD, "w", encoding="utf-8", newline="\n").write(ps)
print("BATCH2_ROWS_ROUTED=3")
