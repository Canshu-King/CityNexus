"""Counter-arm for the Copilot dock's mission header and its three sibling folds.

The gap this pins: `frontend/src/features/agent/CopilotDock.tsx` wrote seven sentences as two-arm
inline expressions across the mission header and the runtime/plan/authority folds, so no dictionary
key owned any of them.  Eight call sites now read seven keys added to both arms of
`frontend/src/i18n/LocaleContext.tsx`:

    agent.missionWorking      "Working on your request"   (:393, the header's bold line)
    agent.ranAgainstFacts     "Ran against your journey facts"   (:396, one arm of the header ternary)
    agent.checkingFacts       "Checking your journey facts…"     (:397 and :406, TWO sites)
    agent.runtimeDetails      "Runtime details"           (:332, the raw-event fold)
    agent.viewMissionPlan     "View safe mission plan"    (:427, the mission-plan fold)
    agent.citynexusAuthority  "CityNexus authority"       (:432, the per-step authority tag)
    agent.stopMission         "Stop mission"              (:477, the stop button)

`agent.checkingFacts` is the reason this arm counts sites, not strings: the same pair appeared twice
(once as the header ternary's else-arm, once as the empty-state paragraph), and a fix that changed
only one of them would leave the other hand-written.  The arm asserts BOTH sites read the key.

Counter assertions pin what this cell must not have touched:

  * The four `zh ? "zh" : "en"` buckets are language codes, not sentences.
  * `agent.toolWorking` is a PRE-EXISTING key (it was the fold's fallback before this cell); the
    cell inserted its new keys next to it, so the arm asserts it is still defined in both arms.

The file's `zh ? "` line count appears as an upper bound, not an equality: this file has three other
cells in flight from the same lane, and an assertion that their correct work turns red is one that
gets switched off.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt8"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

# Each call site, with the number of times it must appear (checkingFacts has two sites).
CALLS = {
    't("agent.missionWorking")': 1,
    't("agent.ranAgainstFacts")': 1,
    't("agent.checkingFacts")': 2,
    't("agent.runtimeDetails")': 1,
    't("agent.viewMissionPlan")': 1,
    't("agent.citynexusAuthority")': 1,
    't("agent.stopMission")': 1,
}

KEYS = [c.split('t("')[1].split('"')[0] for c in CALLS]

INLINE = [
    'zh ? "正在为你处理" : "Working on your request"',
    'zh ? "已按你的行程事实执行" : "Ran against your journey facts"',
    'zh ? "正在核对你的行程事实…" : "Checking your journey facts…"',
    'zh ? "运行详情" : "Runtime details"',
    'zh ? "查看安全任务计划" : "View safe mission plan"',
    'zh ? "CityNexus 授权" : "CityNexus authority"',
    'zh ? "停止任务" : "Stop mission"',
]

ZH_ARM = [
    '"agent.missionWorking": "正在为你处理"',
    '"agent.ranAgainstFacts": "已按你的行程事实执行"',
    '"agent.checkingFacts": "正在核对你的行程事实…"',
    '"agent.runtimeDetails": "运行详情"',
    '"agent.viewMissionPlan": "查看安全任务计划"',
    '"agent.citynexusAuthority": "CityNexus 授权"',
    '"agent.stopMission": "停止任务"',
]
EN_ARM = [
    '"agent.missionWorking": "Working on your request"',
    '"agent.ranAgainstFacts": "Ran against your journey facts"',
    '"agent.checkingFacts": "Checking your journey facts…"',
    '"agent.runtimeDetails": "Runtime details"',
    '"agent.viewMissionPlan": "View safe mission plan"',
    '"agent.citynexusAuthority": "CityNexus authority"',
    '"agent.stopMission": "Stop mission"',
]

LANG_CODE = '[zh ? "zh" : "en"]'
PREEXISTING = '"agent.toolWorking"'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    dock = read(DOCK)
    dictionary = read(DICT)
    lines = dock.split("\n")

    # ---- change assertions: each call site reads its key, the right number of times ----
    for call, want in CALLS.items():
        checks += 1
        got = dock.count(call)
        if got != want:
            bad.append("%s appears %d times, expected %d" % (call, got, want))

    # ---- change assertions: the hand-written pairs are gone -------------------
    for inline in INLINE:
        checks += 1
        if inline in dock:
            bad.append("CopilotDock.tsx still hand-writes %s" % inline[:44])

    # ---- change assertions: both arms of all seven keys -----------------------
    for key in KEYS:
        checks += 1
        hits = dictionary.count('"%s"' % key)
        if hits != 2:
            bad.append("%s is not present exactly twice in the dictionary (arms): %d" % (key, hits))
    checks += 1
    for zh_text in ZH_ARM:
        if zh_text not in dictionary:
            bad.append("the zh arm lost its own text: %s" % zh_text[:50])
    checks += 1
    for en_text in EN_ARM:
        if en_text not in dictionary:
            bad.append("the en arm lost its own text: %s" % en_text[:50])

    # ---- denominator: the file's inline shape count, as a bound ---------------
    checks += 1
    shape = len([l for l in lines if 'zh ? "' in l])
    if shape > 36:
        bad.append(
            "CopilotDock.tsx holds %d `zh ? \"` lines, more than the parent's 44 minus this cell's 8"
            % shape
        )
    print("  denominator: CopilotDock.tsx `zh ? \"` lines now %d (parent 44, this cell removes 8)" % shape)

    # ---- survival assertions (green in BOTH states by design) -----------------
    checks += 1
    lang = len([l for l in lines if LANG_CODE in l])
    if lang != 4:
        bad.append("the language-code bucket count changed: %d (expected 4)" % lang)
    else:
        print("  counter: the four language-code buckets are still present")

    checks += 1
    if dictionary.count(PREEXISTING) != 2:
        bad.append(
            "agent.toolWorking is no longer defined in both arms: %d" % dictionary.count(PREEXISTING)
        )
    else:
        print("  counter: the pre-existing agent.toolWorking key is still defined in both arms")

    print("Copilot dock header/folds dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
