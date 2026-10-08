"""Counter-arm for the Me screen's six body sentences.

The gap this pins: six sentences in `Me()` of frontend/src/app/V8Experience.tsx were hand-written in
two arms inside multi-line ternaries -- exactly the bucket the earlier one-line `zh ? "` census could
not see.  They now read `t("me.*")`, with the keys added to both arms of
frontend/src/i18n/LocaleContext.tsx:
  * me.stayNotChosen, me.stayConfirmed, me.stayChooseInTrips   (the stay card)
  * me.bookingsProtected, me.bookingsImport                   (the bookings card)
  * me.asksBeforeProtectedChange                              (the preferences card)

One of the six is NOT unique: "还没有选定"/"Not chosen yet" also appears at the today strip near the
top of the same file, a different screen.  So "is the inline pair gone" is an empty predicate for
that one -- deleting this site leaves the twin, deleting the twin leaves this one.  Every assertion
below is therefore scoped to a line window, and the last two are counter assertions that pin the
twin's survival so a reader can tell this cell from a sweep.

The root is overridable so the arm can be pointed at a mutated copy of the tree.  An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_i18n_20261008/wt3"
V8 = WT + "/frontend/src/app/V8Experience.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

KEYS = {
    "me.stayNotChosen": ("还没有选定", "Not chosen yet"),
    "me.stayConfirmed": ("已确认的住宿", "Confirmed stay"),
    "me.stayChooseInTrips": ("在「行程 · 住宿」里挑选", "Choose it in Trips · Stay"),
    "me.bookingsProtected": ("受保护的预订，不会被自动改动。",
                             "Protected bookings; they are never changed automatically."),
    "me.bookingsImport": ("在「行程 · 预订」里导入你的票或确认单。",
                          "Import a ticket or confirmation in Trips · Bookings."),
    "me.asksBeforeProtectedChange": (
        "任何会影响已确认预订或受保护安排的改动，都会先征得你同意。",
        "Anything affecting a confirmed booking or protected plan asks you first.",
    ),
}

# The anchors that identify the two cards this cell rewrote.
STAY_CARD = 'className="v8-kicker">{t("my.stay")}'
BOOKINGS_CARD = 't("me.confirmedBookings")'
# The in-file twin: the today strip at the top of the same file, a different screen.
TWIN_WINDOW = 'data-testid="today-stay"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def window_of(lines, anchor, span=14):
    for i, line in enumerate(lines):
        if anchor in line:
            return "\n".join(lines[i:i + span])
    return None


def joined(text):
    """Collapse the newline-and-indent the formatter inserts after a long value's colon.

    A long English value is split after the colon by the formatter, so a substring test for
    '"key": "value"' silently fails on exactly the longest string in this cell.
    """
    return text.replace("\n    ", " ")


def main() -> int:
    bad = []
    checks = 0
    v8 = read(V8)
    dictionary = read(DICT)
    dictionary_flat = joined(dictionary)
    lines = v8.split("\n")

    stay = window_of(lines, STAY_CARD)
    bookings = window_of(lines, BOOKINGS_CARD, span=26)
    twin = window_of(lines, TWIN_WINDOW, span=8)

    # ---- change assertions -------------------------------------------------
    for anchor_name, window in (("stay card", stay), ("bookings card", bookings)):
        checks += 1
        if window is None:
            bad.append("the %s anchor is gone; this arm no longer describes the screen" % anchor_name)

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
            if '"%s": "%s"' % (key, value) not in dictionary_flat:
                bad.append("no %s arm for %s" % (value, key))

    checks += 1
    for key in KEYS:
        if stay is not None and key.startswith("me.stay") and 't("%s")' % key not in stay:
            bad.append("%s is not read inside the stay card window" % key)
        if bookings is not None and key.startswith("me.bookings") and 't("%s")' % key not in bookings:
            bad.append("%s is not read inside the bookings card window" % key)

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    checks += 1
    if twin is None:
        bad.append("the today strip is gone; the twin this cell must not touch has moved")
    elif '"还没有选定"' not in twin:
        bad.append("the in-file twin at the today strip no longer carries its inline pair")

    checks += 1
    if "还没有选定" in v8 and '"还没有选定"' in (stay or ""):
        bad.append("the stay card still carries the inline zh arm")

    print("Me body sentences dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: the today strip's own inline pair is intact")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())