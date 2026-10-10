import io, subprocess, sys

P = "frontend/src/features/planning/aiGenerationRun.ts"
Q = chr(34)
BT = chr(96)
with io.open(P, encoding="utf-8", newline="") as f:
    rows = f.read().split("\n")

BEFORE = u"              text: %sGET /places?city_code=${cityCode} -> ${knownIds.size} places%s," % (BT, BT)
AFTER = u"              text: %sGET /places?city_code=${cityCode} -> ${knownIds.size} ${englishCountNoun(knownIds.size, %splace%s)}%s," % (
    BT, Q, Q, BT)
ANCHOR = u'} from "../../lib/keylessWriteDeadline";'
IMPORT = u'import { englishCountNoun } from "../../lib/plural";'

problems = []
if rows[626] != BEFORE:
    problems.append("line 627 differs: %r" % rows[626][:120])
if rows.count(ANCHOR) != 1:
    problems.append("import anchor count=%d" % rows.count(ANCHOR))
if rows.count(IMPORT) != 0:
    problems.append("import already present")
if problems:
    for p in problems:
        sys.stdout.write("ABORT %s\n" % p)
    sys.exit(3)

at = rows.index(ANCHOR)
rows.insert(at + 1, IMPORT)
body = [i for i, l in enumerate(rows) if l == BEFORE]
assert len(body) == 1, body
rows[body[0]] = AFTER
text = "\n".join(rows)
assert text.count(AFTER) == 1 and text.count(BEFORE) == 0
assert text.count(IMPORT) == 1
assert rows[at].strip() == ANCHOR.strip(), "import did not land right after the draft anchor"
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(text)
sys.stdout.write("OK import_line=%d body_line=%d (draft said 37 and 627)\n" % (at + 2, body[0] + 1))
