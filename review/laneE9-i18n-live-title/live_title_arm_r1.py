"""Counter-arm for the LiveRecovery page's three own headings.

The gap this pins: `frontend/src/features/execution/LiveRecovery.tsx` wrote the page's kicker, its
`<h1>` and the disruption section's heading as inline `{zh ? ... : ...}`. They now read
`t("live.progressKicker")`, `t("live.tripRightNowTitle")` and `t("live.whatHappenedHeading")`,
added to both arms of frontend/src/i18n/LocaleContext.tsx.

Why a NEW key for "In progress" rather than the `exec.state.inProgress` that already holds that
English value: that key's Chinese arm is "进行中", while this screen's inline Chinese arm is
"正在进行". Reusing it would have silently rewritten the Chinese screen while the English screen
still read identically -- the one change a dictionary routing is supposed to make impossible. The
arm carries that as a change assertion (it is red when the key is absent, which is the point), and
keeps two genuine counters: the neighbour key still holds both of its own arms, and this file still
holds the inline pairs this cell did not touch.

The root is overridable so the arm can be pointed at a mutated copy of the tree. An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt8"
LR = WT + "/frontend/src/features/execution/LiveRecovery.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

KEYS = {
    "live.progressKicker": ("正在进行", "In progress"),
    "live.tripRightNowTitle": ("现在的行程", "Your trip right now"),
    "live.whatHappenedHeading": ("发生了什么", "What happened"),
}

# Not copy: language codes routed into the dictionary would be a defect, not a fix.
# The neighbour this cell deliberately did NOT reuse.
NEIGHBOUR_KEY = '"exec.state.inProgress"'
NEIGHBOUR_ZH = "进行中"
# Sites in the same file this cell did not touch.
UNTOUCHED = ('zh ? "连不上服务器，请重试。"', 'zh ? "稍后提醒" : "Remind me later"')


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    src = read(LR)
    dictionary = read(DICT)

    # ---- change assertions -------------------------------------------------
    for key, (zh_value, en_value) in KEYS.items():
        checks += 1
        if 't("%s")' % key not in src:
            bad.append("LiveRecovery.tsx does not read %s" % key)
        if '"%s" : "%s"' % (zh_value, en_value) in src:
            bad.append("%s is still hand-written inline in LiveRecovery.tsx" % key)
        checks += 1
        if dictionary.count('"%s"' % key) != 2:
            bad.append("%s is not present exactly twice in the dictionary: %d"
                       % (key, dictionary.count('"%s"' % key)))
        for value in (zh_value, en_value):
            if '"%s": "%s"' % (key, value) not in dictionary:
                bad.append("no %s arm for %s" % (value, key))

    checks += 1
    for site in ('className="v8-kicker"', "<h1>", "发生了什么"):
        if site not in src:
            bad.append("the %s element this arm anchors on has moved" % site)

    # The neighbour's own Chinese word must NOT appear on this screen: that is the drift a reuse
    # would have caused, so it is a change assertion, not a counter.
    checks += 1
    if '"live.progressKicker": "%s"' % NEIGHBOUR_ZH in dictionary:
        bad.append("live.progressKicker carries the neighbour key's Chinese word; the screen moved")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # Two facts no other cell can break by fixing its own screen: the neighbour key is still there
    # with its own arms (this cell neither reused it nor edited it), and this file still carries
    # inline pairs this cell did not touch -- so the arm cannot be read as "the file is done".
    checks += 1
    if dictionary.count(NEIGHBOUR_KEY) != 2:
        bad.append("exec.state.inProgress moved: expected twice in the dictionary, found %d"
                   % dictionary.count(NEIGHBOUR_KEY))
    if '"exec.state.inProgress": "In progress"' not in dictionary:
        bad.append("exec.state.inProgress lost its English arm")
    if '"exec.state.inProgress": "%s"' % NEIGHBOUR_ZH not in dictionary:
        bad.append("exec.state.inProgress lost its Chinese arm")

    checks += 1
    for untouched in UNTOUCHED:
        if untouched not in src:
            bad.append("an untouched inline pair moved; this cell may have swept the file: %s" % untouched)

    print("LiveRecovery page headings dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: the neighbour key keeps both its arms; this file keeps its untouched pairs")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())