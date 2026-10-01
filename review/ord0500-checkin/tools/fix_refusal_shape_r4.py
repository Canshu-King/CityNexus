"""ORD-0500 r4 -- keep the refusal name on the result, because a landed screen reads it.

The recut conflict is not only cosmetic: ORD-0530's footprint panel calls
`readCheckins(...)` and switches on `answer.refusal` (`frontend/src/features/checkin/FootprintPanel.tsx:59`
at tip 514b397f), while my r1 moved the code into a `facts` object and left `refusal` off the union,
so `tsc` answers TS2339 and their screen stops compiling.  Their file is not mine to rewrite.

The fix stays on my side and keeps one source of truth: the refusal result carries `facts`, and the
two fields a caller already reads are read out of that same object at construction, so no second copy
of the decision exists to drift.
"""
import hashlib
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "wt19", "frontend", "src", "features", "checkin", "checkins.ts")
NL = chr(10)
text = open(PATH, encoding="utf-8", newline="").read()

OLD_UNION = '  | { kind: "refused"; facts: CheckinRefusalFacts }'
NEW_UNION = '  | { kind: "refused"; facts: CheckinRefusalFacts; refusal: CheckinRefusal; status: number }'
OLD_RETURN = '    return { kind: "refused", facts: factsOf(answer.body, answer.status) };'
HELPER = NL.join([
    "/**",
    " * One construction site for a refusal. `facts` is the whole answer; `refusal` and `status` are",
    " * read out of it here rather than stored beside it, because ORD-0530's footprint panel switches",
    " * on `answer.refusal` and this module must keep answering that name.",
    " */",
    "function refused(",
    "  body: unknown,",
    "  status: number,",
    "): { kind: \"refused\"; facts: CheckinRefusalFacts; refusal: CheckinRefusal; status: number } {",
    "  const facts = factsOf(body, status);",
    "  return { kind: \"refused\", facts, refusal: facts.refusal, status: facts.status };",
    "}",
    "",
])
if text.count(OLD_UNION) != 2:
    raise SystemExit("ABORT_UNION_COUNT %d" % text.count(OLD_UNION))
text = text.replace(OLD_UNION, NEW_UNION)
if text.count(OLD_RETURN) != 2:
    raise SystemExit("ABORT_RETURN_COUNT %d" % text.count(OLD_RETURN))
anchor = "/** One tap on one stop."
if text.count(anchor) != 1:
    raise SystemExit("ABORT_HELPER_ANCHOR")
text = text.replace(anchor, HELPER + anchor)
text = text.replace(OLD_RETURN, "    return refused(answer.body, answer.status);")
open(PATH, "w", encoding="utf-8", newline="\n").write(text)
raw = open(PATH, "rb").read()
print("checkins.ts bytes=%d CR=%d sha256=%s" % (len(raw), raw.count(b"\r"),
                                                hashlib.sha256(raw).hexdigest()[:16]))
print("refused() sites:", text.count("return refused(answer.body, answer.status);"))
