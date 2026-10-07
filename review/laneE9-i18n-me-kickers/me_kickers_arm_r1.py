"""Counter-arm for the Me screen's five card kickers.

The gap this pins: `frontend/src/app/V8Experience.tsx` wrote five card headings on the Me screen as
`{zh ? "...": "..."}` -- each sentence hand-written in two arms inside one JSX expression, so no
dictionary key owns any of them and a translator cannot change one without editing JSX.

The change routes all five through `t("me.*")` and adds the keys to both arms of
`frontend/src/i18n/LocaleContext.tsx`:
  * me.confirmedBookings        (the bookings card's kicker)
  * me.changePreferences        (the preferences card's kicker)
  * me.allowAutomaticChanges    (the label beside the mode toggle)
  * me.delegationScope          (the fold's first card)
  * me.technicalIdentifiers     (the fold's second card)

All five pairs are unique in the tree, so "does the pair appear anywhere" would work here.  It is
still not the predicate used: two counter assertions below pin the things this cell must NOT have
touched, because a ruler that only asks whether a string moved cannot tell a fix from a sweep.

The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt2"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"

KEYS = {
    "me.confirmedBookings": ("已确认的预订", "Confirmed bookings"),
    "me.changePreferences": ("改动偏好", "Change preferences"),
    "me.allowAutomaticChanges": ("开启自动执行", "Allow automatic changes"),
    "me.delegationScope": ("委派范围", "Delegation scope"),
    "me.technicalIdentifiers": ("技术标识", "Technical identifiers"),
}

# Not copy: a language code is a lookup key, routing it through the dictionary would BE a defect.
LANG_CODE = 'CITY_NAME_BY_SLUG[citySlug]?.[zh ? "zh" : "en"]'
# The fold summary of the same screen is a different cell's work and is still inline here; this
# arm must not imply the screen was finished.
FOLD_PAIR = '"高级详情" : "Advanced detail"'


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
    for key, (zh_value, en_value) in KEYS.items():
        checks += 1
        if '"%s" : "%s"' % (zh_value, en_value) in v8:
            bad.append("%s is still hand-written inline in V8Experience.tsx" % key)
        if 't("%s")' % key not in v8:
            bad.append("V8Experience.tsx does not read %s" % key)
        checks += 1
        if dictionary.count('"%s"' % key) != 2:
            bad.append("%s is not present exactly twice in the dictionary: %d"
                       % (key, dictionary.count('"%s"' % key)))
        for value in (zh_value, en_value):
            if '"%s": "%s"' % (key, value) not in dictionary:
                bad.append("no %s arm for %s" % (value, key))

    checks += 1
    if 'zh ? "已确认的预订"' in v8 or 'zh ? "委派范围"' in v8:
        bad.append("a Me card kicker still carries an inline zh arm")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    checks += 1
    if LANG_CODE not in v8:
        bad.append("the language-code lookup is gone; a code was routed into the dictionary")

    checks += 1
    if FOLD_PAIR not in v8:
        bad.append("the fold summary's inline pair is gone; this arm no longer describes the screen")
    if FOLD_PAIR not in dock:
        bad.append("the twin fold in CopilotDock.tsx is gone; the counter for the fold cell moved")

    print("Me card kickers dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: language-code lookup intact, fold pair still inline in both files")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())