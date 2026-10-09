"""Counter-arm for the trips-tab aria-label and the simulated-commitment badge.

The gap this pins: two elements in frontend/src/app/V8Experience.tsx wrote their text as inline
`{zh ? "...": "..."}` -- the tablist's accessible name in `TripsWorkspace` (a name a screen reader
announces, which is exactly the kind of copy a translator must own) and the "simulated commitment"
badge in `WalletCommitments`. They now read `t("hub.tripsSectionsAria")` and
`t("bookings.commitmentSimulated")`, added to both arms of frontend/src/i18n/LocaleContext.tsx.

Both pairs are unique in the tree, so "does the pair appear anywhere" would work here. It is still
not the predicate used: two counter assertions below pin what this cell must NOT have touched --
the two language-code lookups (`zh ? "zh" : "en"` and `zh ? "zh-CN" : "en-GB"`), which are lookup
keys and routing them through the dictionary would BE a defect, and a neighbouring key this cell
did not add.

The root is overridable so the arm can be pointed at a mutated copy of the tree. An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt6"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

KEYS = {
    "hub.tripsSectionsAria": ("行程分区", "Trip sections"),
    "bookings.commitmentSimulated": ("模拟承诺", "simulated commitment"),
}

TABS = 'data-testid="trips-tabs"'
BADGE = 'data-testid="wallet-commitment-simulated"'
LANG_CODES = ('zh ? "zh" : "en"', 'zh ? "zh-CN" : "en-GB"')
# A neighbouring key in the same arm that this cell did not touch.
UNTOUCHED_KEY = '"bookings.commitmentUnnamed"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def window_of(lines, anchor, span=6):
    for i, line in enumerate(lines):
        if anchor in line:
            return "\n".join(lines[i:i + span])
    return None


def main() -> int:
    bad = []
    checks = 0
    v8 = read(V8)
    dictionary = read(DICT)
    lines = v8.split("\n")

    tabs = window_of(lines, TABS, span=5)
    badge = window_of(lines, BADGE, span=4)

    # ---- change assertions -------------------------------------------------
    checks += 1
    if tabs is None:
        bad.append("the trips-tabs anchor is gone; this arm no longer describes the screen")
    elif 't("hub.tripsSectionsAria")' not in tabs:
        bad.append("the tablist's accessible name does not read hub.tripsSectionsAria")
    elif '"行程分区"' in tabs:
        bad.append("the tablist's accessible name still carries an inline zh arm")

    checks += 1
    if badge is None:
        bad.append("the simulated-commitment anchor is gone; this arm no longer describes the screen")
    elif 't("bookings.commitmentSimulated")' not in badge:
        bad.append("the badge does not read bookings.commitmentSimulated")
    elif '"模拟承诺"' in badge:
        bad.append("the badge still carries an inline zh arm")

    checks += 1
    if 'zh ? "行程分区"' in v8:
        bad.append("the aria-label pair is still hand-written inline")
    if 'zh ? "模拟承诺"' in v8:
        bad.append("the badge pair is still hand-written inline")

    for key, (zh_value, en_value) in KEYS.items():
        checks += 1
        if 't("%s")' % key not in v8:
            bad.append("V8Experience.tsx does not read %s" % key)
        checks += 1
        if dictionary.count('"%s"' % key) != 2:
            bad.append("%s is not present exactly twice in the dictionary: %d"
                       % (key, dictionary.count('"%s"' % key)))
        for value in (zh_value, en_value):
            if '"%s": "%s"' % (key, value) not in dictionary:
                bad.append("no %s arm for %s" % (value, key))

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # They describe what this cell must not have touched, not the change.
    checks += 1
    for code in LANG_CODES:
        if code not in v8:
            bad.append("a language-code lookup is gone; a code was routed into the dictionary: %s" % code)

    checks += 1
    if UNTOUCHED_KEY not in dictionary:
        bad.append("a neighbouring bookings key moved; this cell reached past its own two strings")

    print("trips aria-label and simulated badge dictionary routing: %d checks, %d bad"
          % (checks, len(bad)))
    print("  counter: both language-code lookups intact, neighbouring key intact")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())