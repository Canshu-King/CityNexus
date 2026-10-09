"""Counter-arm for the today strip's two sentences.

The gap this pins: the today strip in `Hub()` of frontend/src/app/V8Experience.tsx wrote two
sentences as inline `{zh ? "...": "..."}` -- the lodging label beside the stay tile and the empty
state's headline -- so no dictionary key owned them and a translator had to edit JSX. They now read
`t("hub.stayLabel")` and `t("hub.nothingToPreview")`, added to both arms of
frontend/src/i18n/LocaleContext.tsx.

One of the two is NOT unique: "住宿"/"Stay" also appears twice in
frontend/src/features/stay/HotelsPanel.tsx, a different screen, which this cell does not touch. So
"is the inline pair gone" is an empty predicate for that one -- deleting this site leaves the twins
and deleting the twins leaves this one. Every assertion below is scoped to a line window anchored on
the element this cell rewrote, and the counter assertions pin the twins' survival.

The root is overridable so the arm can be pointed at a mutated copy of the tree. An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt5"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"
HOTELS = WT + "/frontend/src/features/stay/HotelsPanel.tsx"

KEYS = {
    "hub.stayLabel": ("住宿", "Stay"),
    "hub.nothingToPreview": ("还没有可以预览的行程", "Nothing to preview yet"),
}

STRIP = 'data-testid="today-strip"'
EMPTY = 'data-testid="hub-glance-empty"'
TWIN_PAIR = 'zh ? "住宿" : "Stay"'


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
    hotels = read(HOTELS)
    lines = v8.split("\n")

    strip = window_of(lines, STRIP, span=8)
    empty = window_of(lines, EMPTY, span=6)

    # ---- change assertions -------------------------------------------------
    checks += 1
    if strip is None:
        bad.append("the today strip anchor is gone; this arm no longer describes the screen")
    elif 't("hub.stayLabel")' not in strip:
        bad.append("the today strip's lodging label does not read hub.stayLabel")
    elif '"住宿"' in strip:
        bad.append("the today strip's lodging label still carries an inline zh arm")

    checks += 1
    if empty is None:
        bad.append("the empty-state anchor is gone; this arm no longer describes the screen")
    elif 't("hub.nothingToPreview")' not in empty:
        bad.append("the empty state does not read hub.nothingToPreview")
    elif '"还没有可以预览的行程"' in empty:
        bad.append("the empty state still carries an inline zh arm")

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

    checks += 1
    if 'zh ? "还没有可以预览的行程"' in v8:
        bad.append("the empty-state pair is still hand-written inline")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # They describe the twins on another screen, not this change: HotelsPanel keeps its own two
    # inline pairs, so removing this cell's pair is not "the string is gone".
    checks += 1
    if hotels.count(TWIN_PAIR) != 2:
        bad.append("the HotelsPanel twins moved: expected 2 inline pairs, found %d"
                   % hotels.count(TWIN_PAIR))

    checks += 1
    if 't("hub.stayLabel")' in hotels or 't("hub.nothingToPreview")' in hotels:
        bad.append("HotelsPanel.tsx now reads a hub.* key; this cell reached past its own screen")

    print("today strip dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: HotelsPanel.tsx still carries both inline pairs")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())