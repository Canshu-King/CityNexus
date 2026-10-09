"""Counter-arm for the Copilot dock's five module-level label functions.

The gap this pins: `frontend/src/features/agent/CopilotDock.tsx` had five MODULE-LEVEL functions
(`summaryText`, `humanAgentStatus`, `lastRuntimeLabel`, `humanIntent`, `humanVerification`,
`humanAction`) that answered their fallback branch with a hand-written two-arm pair.  A module
function has no `useT()` in scope, so the fix is the same shape the realtime-status cell used: give
the function a translator parameter and move the sentence into the dictionary.

Six fallback sites now read six keys added to both arms of `frontend/src/i18n/LocaleContext.tsx`:

    agent.statusWorking          "Working" / "处理中"          (humanAgentStatus, two returns)
    agent.executedAgainstFacts   "Executed against journey facts" / "已按行程事实执行"
    agent.plannedLocally         "Planned locally only" / "仅在本机规划"
    agent.intentQuestion         "Question" / "问题"
    agent.verificationUnknown    "Verification unknown" / "核验状态未知"
    agent.actionContinue         "Continue" / "继续"

What this arm must NOT be credited with, and pins as surviving:

  * The four MAP TABLES (`FAILED_EXTERNAL`, `STOPPED`, `CANCELLED`, `APPROVAL_REQUIRED`, and the
    intent/verification/action tables) hold both languages as DATA -- `{ zh: "...", en: "..." }` --
    and are read as `zh ? entry.zh : entry.en`.  That is a lookup table, not an inline pair, and
    converting it is a different change.  The arm asserts the `entry.zh : entry.en` reads survive.
  * The four `zh ? "zh" : "en"` language buckets are language codes.
  * `agent.toolWorking` already existed and its zh text happens to equal `agent.statusWorking`'s; the
    two keys are deliberately separate (tool label vs run status), so the arm asserts both exist.

The call sites are asserted one by one: a signature change that forgot a caller is exactly the kind
of defect a typechecker catches only if the caller is in the checked set, and this file is.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt9"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

# Each function must declare the translator parameter.
SIGNATURES = [
    "function summaryText(event: NativeRuntimeEvent, zh: boolean, t: (key: string) => string)",
    "function humanAgentStatus(value: string | null | undefined, zh: boolean, t: (key: string) => string)",
    "function lastRuntimeLabel(executed: boolean, zh: boolean, t: (key: string) => string)",
    "function humanIntent(value: string, zh: boolean, t: (key: string) => string)",
    "function humanVerification(value: string, zh: boolean, t: (key: string) => string)",
    "function humanAction(value: string, zh: boolean, t: (key: string) => string)",
]

# Each call site must pass it.
CALLS = {
    "humanAgentStatus(event.status, zh, t)": 2,  # both arms inside summaryText
    "lastRuntimeLabel(executed, zh, t)": 1,
    "summaryText(event, zh, t)": 1,
    "humanIntent(item.response.intent.name, zh, t)": 1,
    "humanVerification(item.response.verification.status, zh, t)": 1,
    "humanAction(item.response.action.type, zh, t)": 1,
}

KEYS = [
    "agent.statusWorking",
    "agent.executedAgainstFacts",
    "agent.plannedLocally",
    "agent.intentQuestion",
    "agent.verificationUnknown",
    "agent.actionContinue",
]

INLINE = [
    'zh ? "处理中" : "Working"',
    'zh ? "已按行程事实执行" : "Executed against journey facts"',
    'zh ? "仅在本机规划" : "Planned locally only"',
    '(zh ? "问题" : "Question")',
    '(zh ? "核验状态未知" : "Verification unknown")',
    '(zh ? "继续" : "Continue")',
]

ZH_ARM = [
    '"agent.statusWorking": "处理中"',
    '"agent.executedAgainstFacts": "已按行程事实执行"',
    '"agent.plannedLocally": "仅在本机规划"',
    '"agent.intentQuestion": "问题"',
    '"agent.verificationUnknown": "核验状态未知"',
    '"agent.actionContinue": "继续"',
]
EN_ARM = [
    '"agent.statusWorking": "Working"',
    '"agent.executedAgainstFacts": "Executed against journey facts"',
    '"agent.plannedLocally": "Planned locally only"',
    '"agent.intentQuestion": "Question"',
    '"agent.verificationUnknown": "Verification unknown"',
    '"agent.actionContinue": "Continue"',
]

LANG_CODE = '[zh ? "zh" : "en"]'
TABLE_READ = "entry.zh : entry.en"


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    dock = read(DOCK)
    dictionary = read(DICT)
    lines = dock.split("\n")

    # ---- change assertions: the translator parameter is declared ---------------
    for sig in SIGNATURES:
        checks += 1
        if sig not in dock:
            bad.append("a function lost its translator parameter: %s" % sig[:64])

    # ---- change assertions: every call site passes it --------------------------
    for call, want in CALLS.items():
        checks += 1
        got = dock.count(call)
        if got != want:
            bad.append("%s appears %d times, expected %d" % (call, got, want))

    # ---- change assertions: the hand-written fallbacks are gone ---------------
    for inline in INLINE:
        checks += 1
        if inline in dock:
            bad.append("CopilotDock.tsx still hand-writes %s" % inline)

    # ---- change assertions: both arms of all six keys -------------------------
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

    # ---- denominator: the file's inline shape count, as a bound ---------------
    checks += 1
    shape = len([l for l in lines if 'zh ? "' in l])
    if shape > 37:
        bad.append(
            "CopilotDock.tsx holds %d `zh ? \"` lines, more than the parent's 44 minus this cell's 7"
            % shape
        )
    print("  denominator: CopilotDock.tsx `zh ? \"` lines now %d (parent 44, this cell removes 7)" % shape)

    # ---- survival assertions (green in BOTH states by design) -----------------
    # The data-driven lookups are tables, not copy: they must stay.
    checks += 1
    tables = dock.count(TABLE_READ)
    if tables != 4:
        bad.append(
            "the map-table reads changed: %d occurrences of %r (expected 4: humanAgentStatus, intent,"
            " verification, action)" % (tables, TABLE_READ)
        )
    else:
        print("  counter: the four map-table reads still use entry.zh : entry.en")

    checks += 1
    lang = len([l for l in lines if LANG_CODE in l])
    if lang != 4:
        bad.append("the language-code bucket count changed: %d (expected 4)" % lang)
    else:
        print("  counter: the four language-code buckets are still present")

    checks += 1
    if dictionary.count('"agent.toolWorking"') != 2:
        bad.append(
            "agent.toolWorking is no longer defined in both arms: %d"
            % dictionary.count('"agent.toolWorking"')
        )
    else:
        print("  counter: agent.toolWorking is still a separate key in both arms")

    print("Copilot dock module-function dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
