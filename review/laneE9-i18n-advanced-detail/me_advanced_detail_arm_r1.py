"""Counter-arm for the Me screen's advanced-detail summary.

The gap this pins: `frontend/src/app/V8Experience.tsx` wrote the Me screen's fold summary as
`{zh ? "高级详情" : "Advanced detail"}` -- the same sentence hand-written in two arms inside one
expression, so no dictionary key owns it and a translator cannot change it without editing JSX.

The change routes that one element through `t("me.advancedDetail")` and adds the key to both
arms of `frontend/src/i18n/LocaleContext.tsx`.

The string is NOT unique to this file: the same pair still lives inline at
`frontend/src/features/agent/CopilotDock.tsx:411`, which this cell does not touch.  So "does the
inline pair appear anywhere" is an empty predicate -- removing this one leaves the twin, and a
future cell that removes the twin would leave this one.  Every assertion below is therefore
scoped to a named file, and the two counter assertions are the ones that pin the twin's survival
so a reader can tell the two cells apart.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that
# can only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that
# always says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt4"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"

INLINE_PAIR = '"高级详情" : "Advanced detail"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    v8 = read(V8)
    dictionary = read(DICT)
    dock = read(DOCK)

    # ---- change assertions -------------------------------------------------
    checks += 1
    if INLINE_PAIR in v8:
        bad.append("V8Experience.tsx still hand-writes the Me screen's advanced-detail pair inline")

    checks += 1
    if '{t("me.advancedDetail")}' not in v8:
        bad.append("V8Experience.tsx does not read the summary from the dictionary")

    checks += 1
    lines = v8.split("\n")
    anchor = [i for i, l in enumerate(lines) if 'data-testid="me-advanced"' in l]
    if not anchor:
        bad.append("the me-advanced details element is gone; this arm no longer describes the screen")
    else:
        window = "\n".join(lines[anchor[0]:anchor[0] + 3])
        if INLINE_PAIR in window:
            bad.append("the me-advanced summary still carries the inline pair: %r" % window.strip()[:120])
        elif "t(\"me.advancedDetail\")" not in window:
            bad.append("the me-advanced summary does not read me.advancedDetail: %r" % window.strip()[:120])

    checks += 1
    if dictionary.count('"me.advancedDetail"') != 2:
        bad.append(
            "me.advancedDetail is not present exactly twice in the dictionary (arms): %d"
            % dictionary.count('"me.advancedDetail"')
        )

    checks += 1
    if '"me.advancedDetail": "高级详情"' not in dictionary:
        bad.append("the zh arm has no me.advancedDetail value")
    if '"me.advancedDetail": "Advanced detail"' not in dictionary:
        bad.append("the en arm has no me.advancedDetail value")

    # ---- counter assertions (must hold in BOTH states, by design) ---------
    # They describe the counter, not the change: the twin fold in the agent dock keeps its own
    # inline pair, so this cell did not "finish the string".
    checks += 1
    if INLINE_PAIR not in dock:
        bad.append("the twin inline pair in CopilotDock.tsx is gone; the counter for this cell moved")

    checks += 1
    dock_line = [i + 1 for i, l in enumerate(dock.split("\n")) if INLINE_PAIR in l]
    if not dock_line:
        bad.append("the twin pair in CopilotDock.tsx is no longer on a line this arm can point at")

    print("Me advanced-detail dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    if dock_line:
        print("  counter: CopilotDock.tsx:%d still carries the inline pair" % dock_line[0])
    for item in bad:
        print("  BAD: %s" % item)
    if bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())