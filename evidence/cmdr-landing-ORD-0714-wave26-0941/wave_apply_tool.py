"""ORD-0714 wave 26: the hero's three counted sentences go to the dictionary, and the English
count noun goes through the one place that decides singular vs plural (`lib/plural.ts`).

Same shape as the wave-25 tool, and the same reason: every replacement must match exactly once or
nothing is written, because a half-moved sentence leaves a screen reading a key that only one of the
two language blocks defines.

One byte-level change is intended, and it is written here rather than smuggled: at n=1 the old inline
English read "1 stops today", because the count and the word were concatenated by hand.  Through
`{n} {plural:stop}` the same slot renders "1 stop today".  Every other rendering is byte-identical --
Chinese carries no plural marker, so the Chinese arm's bytes cannot move by construction.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"D:/moodle/_cmdr_ord0705_wt_1022/frontend/src")
SHELL = ROOT / "app/V8Experience.tsx"
LOC = ROOT / "i18n/LocaleContext.tsx"

NEW_KEYS = [
    ("today.stopsToday", "今天还有 {n} 项安排", "{n} {plural:stop} today"),
    ("today.stopsAfterThis", "后面还有 {n} 站", "{n} {plural:stop} after this"),
    ("today.tripEndsNextStop", "这一趟到下一站就结束了", "This trip ends at the next stop"),
]

HERO_OLD = """                {todayStops.length
                  ? zh
                    ? `今天还有 ${todayStops.length} 项安排`
                    : `${todayStops.length} stops today`
                  : /* An empty calendar day says nothing about whether further stops exist -- only
                       the server's sequence does.  "暂无安排" beside a real later stop was the same
                       contradiction in a smaller font. */
                    remainingAfterNext > 0
                      ? zh
                        ? `后面还有 ${remainingAfterNext} 站`
                        : `${remainingAfterNext} stops after this`
                      : zh
                        ? "这一趟到下一站就结束了"
                        : "This trip ends at the next stop"}"""

HERO_NEW = """                {todayStops.length
                  ? t("today.stopsToday", { n: todayStops.length })
                  : /* An empty calendar day says nothing about whether further stops exist -- only
                       the server's sequence does.  "暂无安排" beside a real later stop was the same
                       contradiction in a smaller font. */
                    remainingAfterNext > 0
                      ? t("today.stopsAfterThis", { n: remainingAfterNext })
                      : t("today.tripEndsNextStop")}"""

REWRITES = [(HERO_OLD, HERO_NEW)]

EN_ANCHOR = '  "itinerary.candidatePreviewNote": "This is a preview of a candidate option - you have not chosen a plan yet.",'
ZH_ANCHOR = '  "itinerary.candidatePreviewNote": "以下只是候选方案的预览，你还没有采用它。",'


def block_lines(pairs, language):
    out = []
    for key, zh, en in pairs:
        value = zh if language == "zh" else en
        if language == "en":
            value = value.replace('"', '\\"')
        out.append('  "{0}": "{1}",'.format(key, value))
    return "\n".join(out)


def main() -> int:
    loc = LOC.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    problems = []

    for anchor, language in ((EN_ANCHOR, "en"), (ZH_ANCHOR, "zh")):
        if loc.count(anchor) != 1:
            problems.append("dictionary anchor matched {0} times in the {1} block".format(
                loc.count(anchor), language))
    for key, _zh, _en in NEW_KEYS:
        if '"{0}"'.format(key) in loc:
            problems.append("key {0} is already in the dictionary -- this wave would duplicate a writer".format(key))
    for old, new in REWRITES:
        hits = shell.count(old)
        if hits != 1:
            problems.append("shell rewrite matched {0} times: {1}".format(hits, old.strip().splitlines()[0][:70]))
    if problems:
        print("ABORT, nothing written:")
        for line in problems:
            print("  -", line)
        return 2

    loc = loc.replace(EN_ANCHOR, EN_ANCHOR + "\n" + block_lines(NEW_KEYS, "en"), 1)
    loc = loc.replace(ZH_ANCHOR, ZH_ANCHOR + "\n" + block_lines(NEW_KEYS, "zh"), 1)
    for old, new in REWRITES:
        shell = shell.replace(old, new, 1)

    LOC.write_bytes(loc.replace("\r\n", "\n").encode("utf-8"))
    SHELL.write_bytes(shell.replace("\r\n", "\n").encode("utf-8"))
    for path in (LOC, SHELL):
        cr = path.read_bytes().count(b"\r")
        if cr:
            raise SystemExit("ABORT after write: {0} carries {1} CR bytes".format(path.name, cr))
    print("wrote {0} keys into both dictionary blocks and {1} shell rewrite; LF kept".format(
        len(NEW_KEYS), len(REWRITES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
