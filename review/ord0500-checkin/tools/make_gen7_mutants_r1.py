"""Build the two throwaway mutant trees for this generation (neither is ever committed).

Both start as hardlink copies of the delivered candidate tree, so the FIRST thing each edit does is
break the link -- writing through a shared inode would edit `wt16` itself, which is exactly how a
"throwaway" mutation ends up in a delivered blob.  The receipts after each pair prove the delivered
bytes never moved.
"""
import hashlib
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NL = chr(10)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def break_link(src_rel, dst_rel):
    a, b = os.path.join(LANE, src_rel), os.path.join(LANE, dst_rel)
    shared = os.stat(a).st_ino == os.stat(b).st_ino
    os.remove(b)
    with open(a, "rb") as f:
        data = f.read()
    open(b, "wb").write(data)
    return shared, os.stat(a).st_ino == os.stat(b).st_ino


# CE-2 -- the mark comes from the plan's activity status instead of the footprint read
itin = "frontend/src/features/trip/TripItinerary.tsx"
was, still = break_link("wt16/" + itin, "wt18/" + itin)
text = open(os.path.join(LANE, "wt18", itin), encoding="utf-8", newline="").read()
old = NL.join([
    "    const next: Record<string, string> = {};",
    "    for (const stamp of answer.stamps) next[stamp.target_key] = stamp.id;",
    "    setStamped(next);",
])
new = NL.join([
    "    const next: Record<string, string> = {};",
    "    /* MUTATION(ORD-0500 CE-2, throwaway tree wt18, never committed): the mark comes from the",
    "       plan's own activity status instead of the rows the footprint door returned.  Three stops",
    "       are COMPLETED in the sealed demo plan, so this face paints 3 marks on a store holding 0",
    "       rows -- which is the second state machine the order forbids. */",
    '    for (const act of plan?.activities ?? [])',
    '      if (act.status === "COMPLETED") next["activity:" + act.id] = act.id;',
    "    setStamped(next);",
])
assert text.count(old) == 1, text.count(old)
open(os.path.join(LANE, "wt18", itin), "w", encoding="utf-8", newline="").write(text.replace(old, new))

# CE-1 -- the door's own duplicate lookup is removed; only the UNIQUE index can then refuse a replay
main = "backend/app/main.py"
was2, still2 = break_link("wt16/" + main, "mutgen6/" + main)
lines = open(os.path.join(LANE, "mutgen6", main), encoding="utf-8", newline="").read().split(NL)
anchor = [i for i, l in enumerate(lines) if l.strip() == "kind, target_key = _checkin_target(payload)"]
assert len(anchor) == 1, anchor
i0 = next(j for j in range(anchor[0], anchor[0] + 30) if lines[j].strip() == "existing = session.scalars(")
i1 = next(j for j in range(i0, i0 + 12) if lines[j].strip() == ").first()")
indent = lines[i0][: len(lines[i0]) - len(lines[i0].lstrip())]
removed = i1 + 1 - i0
lines[i0:i1 + 1] = [
    indent + "existing = None  # MUTATION(ORD-0500 CE-1, throwaway tree mutgen6, never delivered)",
    indent + "    # the door's own duplicate lookup is gone; only the UNIQUE index can refuse a replay",
]
open(os.path.join(LANE, "mutgen6", main), "w", encoding="utf-8", newline="").write(NL.join(lines))

print("CE-2 tree: link was shared", was, "still shared", still)
print("CE-1 tree: link was shared", was2, "still shared", still2, "lines_removed", removed)
print("wt16 main sha", sha("wt16/" + main)[:16], "mutgen6 sha", sha("mutgen6/" + main)[:16])
print("wt16 itin sha", sha("wt16/" + itin)[:16], "wt18 sha", sha("wt18/" + itin)[:16])
print("CR counts", open(os.path.join(LANE, "mutgen6", main), "rb").read().count(b"\r"))
