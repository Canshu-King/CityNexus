import io, re, sys

P = r"D:/moodle/_qoder_pinggong_0555b/frontend/src/lib/sceneClock.ts"
src = io.open(P, encoding="utf-8").read()

CASES = [
    ("FROZEN_WITHOUT_TTL", "evidenceSealedWithoutExpiry"),
    ("EVIDENCE_REFERENCE_INCONSISTENT", "evidenceReferenceMismatch"),
]

# harvest the two split-line arms straight from the file, byte for byte
blocks = {}
for state, key in CASES:
    m = re.search(
        r'  if \(state === "%s"\)\n    return zh\n      \? "([^"]*)"\n      : "([^"]*)";' % state,
        src)
    if not m:
        sys.exit("ABORT could not harvest %s" % state)
    blocks[state] = (key, m.group(1), m.group(2))

# 1) two new members of the key union
u = '  | "evidenceNoFrozen"\n  | "evidenceNoScenario";'
if src.count(u) != 1:
    sys.exit("ABORT key-union anchor hits=%d" % src.count(u))
src = src.replace(u, '  | "evidenceNoFrozen"\n  | "evidenceNoScenario"\n  | "evidenceSealedWithoutExpiry"\n  | "evidenceReferenceMismatch";', 1)

# 2) two new rows in the table, values exactly as harvested
anchor = '  evidenceNoScenario: { zh: "台上没有场景", en: "no scenario on stage" },'
if src.count(anchor) != 1:
    sys.exit("ABORT table anchor hits=%d" % src.count(anchor))
rows = "".join('  %s: { zh: "%s", en: "%s" },\n' % (blocks[s][0], blocks[s][1], blocks[s][2])
               for s, _ in CASES)
src = src.replace(anchor, anchor + "\n" + rows.rstrip("\n"), 1)

# 3) the two call sites stop carrying literals
for state, (key, zh, en) in ((s, blocks[s]) for s, _ in CASES):
    old = '  if (state === "%s")\n    return zh\n      ? "%s"\n      : "%s";' % (state, zh, en)
    new = '  if (state === "%s") return sceneCopy(zh, "%s");' % (state, key)
    if src.count(old) != 1:
        sys.exit("ABORT call-site needle for %s hits=%d" % (state, src.count(old)))
    src = src.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(src)
for s, (k, zh, en) in blocks.items():
    print("harvested %s -> %s | zh=%s | en=%s" % (s, k, zh, en))
print("APPLIED=2 rows+2 union+2 call sites")
