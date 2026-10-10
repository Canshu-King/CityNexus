import io, sys

P = "frontend/src/features/planning/catalogueReadback.ts"
Q = chr(34)
with io.open(P, encoding="utf-8", newline="") as f:
    rows = f.read().split("\n")

BEFORE = u"    : %sRead back from the server: this city now has ${count} places that can go into a trip.%s;" % (chr(96), chr(96))
AFTER = u"    : %sRead back from the server: this city now has ${count} ${englishCountNoun(count, %splace%s)} that can go into a trip.%s;" % (
    chr(96), Q, Q, chr(96))
IMPORT = u'import { englishCountNoun } from "../../lib/plural";'
ANCHOR = u"export type CatalogueReadback = {"

problems = []
if rows[77] != BEFORE:
    problems.append("line 78 differs: %r" % rows[77][:100])
if rows.count(ANCHOR) != 1:
    problems.append("anchor count=%d" % rows.count(ANCHOR))
if rows.count(IMPORT) != 0:
    problems.append("import already present")
if problems:
    for p in problems:
        sys.stdout.write("ABORT %s\n" % p)
    sys.exit(3)

at = rows.index(ANCHOR)
rows.insert(at, IMPORT)
# locate the moved body line by content, not by arithmetic
body = [i for i, l in enumerate(rows) if l == BEFORE]
assert len(body) == 1, body
rows[body[0]] = AFTER

text = "\n".join(rows)
assert text.count(AFTER) == 1 and text.count(BEFORE) == 0
assert text.count(IMPORT) == 1
assert rows[at - 1].strip() == "", "import landed away from a blank line"
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(text)
sys.stdout.write("OK import_line=%d body_line=%d zh_arm_untouched=%d\n"
                 % (at + 1, body[0] + 1,
                    sum(1 for l in rows if u"zh ? " not in l and u"服务器回读" in l)))
