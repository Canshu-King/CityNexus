"""Counter-arm for the Copilot dock's stream-error and action-state sentences.

The gap this pins: `frontend/src/features/agent/CopilotDock.tsx` wrote nine sentences of the
runtime-status surface as two-arm inline expressions, so no dictionary key owned any of them:

    agent.streamUnreadable    "A runtime event could not be read"
    agent.streamReconnecting  "Reconnecting to runtime events"
    agent.streamUnavailable   "Event stream unavailable; received events are preserved"
    agent.stopping            "Stopping…"
    agent.stoppedThrough      "Stopped through CityNexus"
    agent.approvalOffline     "Approval is disabled while offline"
    agent.approvalNoId        "CityNexus approval_id is not available; review in Recovery"
    agent.approvalRecording   "Recording CityNexus approval…"
    agent.approvalRecorded    "Approval recorded; CityNexus still owns execution authorization"

All nine strings are unique in frontend/src, so their absence is a real predicate.  The arm still
states the change per call site (each `setStreamError` / `setActionState` call names its own key)
rather than by a whole-file count, because this file is being edited by sibling cells: an assertion
that another lane's correct work turns red is one that gets switched off, and then it stops
measuring.  The file's `zh ? "` line count appears once as an upper bound, not an equality.

Near-misses this cell must not be credited with:

  * `copyFor(attribution, zh).body ?? t("agent.stopFailed")` and its sibling `t("agent.approvalFailed")`
    are the FALLBACK path of the same two handlers this cell changes.  They were already dictionary
    reads on the parent; this cell adds nothing to them and must not remove them.
  * `zh ? "zh" : "en"` (four language buckets) are language codes, not sentences.

Counter assertion: the two sibling cells in this file (the observability fold labels and the
proposal/approval block) keep their own keys, and the Me screen's same-string twins stay inline --
so "does the string still appear somewhere in the tree" is never the question this arm asks.
"""
import sys

# The root is overridable so this arm can be pointed at a mutated copy of the tree.  An arm that can
# only read its own author's worktree cannot go red on a snapshot, which makes it a ruler that always
# says yes.
WT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_lane_mugong_i18n_20261008/wt7"
DOCK = WT + "/frontend/src/features/agent/CopilotDock.tsx"
DICT = WT + "/frontend/src/i18n/LocaleContext.tsx"

# Each call site names its own key: the setter and the key travel together.
CALLS = [
    ('setStreamError(t("agent.streamUnreadable"))', "setStreamError"),
    ('setStreamError(t("agent.streamReconnecting"))', "setStreamError"),
    ('setStreamError(t("agent.streamUnavailable"))', "setStreamError"),
    ('setActionState(t("agent.stopping"))', "setActionState"),
    ('setActionState(t("agent.stoppedThrough"))', "setActionState"),
    ('setActionState(t("agent.approvalOffline"))', "setActionState"),
    ('setActionState(t("agent.approvalNoId"))', "setActionState"),
    ('setActionState(t("agent.approvalRecording"))', "setActionState"),
    ('setActionState(t("agent.approvalRecorded"))', "setActionState"),
]

KEYS = [c.split('t("')[1].split('"')[0] for c, _ in CALLS]

# The hand-written expressions this cell removes, each as it appeared.
INLINE = [
    'zh ? "运行事件暂时无法解析" : "A runtime event could not be read"',
    'zh ? "正在重新连接运行事件" : "Reconnecting to runtime events"',
    'zh ? "运行事件流不可用；已保留已收到的事件" : "Event stream unavailable; received events are preserved"',
    'zh ? "正在停止…" : "Stopping…"',
    'zh ? "已通过 CityNexus 停止" : "Stopped through CityNexus"',
    'zh ? "离线时不能确认方案" : "Approval is disabled while offline"',
    'zh ? "缺少 CityNexus approval_id，需打开恢复中心审核" : "CityNexus approval_id is not available; review in Recovery"',
    'zh ? "正在记录 CityNexus 确认…" : "Recording CityNexus approval…"',
    'zh ? "确认已记录；仍需由 CityNexus 执行授权" : "Approval recorded; CityNexus still owns execution authorization"',
]

ZH_ARM = [
    '"agent.streamUnreadable": "运行事件暂时无法解析"',
    '"agent.streamReconnecting": "正在重新连接运行事件"',
    '"agent.streamUnavailable": "运行事件流不可用；已保留已收到的事件"',
    '"agent.stopping": "正在停止…"',
    '"agent.stoppedThrough": "已通过 CityNexus 停止"',
    '"agent.approvalOffline": "离线时不能确认方案"',
    '"agent.approvalNoId": "缺少 CityNexus approval_id，需打开恢复中心审核"',
    '"agent.approvalRecording": "正在记录 CityNexus 确认…"',
    '"agent.approvalRecorded": "确认已记录；仍需由 CityNexus 执行授权"',
]
EN_ARM = [
    '"agent.streamUnreadable": "A runtime event could not be read"',
    '"agent.streamReconnecting": "Reconnecting to runtime events"',
    '"agent.streamUnavailable": "Event stream unavailable; received events are preserved"',
    '"agent.stopping": "Stopping…"',
    '"agent.stoppedThrough": "Stopped through CityNexus"',
    '"agent.approvalOffline": "Approval is disabled while offline"',
    '"agent.approvalNoId": "CityNexus approval_id is not available; review in Recovery"',
    '"agent.approvalRecording": "Recording CityNexus approval…"',
    '"agent.approvalRecorded": "Approval recorded; CityNexus still owns execution authorization"',
]

LANG_CODE = '[zh ? "zh" : "en"]'


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    bad = []
    checks = 0
    dock = read(DOCK)
    dictionary = read(DICT)

    # ---- change assertions: each call site names its key ----------------------
    for call, _ in CALLS:
        checks += 1
        if call not in dock:
            bad.append("CopilotDock.tsx no longer reads %s" % call)

    # ---- change assertions: the hand-written pairs are gone -------------------
    for inline in INLINE:
        checks += 1
        if inline in dock:
            bad.append("CopilotDock.tsx still hand-writes %s" % inline[:44])

    # ---- change assertions: both arms of all nine keys ------------------------
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
    shape = len([l for l in dock.split("\n") if 'zh ? "' in l])
    if shape > 35:
        bad.append(
            "CopilotDock.tsx holds %d `zh ? \"` lines, more than the parent's 44 minus this cell's 9"
            % shape
        )
    print("  denominator: CopilotDock.tsx `zh ? \"` lines now %d (parent 44, this cell removes 9)" % shape)

    # ---- survival assertions (green in BOTH states by design) -----------------
    # The pre-existing fallbacks of the two handlers this cell touches.
    checks += 1
    if 't("agent.stopFailed")' not in dock:
        bad.append("the stop handler lost its pre-existing agent.stopFailed fallback")
    checks += 1
    if 't("agent.approvalFailed")' not in dock:
        bad.append("the approve handler lost its pre-existing agent.approvalFailed fallback")

    # Language-code buckets are not copy.
    checks += 1
    lang = len([l for l in dock.split("\n") if LANG_CODE in l])
    if lang != 4:
        bad.append("the language-code bucket count changed: %d (expected 4)" % lang)
    else:
        print("  counter: the four language-code buckets are still present")

    print("Copilot dock stream/action-state dictionary routing: %d checks, %d bad" % (checks, len(bad)))
    for item in bad:
        print("  BAD: %s" % item)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
