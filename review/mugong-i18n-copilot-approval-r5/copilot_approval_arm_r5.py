"""Counter-arm for the Copilot dock's proposal + approval block.

The gap this pins: `frontend/src/features/agent/CopilotDock.tsx` wrote ten sentences of the
`cn-native-proposal` / `cn-copilot-approval` block as two-arm inline expressions, so no dictionary
key owned any of them.  They now read ten keys under the `agent.*` namespace:

    agent.proposalHeading       "Suggestions & protected plans"
    agent.proposalReady         "A suggestion is ready; open advanced detail to see how it was produced."
    agent.proposalNone          "There is nothing for you to decide yet."
    agent.protectedCommitment   "Protected commitment"
    agent.protectedActivity     "Protected activity"
    agent.needsConfirmation     "Needs your confirmation"
    agent.confirmScope          "Anything that affects a confirmed booking or a protected plan ..."
    agent.approve               "Approve"
    agent.reject                "Reject"
    agent.modifyReview          "Modify / Review"

Three counter assertions pin things this cell must NOT have touched.  Each is a near-twin that a
whole-tree string search would confuse with this cell's work:

  * `frontend/src/app/V8Experience.tsx:4829` writes a NEAR-TWIN of `agent.confirmScope` -- the same
    opening clause ("任何会影响已确认预订或受保护安排的改动") with a different ending
    ("都会先征得你同意。" vs "都需要你先确认，系统不会自己改。").  They are two sentences, not one, so
    this cell must not have swallowed the other; the arm asserts the V8 one still reads inline.
  * `frontend/src/i18n/LocaleContext.tsx` already defines `v14.confirmationRequired` with the value
    "需要你确认" for the Recovery screen.  This cell adds its own `agent.needsConfirmation` with the
    same text on purpose (per-feature keys are the house style); the arm asserts the v14 key is still
    there, so a later reader cannot "de-duplicate" the two screens together.
  * The file picks a language bucket out of `toolLabels` / `lifecycleLabels` with `zh ? "zh" : "en"`
    four times (138, 140, 300, 416).  Those are language codes, not sentences.

The `zh ? "` line count is the absence's denominator: the parent held 44 such lines and this tree
holds 35.  Note the count is LINES, not occurrences -- the parent has 45 occurrences because one
line carries two.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt5"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
V8 = WT + "/frontend/src/app/V8Experience.tsx"

KEYS = [
    "agent.proposalHeading",
    "agent.proposalReady",
    "agent.proposalNone",
    "agent.protectedCommitment",
    "agent.protectedActivity",
    "agent.needsConfirmation",
    "agent.confirmScope",
    "agent.approve",
    "agent.reject",
    "agent.modifyReview",
]

INLINE = [
    '{zh ? "建议与受保护安排" : "Suggestions & protected plans"}',
    'zh ? "已经生成建议，展开高级详情可以看到过程。" : "A suggestion is ready; open advanced detail to see how it was produced."',
    'zh ? "还没有需要你决定的改动。" : "There is nothing for you to decide yet."',
    '{zh ? "受保护承诺" : "Protected commitment"}',
    '{zh ? "受保护活动" : "Protected activity"}',
    '{zh ? "需要你确认" : "Needs your confirmation"}',
    '? "任何会影响已确认预订或受保护安排的改动，都需要你先确认，系统不会自己改。"',
    '{zh ? "批准" : "Approve"}',
    '{zh ? "拒绝" : "Reject"}',
    '{zh ? "修改 / 审核" : "Modify / Review"}',
]

ZH_ARM = [
    '"agent.proposalHeading": "建议与受保护安排"',
    '"agent.proposalReady": "已经生成建议，展开高级详情可以看到过程。"',
    '"agent.proposalNone": "还没有需要你决定的改动。"',
    '"agent.protectedCommitment": "受保护承诺"',
    '"agent.protectedActivity": "受保护活动"',
    '"agent.needsConfirmation": "需要你确认"',
    '"agent.confirmScope": "任何会影响已确认预订或受保护安排的改动，都需要你先确认，系统不会自己改。"',
    '"agent.approve": "批准"',
    '"agent.reject": "拒绝"',
    '"agent.modifyReview": "修改 / 审核"',
]
EN_ARM = [
    '"agent.proposalHeading": "Suggestions & protected plans"',
    '"agent.proposalReady": "A suggestion is ready; open advanced detail to see how it was produced."',
    '"agent.proposalNone": "There is nothing for you to decide yet."',
    '"agent.protectedCommitment": "Protected commitment"',
    '"agent.protectedActivity": "Protected activity"',
    '"agent.needsConfirmation": "Needs your confirmation"',
    '"agent.confirmScope": "Anything that affects a confirmed booking or a protected plan needs your confirmation first; nothing is changed automatically."',
    '"agent.approve": "Approve"',
    '"agent.reject": "Reject"',
    '"agent.modifyReview": "Modify / Review"',
]

# The two blocks this cell changed, each anchored by what identifies it in the DOM.
PROPOSAL_CLASS = 'className="cn-native-proposal"'
APPROVAL_TESTID = 'data-testid="native-hermes-approval"'

LANG_CODE = '[zh ? "zh" : "en"]'
V14_KEY = '"v14.confirmationRequired": "需要你确认"'
V8_TWIN = '? "任何会影响已确认预订或受保护安排的改动，都会先征得你同意。"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    dock = read(DOCK)
    dictionary = read(DICT)
    v8 = read(V8)
    lines = dock.split("\n")

    # ---- change assertions: the hand-written pairs are gone -------------------
    for inline in INLINE:
        checks += 1
        if inline in dock:
            bad.append("CopilotDock.tsx still hand-writes %s" % inline[:52])

    # ---- change assertions: each block reads its keys -------------------------
    for anchor, wanted in (
        (PROPOSAL_CLASS, ["agent.proposalHeading", "agent.proposalReady", "agent.proposalNone",
                          "agent.protectedCommitment", "agent.protectedActivity"]),
        (APPROVAL_TESTID, ["agent.needsConfirmation", "agent.confirmScope", "agent.approve",
                           "agent.reject", "agent.modifyReview"]),
    ):
        checks += 1
        hits = [i for i, l in enumerate(lines) if anchor in l]
        if len(hits) != 1:
            bad.append("the anchor %s is not on exactly one line: %d" % (anchor, len(hits)))
            continue
        window = "\n".join(lines[hits[0]:hits[0] + 16])
        for key in wanted:
            checks += 1
            if 't("%s")' % key not in window:
                bad.append("the block at %s does not read %s: %r" % (anchor, key, window.strip()[:100]))

    # ---- change assertions: both arms of all ten keys -------------------------
    for key in KEYS:
        checks += 1
        hits = dictionary.count('"%s"' % key)
        if hits != 2:
            bad.append("%s is not present exactly twice in the dictionary (arms): %d" % (key, hits))
    checks += 1
    for zh_text in ZH_ARM:
        if zh_text not in dictionary:
            bad.append("the zh arm lost its own text: %s" % zh_text[:56])
    checks += 1
    for en_text in EN_ARM:
        if en_text not in dictionary:
            bad.append("the en arm lost its own text: %s" % en_text[:56])

    # ---- denominator: the file's inline shape count ---------------------------
    checks += 1
    shape = len([l for l in lines if 'zh ? "' in l])
    if shape != 35:
        bad.append(
            "CopilotDock.tsx holds %d `zh ? \"` lines, expected 35 (the parent held 44)" % shape
        )
    print("  denominator: CopilotDock.tsx `zh ? \"` lines now %d (parent 44)" % shape)

    # ---- survival assertions (green in BOTH states by design) -----------------
    # The near-twin sentence on the Me screen is a DIFFERENT sentence; this cell must not have
    # swallowed it, and must not be credited with it.
    checks += 1
    if V8_TWIN not in v8:
        bad.append("the near-twin confirmation sentence is gone from V8Experience.tsx; the counter moved")
    else:
        v8_line = [i + 1 for i, l in enumerate(v8.split("\n")) if V8_TWIN in l]
        print("  counter: V8Experience.tsx:%s still writes its own confirmation sentence inline" % v8_line)

    # The Recovery screen's own key keeps its own value; the two screens stay separate keys.
    checks += 1
    if V14_KEY not in dictionary:
        bad.append("v14.confirmationRequired is gone; this cell must not merge the two screens' keys")
    else:
        print("  counter: LocaleContext.tsx still defines v14.confirmationRequired with its own value")

    # Language-code buckets are not copy.
    checks += 1
    lang_lines = [i + 1 for i, l in enumerate(lines) if LANG_CODE in l]
    if lang_lines != [138, 140, 300, 416]:
        bad.append("the language-code bucket lines moved or changed: %s" % lang_lines)
    else:
        print("  counter: language-code buckets still at CopilotDock.tsx:%s" % ",".join(str(n) for n in lang_lines))

    print("Copilot dock proposal/approval dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
