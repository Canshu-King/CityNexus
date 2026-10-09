"""Counter-arm for the continuation refusal's technical fold, cell 2.

Same fold as cell 1 (woodworker r1, commit f575e8abc9a2d457eda3b0a04ba85bbc125a9eaf, which is
NOT on the authoritative line yet).  Cell 1 changed five sentences; a sibling lane landed
b92176ba368c9436efbf5648cec085dbb27e0d1d first and took the fold summary label
(`hub.continuationTechnicalDetail`) alone, so this cell takes the FOUR that were left:

    hub.continuationServerReason      "Server's own reason: "
    hub.continuationNoServerReason    "The server sent no reason text -- this sentence is ours, ..."
    hub.continuationReading           "This device's reading: HTTP {status}"
    hub.continuationNoRequestId       "This screen holds no repeatable code -- this read did not carry one."

`hub.continuationTechnicalDetail` is deliberately NOT in this cell's change set: it already reads
the dictionary on the parent, so the arm asserts it SURVIVES as a dictionary read (if a later cell
re-inlines it, this arm goes red -- that is the point: the fold must not lose ground).

Empty predicates are avoided by name and anchor, never by whole-tree string search:

  * "This device's reading: HTTP" also sits inline three times in components/CnxMeasuredFacts.tsx
    (lines 29, 77, 78).  Removing this cell's copy leaves those three, so "is the pair gone from the
    tree" is true before and after this cell and would never fail.  Two counter assertions pin those
    three lines instead.
  * The other three strings are unique in frontend/src, so their absence in V8Experience.tsx IS a
    real predicate; the arm also counts the file's `zh ? "` shape to give that absence a denominator.
  * Each of the four is asserted on its own `data-testid` anchor, so a sibling cell that moves one
    of them makes the arm red rather than silently out of date.

`hub.continuationServerReason` keeps a trailing space in the en arm on purpose: the old code built
it with a template string and the JSX expression that follows contributes no space of its own, so
trimming it would change the sentence the traveller reads.  `hub.continuationReading` interpolates
the measured status through a `{status}` slot rather than pasting it around the sentence.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt2"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
MEASURED = WT + "/frontend/src/components/CnxMeasuredFacts.tsx"

KEYS = [
    "hub.continuationServerReason",
    "hub.continuationNoServerReason",
    "hub.continuationReading",
    "hub.continuationNoRequestId",
]

# Each key owns one element, named by that element's testid.
ANCHORS = {
    "hub.continuationServerReason": 'data-testid="continuation-resume-server-reason"',
    "hub.continuationNoServerReason": 'data-testid="continuation-resume-no-server-reason"',
    "hub.continuationReading": 'data-testid="continuation-resume-http-status"',
    "hub.continuationNoRequestId": 'data-testid="continuation-resume-no-request-id"',
}

# The hand-written pairs this cell removes, searched as raw text because two were template literals.
INLINE = [
    '"服务器给出的原因："',
    '"Server\'s own reason: "',
    '"服务器没有给出原因文字（这条是本机说的，不是服务器说的）。"',
    '"The server sent no reason text -- this sentence is ours, not the server\'s."',
    "`这台设备看到的回读：HTTP ${resumeOutcome.httpStatus}`",
    "`This device's reading: HTTP ${resumeOutcome.httpStatus}`",
    '"这一屏没有拿到可复述的编号（这条读取没把它送过来）。"',
    '"This screen holds no repeatable code -- this read did not carry one."',
]

ZH_ARM = [
    '"hub.continuationServerReason": "服务器给出的原因："',
    '"hub.continuationNoServerReason": "服务器没有给出原因文字（这条是本机说的，不是服务器说的）。"',
    '"hub.continuationReading": "这台设备看到的回读：HTTP {status}"',
    '"hub.continuationNoRequestId": "这一屏没有拿到可复述的编号（这条读取没把它送过来）。"',
]

EN_ARM = [
    # Trailing space is load-bearing -- see the module docstring.
    '"hub.continuationServerReason": "Server\'s own reason: "',
    '"hub.continuationNoServerReason": "The server sent no reason text -- this sentence is ours, not the server\'s."',
    '"hub.continuationReading": "This device\'s reading: HTTP {status}"',
    '"hub.continuationNoRequestId": "This screen holds no repeatable code -- this read did not carry one."',
]

MEASURED_INLINE = '"This device\'s reading: HTTP"'
# Line 77 is a VARIANT of the label, not the label: the "measured none" branch words it differently.
# So the three lines are asserted by the exact substring each one really carries.
MEASURED_LINES = {
    29: '"This device\'s reading: HTTP"',
    77: '"This device\'s reading: HTTP measured none"',
    78: '"This device\'s reading: HTTP"',
}


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    v8 = read(V8)
    dictionary = read(DICT)
    v8_lines = v8.split("\n")

    # ---- change assertions: the four hand-written pairs are gone -----------------
    for inline in INLINE:
        checks += 1
        if inline in v8:
            bad.append("V8Experience.tsx still hand-writes %s" % inline[:44])

    # ---- change assertions: each key is read on the element that owns it ---------
    for key, anchor in ANCHORS.items():
        checks += 1
        hits = [i for i, l in enumerate(v8_lines) if anchor in l]
        if len(hits) != 1:
            bad.append(
                "the anchor for %s is not on exactly one line: %d (%s)" % (key, len(hits), anchor)
            )
            continue
        window = "\n".join(v8_lines[hits[0]:hits[0] + 9])
        if 't("%s")' % key not in window and 't("%s",' % key not in window:
            bad.append(
                "the element anchored by %s does not read %s: %r"
                % (anchor, key, window.strip()[:110])
            )

    # ---- change assertions: the dictionary owns both arms of each key -----------
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

    # The measured status goes through the slot, not around the sentence.
    checks += 1
    if "hub.continuationReading" in v8 and "{ status: resumeOutcome.httpStatus }" not in v8:
        bad.append("hub.continuationReading is read without passing the measured status")

    # The file's inline-bilingual shape drops by exactly this cell's single removal.  Two of the
    # four sentences were template literals inside a `${...}`, and one was a three-line ternary, so
    # they did not each cost a `zh ? "` line -- the parent had nine and this tree has eight.  The
    # count is computed here rather than quoted, so a sibling cell's edit shows up instead of
    # silently matching a stale literal.
    checks += 1
    shape = len([l for l in v8_lines if 'zh ? "' in l])
    if shape != 8:
        bad.append(
            "V8Experience.tsx holds %d `zh ? \"` lines, expected 8 (the parent had 9)" % shape
        )
    print("  denominator: V8Experience.tsx `zh ? \"` lines now %d (parent 9)" % shape)

    # ---- survival assertion: the sibling lane's fold label must stay routed ------
    checks += 1
    if '{zh ? "技术详情" : "Technical detail"}' in v8:
        bad.append("the fold summary was re-inlined; the sibling lane's change was undone by this cell")
    checks += 1
    fold = [i for i, l in enumerate(v8_lines) if 'data-testid="continuation-technical-toggle"' in l]
    if not fold:
        bad.append("the continuation fold's summary anchor is gone")
    elif 't("hub.continuationTechnicalDetail")' not in "\n".join(v8_lines[fold[0]:fold[0] + 2]):
        bad.append("the fold summary no longer reads hub.continuationTechnicalDetail")

    # ---- counter assertions (green in BOTH states by design) --------------------
    # These describe the counter, not the change: CnxMeasuredFacts.tsx keeps its own hand-written
    # reading label at three named lines, so this cell did not "finish the string".
    checks += 1
    measured = read(MEASURED)
    if MEASURED_INLINE not in measured:
        bad.append("the twin reading label is gone from CnxMeasuredFacts.tsx; the counter moved")
    else:
        measured_lines = measured.split("\n")
        for want in sorted(MEASURED_LINES):
            checks += 1
            needle = MEASURED_LINES[want]
            got = measured_lines[want - 1] if want <= len(measured_lines) else ""
            if needle not in got:
                bad.append(
                    "CnxMeasuredFacts.tsx:%d no longer carries %s: %r" % (want, needle[:40], got.strip()[:80])
                )
        print(
            "  counter: components/CnxMeasuredFacts.tsx:%s still carry the inline reading label"
            % ",".join(str(n) for n in sorted(MEASURED_LINES))
        )

    print("Continuation technical fold cell 2: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())