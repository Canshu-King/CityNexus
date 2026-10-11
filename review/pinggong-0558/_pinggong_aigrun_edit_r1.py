import io, sys

P = r"D:/moodle/_qoder_pinggong_0558_ai/frontend/src/features/planning/aiGenerationRun.ts"
s = io.open(P, encoding="utf-8").read()

IMP_OLD = 'import { classifyReadFailure, type Attribution } from "../../lib/failureAttribution";'
IMP_NEW = IMP_OLD + '\nimport { englishCountNoun } from "../../lib/plural";'

OLD = 'text: `GET /places?city_code=${cityCode} -> ${knownIds.size} places`,'
NEW = 'text: `GET /places?city_code=${cityCode} -> ${knownIds.size} ${englishCountNoun(knownIds.size, "place")}`,'

for old, new in ((IMP_OLD, IMP_NEW), (OLD, NEW)):
    if s.count(old) != 1:
        sys.exit("ABORT needle hits=%d for %r" % (s.count(old), old[:44]))
    s = s.replace(old, new, 1)
    print("ok", old[:44])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("APPLIED=2")
