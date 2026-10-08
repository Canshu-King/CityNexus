"""Counter-arm for the LiveRecovery change-diff labels.

The gap this pins: `frontend/src/features/execution/LiveRecovery.tsx` wrote five pieces of the
disruption card as inline `{zh ? "...": "..."}` -- the two labels of the change list (`<dt>` Removed
/ Replaced with / Moved), the "Affected:" prefix, and "Suggested change". No key owned any of them,
so a translator had to edit JSX. They now read recovery.diffRemoved, recovery.diffAdded,
recovery.diffMoved, recovery.affectedPrefix and recovery.suggestedChange, added to both arms of
frontend/src/i18n/LocaleContext.tsx.

All five pairs are unique in the tree, so "does the pair appear anywhere" would work here. It is
still not the predicate used: two counter assertions below pin what this cell must NOT have touched,
because a ruler that only asks whether a string moved cannot tell a fix from a sweep. The file has
twelve other inline pairs left; this cell took five.

The root is overridable so the arm can be pointed at a mutated copy of the tree. An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt7"
LR = WT + "/frontend/src/features/execution/LiveRecovery.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

KEYS = {
    "recovery.diffRemoved": ("移出", "Removed"),
    "recovery.diffAdded": ("换成", "Replaced with"),
    "recovery.diffMoved": ("调整时间", "Moved"),
    "recovery.affectedPrefix": (" · 受影响：", " · Affected: "),
    "recovery.suggestedChange": ("推荐怎么改", "Suggested change"),
}

# Sites this cell did not touch; the counter pins that they are still inline.
UNTOUCHED = ('zh ? "正在进行" : "In progress"', 'zh ? "连不上服务器，请重试。"')
# A neighbouring key another cell added; this cell must not have disturbed it.
NEIGHBOUR_KEY = '"recovery.deviceReason"'


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
        if '"%s"' % zh_value in src:
            bad.append("the zh literal for %s is still in LiveRecovery.tsx" % key)
        checks += 1
        if dictionary.count('"%s"' % key) != 2:
            bad.append("%s is not present exactly twice in the dictionary: %d"
                       % (key, dictionary.count('"%s"' % key)))
        for value in (zh_value, en_value):
            if '"%s": "%s"' % (key, value) not in dictionary:
                bad.append("no %s arm for %s" % (value, key))

    checks += 1
    for pair in ('zh ? "移出" : "Removed"', 'zh ? "换成" : "Replaced with"',
                 'zh ? "调整时间" : "Moved"', 'zh ? "推荐怎么改" : "Suggested change"'):
        if pair in src:
            bad.append("a diff-label pair is still hand-written inline: %s" % pair)

    checks += 1
    if 'data-testid="live-diff"' not in src:
        bad.append("the diff list anchor is gone; this arm no longer describes the screen")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # They describe what this cell must not have touched, not the change.
    checks += 1
    for pair in UNTOUCHED:
        if pair not in src:
            bad.append("an untouched inline pair moved; this cell may have swept the file: %s" % pair)

    checks += 1
    if NEIGHBOUR_KEY not in dictionary:
        bad.append("a neighbouring recovery key moved; this cell reached past its own five strings")

    print("LiveRecovery diff labels dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: the file's other inline pairs and the neighbouring key are intact")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())