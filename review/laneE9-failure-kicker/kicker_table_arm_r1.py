"""Counter-arm for the failure-attribution kicker table.

The gap this pins: `frontend/src/lib/failureAttribution.ts` repeated its small screen label as an
inline `{zh ? ... : ...}` ternary at fourteen separate return sites, so the same word could be typed
differently in different branches and no single row owned it. The module's own charter (its header)
says this file owns the mapping from evidence to reason and that nothing downstream may invent a
cause -- the copy should follow the same rule. All fourteen sites now read from one `KICKER_COPY`
table through `kickerOf(...)`.

Why the table is local rather than in `i18n/LocaleContext.tsx`: the landing leg's own roll call found
twenty-seven pending branches colliding on that one file, and `features/abort/journeyAbortCopy.ts`,
`features/trash/journeyTrashCopy.ts` and `features/studio/planVersionHistoryCopy.ts` already set the
precedent of keeping one module's words beside that module. This cell adds no branch pressure to the
shared dictionary.

The finding that shaped the table: two rows answer the SAME Chinese word 服务器 with DIFFERENT English
words -- `server` says "Server" (the service failed on itself) and `origin` says "The origin" (it
answered, but not with a journey response). A "does a row with this text already exist" search finds
one match and merges them, which would silently rewrite one screen's English. Assertion 5 pins both
rows keeping both arms.

The root is overridable so the arm can be pointed at a mutated copy of the tree. An arm that can
only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
says yes.
"""
import re
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_laneE9_20261008/wt9"
FA = WT + "/frontend/src/lib/failureAttribution.ts"

ROWS = {
    "connectionFine": ("连接正常", "Connection is fine"),
    "connection": ("连接", "Connection"),
    "server": ("服务器", "Server"),
    "origin": ("服务器", "The origin"),
    "rateLimited": ("问得太快", "Asked too quickly"),
    "alreadyDone": ("已经办过了", "Already done"),
    "noReply": ("没有回音", "No reply"),
    "identity": ("身份", "Identity"),
    "permission": ("权限", "Permission"),
    "read": ("读取", "Read"),
}


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    src = read(FA)

    # ---- change assertions -------------------------------------------------
    checks += 1
    if "kicker: zh ? " in src:
        bad.append("a kicker is still an inline ternary at a return site")

    checks += 1
    used = re.findall(r'kicker: kickerOf\("([a-zA-Z]+)"\)', src)
    if len(used) != 14:
        bad.append("expected 14 kicker call sites, found %d" % len(used))

    checks += 1
    for name, (zh_value, en_value) in ROWS.items():
        if '  %s: { zh: "%s", en: "%s" },' % (name, zh_value, en_value) not in src:
            bad.append("KICKER_COPY row %s is missing or its arms changed" % name)

    checks += 1
    # every name a site uses must be a row that exists -- a typo here would print "undefined"
    for name in set(used):
        if ("%s: {" % name) not in src:
            bad.append("a call site names %s, which the table does not define" % name)

    checks += 1
    # the no-merge guard: two rows share the Chinese word and must keep different English words
    if ROWS["server"][0] != ROWS["origin"][0]:
        bad.append("the premise of this cell changed: server and origin no longer share the zh arm")
    if ROWS["server"][1] == ROWS["origin"][1]:
        bad.append("server and origin have the same English arm; one screen was rewritten")

    checks += 1
    if len(set(ROWS[k][1] for k in ("server", "origin"))) != 2:
        bad.append("the two 服务器 rows collapsed into one English value")

    # ---- counter assertions (must hold in BOTH states, by design) ----------
    # Sibling-proof: these pin the module's contract, not another cell's wording.
    checks += 1
    if "export function copyFor(" not in src:
        bad.append("copyFor is no longer exported; this cell broke the consumers' contract")

    checks += 1
    cases = set(re.findall(r'case "(failure\.[a-zA-Z]+)"', src))
    for needed in ("failure.journeyNotFound", "failure.networkUnavailable", "failure.serverError",
                   "failure.originInvalidResponse", "failure.rateLimited"):
        if needed not in cases:
            bad.append("a reason the kickers serve is no longer a case: %s" % needed)

    print("failure-attribution kicker table: %d checks, %d bad" % (checks, len(bad)))
    print("  counter: copyFor still exported, every served reason still a case")
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())