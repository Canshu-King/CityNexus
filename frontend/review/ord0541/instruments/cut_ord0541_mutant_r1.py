"""ORD-0541 lane: cut the mutant -- the reuse predicate with the tier clause removed.

This is the bundle the A3 arm is supposed to go red on. The candidate refuses to reuse a standing row
unless `visibility` is exactly `LINK_READ` (the commander's ruling); this mutant reuses any standing
row that carries a token, which is the behaviour the ruling exists to forbid. Nothing else changes.
"""
import io
import sys

PATH = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/src/features/poster/posterShare.ts"
CLAUSE = '    if (row.visibility !== POSTER_SHARE_VISIBILITY) continue;\n'

with io.open(PATH, encoding="utf-8", newline="") as handle:
    text = handle.read()

count = text.count(CLAUSE)
if count != 1:
    sys.exit("[mutant] expected exactly one tier clause in %s, found %d" % (PATH, count))

with io.open(PATH, "w", encoding="utf-8", newline="") as handle:
    handle.write(text.replace(CLAUSE, ""))

print("MUTANT_PATCHED removed_clause_chars=%d bytes_now=%d" % (len(CLAUSE), len(text) - len(CLAUSE)))
