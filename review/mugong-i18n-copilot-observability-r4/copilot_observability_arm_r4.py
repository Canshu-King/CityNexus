"""Counter-arm for the Copilot dock's runtime-observability fold.

The gap this pins: `frontend/src/features/agent/CopilotDock.tsx` wrote the eight labels inside the
`native-hermes-observability` fold as two-arm inline expressions, so no dictionary key owned any of
them:

    agent.obsAdvancedDetail   "Advanced detail"   / "高级详情"     (the fold summary)
    agent.obsTaskId           "task id"           / "任务编号"
    agent.obsMission          "mission"           / "内部任务"
    agent.obsSteps            "steps"             / "已用步骤"
    agent.obsCurrent          "current"           / "当前"
    agent.obsTool             "tool"              / "工具"
    agent.obsDuration         "duration"          / "耗时"
    agent.obsExecution        "execution"         / "执行方式"

Every one of these strings is unique in frontend/src, so their absence IS a real predicate -- but
this arm still anchors each to the element that carried it (the fold's data-testid and the label
sites inside it), because a sibling cell that moves a label should make this arm red rather than
silently out of date.

Three things this arm deliberately does NOT treat as copy, and pins as surviving:

  * The file uses `zh ? "zh" : "en"` FOUR times (138, 140, 300, 416) to pick a language bucket out
    of `toolLabels` / `lifecycleLabels`.  Those are language codes, not sentences: routing them
    through the dictionary would be introducing a defect.  Line 416 sits INSIDE the fold this cell
    changed, so a whole-line "no inline ternary left in the fold" assertion would be wrong -- this
    arm asserts that line still carries its language code.
  * The fold's `agent.toolWorking` fallback is a PRE-EXISTING key (defined in both arms already);
    this cell did not add it and must not remove it.

Counter assertion: `frontend/src/app/V8Experience.tsx` still hand-writes the `"高级详情" : "Advanced
detail"` pair on its own Me screen.  This cell took only the Copilot dock's copy, so a whole-tree
search for the pair is true before and after; the twin is pinned rather than asserted absent.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt4"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
V8 = WT + "/frontend/src/app/V8Experience.tsx"

KEYS = [
    "agent.obsAdvancedDetail",
    "agent.obsTaskId",
    "agent.obsMission",
    "agent.obsSteps",
    "agent.obsCurrent",
    "agent.obsTool",
    "agent.obsDuration",
    "agent.obsExecution",
]

# The hand-written pairs this cell removes, each as it appeared.
INLINE = [
    '{zh ? "高级详情" : "Advanced detail"}',
    '{zh ? "任务编号" : "task id"}',
    '{zh ? "内部任务" : "mission"}',
    '{zh ? "已用步骤" : "steps"}',
    '{zh ? "当前" : "current"}',
    '{zh ? "工具" : "tool"}',
    '{zh ? "耗时" : "duration"}',
    '{zh ? "执行方式" : "execution"}',
]

ZH_ARM = [
    '"agent.obsAdvancedDetail": "高级详情"',
    '"agent.obsTaskId": "任务编号"',
    '"agent.obsMission": "内部任务"',
    '"agent.obsSteps": "已用步骤"',
    '"agent.obsCurrent": "当前"',
    '"agent.obsTool": "工具"',
    '"agent.obsDuration": "耗时"',
    '"agent.obsExecution": "执行方式"',
]
EN_ARM = [
    '"agent.obsAdvancedDetail": "Advanced detail"',
    '"agent.obsTaskId": "task id"',
    '"agent.obsMission": "mission"',
    '"agent.obsSteps": "steps"',
    '"agent.obsCurrent": "current"',
    '"agent.obsTool": "tool"',
    '"agent.obsDuration": "duration"',
    '"agent.obsExecution": "execution"',
]

FOLD = 'data-testid="native-hermes-observability"'
LANG_CODE = '[zh ? "zh" : "en"]'
TWIN = '"高级详情" : "Advanced detail"'


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
            bad.append("CopilotDock.tsx still hand-writes %s" % inline)

    # ---- change assertions: the fold reads all eight keys ---------------------
    checks += 1
    fold = [i for i, l in enumerate(lines) if FOLD in l]
    if len(fold) != 1:
        bad.append("the observability fold anchor is not on exactly one line: %d" % len(fold))
    else:
        # The fold spans from its <details> to the closing </details>; take a generous window.
        window = "\n".join(lines[fold[0]:fold[0] + 14])
        for key in KEYS:
            checks += 1
            if 't("%s")' % key not in window:
                bad.append("the observability fold does not read %s: %r" % (key, window.strip()[:100]))

    # ---- change assertions: both arms of all eight keys -----------------------
    for key in KEYS:
        checks += 1
        hits = dictionary.count('"%s"' % key)
        if hits != 2:
            bad.append("%s is not present exactly twice in the dictionary (arms): %d" % (key, hits))
    checks += 1
    for zh_text in ZH_ARM:
        if zh_text not in dictionary:
            bad.append("the zh arm lost its own text: %s" % zh_text)
    checks += 1
    for en_text in EN_ARM:
        if en_text not in dictionary:
            bad.append("the en arm lost its own text: %s" % en_text)

    # ---- denominator: the file's inline shape count ---------------------------
    # The count is the absence's DENOMINATOR, not the change's proof: a sibling cell in the same
    # file lowers it further, so asserting an exact number would go falsely red on the tree where
    # both cells have landed.  The change itself is pinned by the fold assertion above, which names
    # the element this cell owns and stays true whoever else edits the file.
    checks += 1
    shape = len([l for l in lines if 'zh ? "' in l])
    if shape > 37:
        bad.append(
            "CopilotDock.tsx holds %d `zh ? \"` lines, more than the parent's 44 minus this cell's 7"
            % shape
        )
    print("  denominator: CopilotDock.tsx `zh ? \"` lines now %d (parent 44, this cell removes 7)" % shape)

    # ---- survival assertions (green in BOTH states by design) -----------------
    # The language-code buckets are NOT copy; the fold's own line 416 must keep its own.
    # Asserted by COUNT, not by line number: a sibling cell editing the same file shifts every line
    # below its own edit, so pinning 138/140/300/416 would go falsely red once that lands.  What must
    # hold is that all four buckets still exist and the fold's own one still sits inside the fold.
    checks += 1
    lang_lines = [i + 1 for i, l in enumerate(lines) if LANG_CODE in l]
    if len(lang_lines) != 4:
        bad.append(
            "the language-code bucket count changed: %d (expected 4): %s"
            % (len(lang_lines), lang_lines)
        )
    elif fold and not (fold[0] < lang_lines[-1] < fold[0] + 14):
        bad.append(
            "the fold's language-code bucket no longer sits inside the fold: %s" % lang_lines
        )
    else:
        print("  counter: language-code buckets still at CopilotDock.tsx:%s" % ",".join(str(n) for n in lang_lines))

    checks += 1
    if 't("agent.toolWorking")' not in dock:
        bad.append("the fold lost its pre-existing agent.toolWorking fallback")

    # The Me screen's twin keeps its own inline pair -- this cell took only the dock's copy.
    checks += 1
    if TWIN not in v8:
        bad.append("the twin inline pair is gone from V8Experience.tsx; the counter for this cell moved")
    else:
        twin_line = [i + 1 for i, l in enumerate(v8.split("\n")) if TWIN in l]
        print("  counter: V8Experience.tsx:%s still carries the inline 高级详情 pair" % twin_line)

    print("Copilot dock observability fold dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
