"""Counter-arm for the trip-setup review step's "必填" family.

The gap this pins: `frontend/src/features/setup/JourneyTrialSetup.tsx` wrote the "not filled in ·
required" phrase as a two-arm inline expression FOUR times, so no dictionary key owned it:

    :830 / :831   inside `missingLine` -- a template that joins `{field.label} <phrase>` per field
    :1289         the review row's arrival fallback
    :1300         the review row's departure fallback
    :1436         the blocked-button hint, which carries a LEADING space in the en arm

The last one is why there are two keys and not one: `trial.fieldRequiredInline` keeps that leading
space, because the old code produced it inside a ternary whose result is rendered directly after a
sibling button's label -- trimming it would run the two words together on screen.

Two shapes make "is the inline phrase gone from the tree" the wrong predicate here, and both are
pinned rather than papered over:

  * `:830` and `:831` were a zh/en PAIR of the same sentence; after the change the two arms differ
    only in the joiner ("、" vs ", ") and the prefix, so the arms stay a `zh` branch and only the
    shared phrase comes from the dictionary.  An arm that asserted "the ternary is gone" would be
    wrong -- the ternary is still there and should be.
  * Three COMMENTS in the file quote the phrase verbatim (804, 1433, 1586).  A whole-file string
    count would never reach zero while those remain, so this arm asserts the inline EXPRESSIONS are
    gone by name and separately asserts the comments survive.

Every assertion is anchored: the component by the data-testid of each element that carried a phrase,
the dictionary by key name in both arms with their exact bytes.  The `zh ? "` line count gives the
absence a denominator: the parent held 47 and this tree holds 44 -- three lines fewer for four
sentences, because `:830`/`:831` were one `zh` branch pair and the review rows used `||` with
parentheses rather than a ternary.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt3"
TRIAL = WT + "/frontend/src/features/setup/JourneyTrialSetup.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

KEYS = ["trial.fieldRequired", "trial.fieldRequiredInline"]

# The hand-written expressions this cell removes.
INLINE = [
    '(zh ? "未填写 · 必填" : "not filled in · required")',
    '(zh ? " 未填写 · 必填" : " not filled in · required")',
    "`${field.label} 未填写 · 必填`",
    "`${field.label} not filled in · required`",
]

ZH_ARM = [
    '"trial.fieldRequired": "未填写 · 必填"',
    # Leading space is load-bearing -- see the module docstring.
    '"trial.fieldRequiredInline": " 未填写 · 必填"',
]
EN_ARM = [
    '"trial.fieldRequired": "not filled in · required"',
    '"trial.fieldRequiredInline": " not filled in · required"',
]

# Each review row is anchored by the element that carried the phrase.
ANCHORS = ['data-testid="review-arrival"', 'data-testid="review-departure"']
# The blocked-button hint has no testid; it is anchored by the sentence its ORD comment sits above.
HINT_COMMENT = "the review step's rows already say"


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    trial = read(TRIAL)
    dictionary = read(DICT)
    lines = trial.split("\n")

    # ---- change assertions: the hand-written expressions are gone --------------
    for inline in INLINE:
        checks += 1
        if inline in trial:
            bad.append("JourneyTrialSetup.tsx still hand-writes %s" % inline[:44])

    # ---- change assertions: each row's element reads the key -------------------
    for anchor in ANCHORS:
        checks += 1
        hits = [i for i, l in enumerate(lines) if anchor in l]
        if len(hits) != 1:
            bad.append("the anchor %s is not on exactly one line: %d" % (anchor, len(hits)))
            continue
        window = "\n".join(lines[hits[0]:hits[0] + 4])
        if 't("trial.fieldRequired")' not in window:
            bad.append("the element at %s does not read trial.fieldRequired: %r" % (anchor, window.strip()[:110]))

    # ---- change assertions: the joined list reads the key in BOTH arms ---------
    # The arms stay a zh branch (only the joiner differs); the phrase must come from the key twice,
    # once per arm.  A single occurrence would mean one arm kept its own copy.
    checks += 1
    joined = [i for i, l in enumerate(lines) if 'missingNow.map((field) => `${field.label} ' in l]
    if len(joined) != 2:
        bad.append(
            "the joined missing-list has %d arms reading the key, expected 2" % len(joined)
        )
    else:
        for i in joined:
            if 't("trial.fieldRequired")' not in lines[i]:
                bad.append("joined-list arm at line %d does not read the key" % (i + 1))

    # ---- change assertions: the blocked hint reads the inline-spaced key -------
    checks += 1
    hint = [i for i, l in enumerate(lines) if HINT_COMMENT in l]
    if not hint:
        bad.append("the blocked-hint comment is gone; this arm no longer describes the site")
    else:
        window = "\n".join(lines[hint[0]:hint[0] + 5])
        if 't("trial.fieldRequiredInline")' not in window:
            bad.append("the blocked hint does not read trial.fieldRequiredInline: %r" % window.strip()[:120])
        if 'step === 3 ?' not in window:
            bad.append("the blocked hint lost its step-3 guard: %r" % window.strip()[:120])

    # ---- change assertions: both arms of both keys ----------------------------
    for key in KEYS:
        checks += 1
        hits = dictionary.count('"%s"' % key)
        if hits != 2:
            bad.append("%s is not present exactly twice in the dictionary (arms): %d" % (key, hits))
    checks += 1
    for zh_text in ZH_ARM:
        if zh_text not in dictionary:
            bad.append("the zh arm lost its own text: %s" % zh_text[:52])
    checks += 1
    for en_text in EN_ARM:
        if en_text not in dictionary:
            bad.append("the en arm lost its own text: %s" % en_text[:52])

    # The two keys must differ by exactly the leading space, or the hint runs into its neighbour.
    checks += 1
    if '"trial.fieldRequired": "not filled in · required"' not in dictionary:
        bad.append("the en fieldRequired value lost its byte form")
    checks += 1
    if '"trial.fieldRequiredInline": " not filled in · required"' not in dictionary:
        bad.append("the en fieldRequiredInline value lost its leading space")

    # The absent ternary must STAY: after this change the two arms differ only in joiner/prefix.
    checks += 1
    if "`还需要填写：${missingNow.map((field) => field.label).join(\"、\")}`" not in trial:
        bad.append("the step-1/2 joined-list branch lost its wording")

    # ---- denominator: the file's inline shape count --------------------------
    checks += 1
    shape = len([l for l in lines if 'zh ? "' in l])
    if shape != 44:
        bad.append(
            "JourneyTrialSetup.tsx holds %d `zh ? \"` lines, expected 44 (the parent held 47)" % shape
        )
    print("  denominator: JourneyTrialSetup.tsx `zh ? \"` lines now %d (parent 47)" % shape)

    # ---- survival assertions: the comments quoting the phrase stay ------------
    # They are documentation, not copy; a cell that "fixed" them would be editing the record.
    for want in ("抵达 未填写 · 必填", "second phrasing of it", "it prints 未填写 · 必填 for"):
        checks += 1
        if want not in trial:
            bad.append("a comment quoting the phrase is gone: %s" % want)

    print("Trip-setup required-field dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())