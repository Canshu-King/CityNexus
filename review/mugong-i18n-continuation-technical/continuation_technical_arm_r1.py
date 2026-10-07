"""Counter-arm for the continuation refusal's technical-detail fold.

The gap this pins: `frontend/src/app/V8Experience.tsx` hand-wrote five sentences of the
`today-continuation-technical` fold as two-arm inline expressions -- the same sentence written
twice inside one expression, so no dictionary key owns any of them and a translator cannot change
one without editing JSX:

    hub.continuationNoServerReason    "The server sent no reason text -- ..."
    hub.continuationTechnicalDetail   "Technical detail"
    hub.continuationServerReason      "Server's own reason: "
    hub.continuationReading           "This device's reading: HTTP {status}"
    hub.continuationNoRequestId       "This screen holds no repeatable code -- ..."

Two of these strings are NOT unique to this file, so "does the pair appear anywhere" is an empty
predicate for them and this arm never asks it:

  * `"技术详情" : "Technical detail"` also sits inline in four sibling folds -- PlanWithAiSheet.tsx,
    V14RecoveryTruthPanel.tsx, JourneyTrialSetup.tsx and RealCityDiscoveryPanel.tsx.  Removing the
    one this cell touches leaves those four, so a whole-tree grep for the pair is green before and
    after.  Every assertion on it is scoped to the named anchor
    `data-testid="continuation-technical-toggle"`, and four counter assertions pin the twins'
    survival so a reader can tell this cell apart from a future one that takes them.

  * "This device's reading: HTTP" also sits inline, twice, in components/CnxMeasuredFacts.tsx.
    Two counter assertions pin those too.

The `t()` routing also has to survive a shape change: `hub.continuationServerReason` carries a
trailing space in the en arm because the old code built it as a template string with the space
inside, and the two JSX expressions that follow it are adjacent (JSX inserts no space between
sibling expressions).  If a future edit trims that space the sentence the traveller reads changes,
so this arm asserts the byte.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that
# can only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that
# always says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
# The four sibling folds that keep their own hand-written copy of the "技术详情" pair.
TWINS = [
    WT + "/frontend/src/features/planning/PlanWithAiSheet.tsx",
    WT + "/frontend/src/features/recovery/V14RecoveryTruthPanel.tsx",
    WT + "/frontend/src/features/setup/JourneyTrialSetup.tsx",
    WT + "/frontend/src/features/discovery/RealCityDiscoveryPanel.tsx",
]
MEASURED = WT + "/frontend/src/components/CnxMeasuredFacts.tsx"

KEYS = [
    "hub.continuationNoServerReason",
    "hub.continuationTechnicalDetail",
    "hub.continuationServerReason",
    "hub.continuationReading",
    "hub.continuationNoRequestId",
]

INLINE_TECHNICAL = '"技术详情" : "Technical detail"'
INLINE_READING = '"This device\'s reading: HTTP"'

# The fold's own anchor: this cell changes the fold scoped by this testid, not by string search.
FOLD_TOGGLE = 'data-testid="continuation-technical-toggle"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    v8 = read(V8)
    dictionary = read(DICT)
    v8_lines = v8.split("\n")

    # ---- change assertions -------------------------------------------------
    # Each of the five hand-written pairs is gone from the component.  The reading sentence was a
    # template literal (backticks), so it is searched as raw text, not as a quoted string.
    for inline in (
        '"服务器没有给出原因文字（这条是本机说的，不是服务器说的）。"',
        '"The server sent no reason text -- this sentence is ours, not the server\'s."',
        '"服务器给出的原因："',
        '"Server\'s own reason: "',
        "`这台设备看到的回读：HTTP ${resumeOutcome.httpStatus}`",
        "`This device's reading: HTTP ${resumeOutcome.httpStatus}`",
        '"这一屏没有拿到可复述的编号（这条读取没把它送过来）。"',
        '"This screen holds no repeatable code -- this read did not carry one."',
    ):
        checks += 1
        if inline in v8:
            bad.append("V8Experience.tsx still hand-writes %s" % inline[:48])

    # Each key is read by the component, on the element that owns it.
    for key in KEYS:
        checks += 1
        if 't("%s"' % key not in v8 and "t('%s'" % key not in v8:
            bad.append("V8Experience.tsx does not read %s" % key)

    # The fold is the thing being changed: assert on its anchor, not on the string.
    checks += 1
    anchor = [i for i, l in enumerate(v8_lines) if FOLD_TOGGLE in l]
    if len(anchor) != 1:
        bad.append(
            "the continuation-technical-toggle anchor is not on exactly one line: %d" % len(anchor)
        )
    else:
        window = "\n".join(v8_lines[anchor[0]:anchor[0] + 2])
        if INLINE_TECHNICAL in window:
            bad.append(
                "the continuation fold's summary still carries the inline pair: %r" % window.strip()[:120]
            )
        elif 't("hub.continuationTechnicalDetail")' not in window:
            bad.append(
                "the continuation fold's summary does not read the key: %r" % window.strip()[:120]
            )

    # Each key exists in BOTH arms of the dictionary, exactly once per arm.
    for key in KEYS:
        checks += 1
        hits = dictionary.count('"%s"' % key)
        if hits != 2:
            bad.append("%s is not present exactly twice in the dictionary (arms): %d" % (key, hits))

    # The two arms must not carry the same text -- a key copied into one arm only would route to
    # the en fallback and this arm would still be green.
    checks += 1
    for zh_text in (
        '"hub.continuationTechnicalDetail": "技术详情"',
        '"hub.continuationNoServerReason": "服务器没有给出原因文字（这条是本机说的，不是服务器说的）。"',
        '"hub.continuationNoRequestId": "这一屏没有拿到可复述的编号（这条读取没把它送过来）。"',
        '"hub.continuationServerReason": "服务器给出的原因："',
    ):
        if zh_text not in dictionary:
            bad.append("the zh arm lost its own text: %s" % zh_text[:56])

    checks += 1
    for en_text in (
        '"hub.continuationTechnicalDetail": "Technical detail"',
        '"hub.continuationNoServerReason": "The server sent no reason text -- this sentence is ours, not the server\'s."',
        '"hub.continuationNoRequestId": "This screen holds no repeatable code -- this read did not carry one."',
        # Trailing space is load-bearing: the old code built this with a template string and the
        # following JSX expression contributes no space of its own.
        '"hub.continuationServerReason": "Server\'s own reason: "',
    ):
        if en_text not in dictionary:
            bad.append("the en arm lost its own text: %s" % en_text[:56])

    # The status is interpolated through the dictionary's {status} slot, not pasted around it.
    checks += 1
    if "hub.continuationReading" in v8 and "{ status: resumeOutcome.httpStatus }" not in v8:
        bad.append("hub.continuationReading is read without passing the measured status")

    checks += 1
    if '"hub.continuationReading": "This device\'s reading: HTTP {status}"' not in dictionary:
        bad.append("the en arm's reading sentence does not carry a {status} slot")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # They describe the counter, not the change: this cell did not "finish the string".
    for twin in TWINS:
        checks += 1
        body = read(twin)
        if INLINE_TECHNICAL not in body:
            bad.append("the twin pair is gone from %s; the counter for this cell moved" % twin.rsplit("/", 1)[1])
        else:
            line = [i + 1 for i, l in enumerate(body.split("\n")) if INLINE_TECHNICAL in l]
            if not line:
                bad.append("%s still holds the pair but no line this arm can point at" % twin.rsplit("/", 1)[1])
            else:
                print(
                    "  counter: %s:%d still carries the inline 技术详情 pair"
                    % (twin.rsplit("/frontend/src/", 1)[1], line[0])
                )

    checks += 1
    measured = read(MEASURED)
    if INLINE_READING not in measured:
        bad.append("the twin reading pair in CnxMeasuredFacts.tsx is gone; the counter for this cell moved")
    else:
        line = [i + 1 for i, l in enumerate(measured.split("\n")) if INLINE_READING in l]
        print(
            "  counter: components/CnxMeasuredFacts.tsx:%d still carries the inline reading pair"
            % (line[0] if line else -1)
        )

    print(
        "Continuation technical fold dictionary routing: %d checks, %d bad" % (checks, len(bad))
    )
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
