"""ORD-0082/0085/0086/0087 kill evidence -- does each new gate actually defend its own fix?

A green gate proves nothing by itself: it may be asserting something the screen says anyway.  So
every behaviour this round added gets one mutant that removes *that* behaviour, and the run has to
name the node that owns it.  Survivals are reported as survivals.

Same discipline as the ORD-0066/0072 batch, keeping the bug that batch found fixed: the mutant is
written, then read back from disk before the suite is trusted, because a mutant that never landed
turns every node into a false SURVIVED.
"""

import hashlib
import os
import socket
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_integration_20260919"
FRONTEND = f"{ROOT}/frontend"
HERO = "src/app/V8Experience.tsx"
PANEL = "src/features/simulation/SimulationPanel.tsx"
ADAPTER = "src/features/simulation/simulationAdapter.ts"
SHEET = "src/features/simulation/SimulationPanel.css"
CLOCK = "src/lib/sceneClock.ts"
STAGE_SPEC = "e2e/qoder-today-follows-the-stage.spec.ts"
SHEET_AI = "src/features/planning/PlanWithAiSheet.tsx"
STYLES = "src/styles.css"
AI_SPEC = "e2e/qoder-ai-sheet-blocked.spec.ts"
MAP = "src/components/v8/MapPanel.tsx"
MAP_SPEC = "e2e/qoder-map-gesture-ownership.spec.ts"
INBOX = "src/features/inbox/JourneyInboxWorkbench.tsx"
EXPERIENCE = "src/app/V8Experience.tsx"
ATTRIBUTION = "src/lib/failureAttribution.ts"
INBOX_SPEC = "e2e/qoder-inbox-review-queue.spec.ts"
EXIT_SPEC = "e2e/qoder-failure-has-an-exit.spec.ts"
WIZARD = "src/features/setup/JourneyTrialSetup.tsx"
WIZ_SPEC = "e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts"
OFFLINE_LIB = "src/lib/offlineJourney.ts"
OFFLINE_SPEC = "e2e/qoder-offline-persistence.spec.ts"
REPLAN_SPEC = "e2e/qoder-replan-review-actions.spec.ts"
PREP = "src/features/discovery/DestinationPreparationPanel.tsx"
PREP_SPEC = "e2e/qoder-destination-preparation.spec.ts"
NA_SPEC = "e2e/qoder-not-answered-cell.spec.ts"
TONGUE_SPEC = "e2e/qoder-speaks-the-travellers-language.spec.ts"
DEMO_SPEC = "e2e/qoder-demo-entry-addresses-dont-create.spec.ts"
TIERS_SPEC = "e2e/qoder-budget-advisory-tiers.spec.ts"
WIZ2_SPEC = "e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts"
I18N = "src/i18n/LocaleContext.tsx"
COPY_SPEC = "e2e/qoder-demo-entry-copy-matches-the-stage.spec.ts"
SURFACE_SPEC = "e2e/qoder-wizard-hint-surface-readings.spec.ts"
SCENE_SPEC = "e2e/qoder-simulation-scene.spec.ts"
WALLET_SPEC = "e2e/qoder-wallet-commitments.spec.ts"
LOGDIR = f"{ROOT}/review"

# (name, file, anchor, mutant, [(spec, [node titles])])
CASES = [
    (
        "killA1-hero-stops-reading-the-servers-projection",
        HERO,
        '  const useProjection = byStage && cursorStatus !== "STALE";\n',
        "  const useProjection = false;\n",
        [(STAGE_SPEC, ["sim-today-hero-follows-the-stage"])],
    ),
    (
        # Today is never told the stage moved: both the dedicated node and the co-mandated one
        # (ORD-0088 #3) must go red.
        "killA2-today-is-never-told-the-stage-moved",
        HERO,
        "        onStageChanged={onStageChanged}\n",
        "        onStageChanged={null}\n",
        [
            (STAGE_SPEC, ["sim-today-hero-follows-the-stage"]),
            (SCENE_SPEC, ["sim-scene-advances-on-server"]),
        ],
    ),
    (
        "killA3-unknown-price-is-shown-as-money",
        HERO,
        "                    {known && amountMinor != null\n",
        "                    {amountMinor != null\n",
        [(WALLET_SPEC, ["ord0087-unknown-price-is-said-unknown"])],
    ),
    (
        "killA4-simulated-label-ignores-the-field",
        HERO,
        '            const simulated = String(item.external_ref ?? "").startsWith("mock-");\n',
        "            const simulated = true;\n",
        [(WALLET_SPEC, ["ord0087-simulated-label-comes-from-the-field"])],
    ),
    (
        "killA5-attention-contradicts-the-map-again",
        HERO,
        "  const tripUnlocatable = mapReportsNoLocation ?? tripHasNoCoordinates(data);\n",
        "  const tripUnlocatable = false;\n",
        [
            (STAGE_SPEC, ["today-attention-does-not-contradict-the-map"]),
            (STAGE_SPEC, ["today-attention-agrees-with-the-map-when-nothing-can-be-placed"]),
        ],
    ),
    (
        # Substituting ORD-0088 #3's values asked whether the co-mandated gate reddens when the scene
        # moves and Today's line does not.  Switching the projection read off was meant to be that
        # shape; the measured answer is **SURVIVED, and that is the finding** -- with `byStage` off,
        # the fallback window is still measured against `nowMs = stageMs`, i.e. the *server's* scene
        # minute (ORD-0088 item 1), so the hero keeps following the stage.  The frozen-hero defect
        # therefore cannot be put back by breaking one path; both clocks would have to go, which is
        # what the two `today-scene-window-*` mutants below aim at instead.
        "killA6-hero-still-follows-without-the-projection",
        HERO,
        "  const byStage = !usingDeviceClock && Boolean(execution);\n",
        "  const byStage = false;\n",
        [
            (SCENE_SPEC, ["sim-scene-advances-on-server"]),
            (STAGE_SPEC, ["sim-today-hero-follows-the-stage"]),
        ],
    ),
    (
        "killA7-scene-window-called-device-time-in-the-diagnostic",
        HERO,
        '                      "SCENE_WINDOW"\n',
        '                      "DEVICE_WINDOW"\n',
        [(STAGE_SPEC, ["today-scene-window-is-not-called-device-time"])],
    ),
    (
        "killA8-scene-window-says-the-device-own-time-out-loud",
        HERO,
        '                      ? " · 服务器的执行投影还没到，这一屏没有按游标定位"\n',
        '                      ? " · 这一屏用的是这台设备自己的时间，只是顺带没拿到游标"\n',
        [(STAGE_SPEC, ["today-scene-window-is-not-called-device-time"])],
    ),
    (
        # The shape ORD-0087's residual actually was: the cards exist in the DOM on the phone's
        # Trips -> 预订 tab but are drawn inside a disclosure labelled 高级 / 开发者, so they read
        # `hidden` to a thumb and to Playwright.  Removing the hoisted section puts that back.
        "killA9-commitments-only-under-the-developer-disclosure",
        HERO,
        '          <div className="v8-booking-grid" data-testid="trips-commitments">\n'
        '            <WalletCommitments wallet={wallet} timezone={data.journey.timezone || undefined} />\n'
        "          </div>\n",
        "",
        [(WALLET_SPEC, ["ord0087-booked-commitment-is-on-the-wallet-screen"])],
    ),
    (
        # The floating widget (the traveller's "别把屏幕挡住"): one mutant per clause the new gate
        # asserts, so "the gate is green" cannot mean "nobody ever broke any of the six promises".
        "killD1-widget-opens-on-its-own",
        PANEL,
        "  const [open, setOpen] = useState<boolean>(() => defaultOpen ?? false);\n",
        "  const [open, setOpen] = useState<boolean>(() => true);\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        # SURVIVED by design, re-read this round: the resting position is no longer taken from this
        # custom property.  `useBottomChromeClearance` measures the nav / Copilot pill / wizard CTA and
        # writes an inline `bottom`, so the CSS value only covers the frame before the first
        # measurement.  The behaviour it used to own is killD9 below.
        "killD2-ball-parked-in-the-nav-band",
        SHEET,
        "    --cn-sim-float-clearance: calc(124px + env(safe-area-inset-bottom, 0px) + 12px);\n",
        "    --cn-sim-float-clearance: 24px;\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killD9-ball-clearance-is-not-measured",
        PANEL,
        "      setBottom(Math.max(12, window.innerHeight - top + 12));\n",
        "      setBottom(24);\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        # ORD-0100 ①: the slot answer is what separates "the catalogue lists it" from "the server can
        # book it" -- measured in review/bookable-target-shape.json, where the food service is listed,
        # answers no slot, and is refused as `not available in the frozen catalog`.
        "killD10-booking-target-ignores-the-slot-answer",
        ADAPTER,
        "      const count = Array.isArray(slots) ? slots.length : 0;\n",
        "      const count = 1;\n",
        [(STAGE_SPEC, ["sim-booking-target-is-an-activity-the-server-gives-a-slot-for"])],
    ),
    (
        # The defect the order was written about: with `city_service_id` null on every activity, the old
        # ordering left the target at whatever the array holds first.
        "killD11-booking-target-falls-back-to-array-order",
        PANEL,
        "    ? bookableRead.data.targets\n",
        "    ? openActivities\n",
        [(STAGE_SPEC, ["sim-booking-target-is-an-activity-the-server-gives-a-slot-for"])],
    ),
    (
        # ORD-0100 ②: the row must say which proposal it is about to send.
        "killD12-accept-row-does-not-name-its-target",
        PANEL,
        '      zh: proposalId ? `接受方案：${shortId(proposalId)}` : "接受方案",\n',
        '      zh: "接受方案",\n',
        [(STAGE_SPEC, ["sim-replan-receipt-names-the-proposal-the-row-sends"])],
    ),
    (
        # ORD-0134 ①: the sheet must not be its own scrollport.  Let it scroll again and the pinned
        # footer falls back below the fold -- the reading the Commander measured on a phone (360x640,
        # submit centre y=790, `elementFromPoint` -> nothing).  An earlier version of this mutant
        # switched the *middle's* overflow instead and SURVIVED: the footer is held by flex layout,
        # not by that property, so the criterion was re-aimed at the line that carries it.
        "killF1-sheet-scrolls-its-own-footer",
        STYLES,
        "  display: flex;\n  flex-direction: column;\n  overflow: hidden;\n",
        "  display: flex;\n  flex-direction: column;\n  overflow: auto;\n",
        [(AI_SPEC, ["ord0134-ai-sheet-actions-stay-inside-the-visible-viewport"])],
    ),
    (
        # A footer that may shrink is a footer that gets squeezed out of the visible box.
        "killF3-footer-may-shrink-again",
        STYLES,
        ".plan-ai-head,\n.plan-ai-actions {\n  flex: none;\n}",
        ".plan-ai-head,\n.plan-ai-actions {\n  flex: 0 1 auto;\n}",
        [(AI_SPEC, ["ord0134-ai-sheet-actions-stay-inside-the-visible-viewport"])],
    ),
    (
        # The other half of the fix: bound by the visible viewport, not only by `vh`.
        "killF2-sheet-sized-by-layout-viewport-only",
        STYLES,
        "  max-height: min(92vh, calc(var(--vv-height, 100dvh) - var(--vv-offset, 0px)));\n",
        "  max-height: 92vh;\n",
        [(AI_SPEC, ["ord0134-ai-sheet-actions-stay-inside-the-visible-viewport"])],
    ),
    (
        # ORD-0107: three silences this order closed, each with the arm that owns it.
        "killE1-short-catalogue-is-silent-again",
        SHEET_AI,
        "          if (knownIds.size < 2) {\n",
        "          if (false) {\n",
        [(AI_SPEC, ["ord0107-ai-sheet-names-why-it-could-not-plan"])],
    ),
    (
        "killE2-unreadable-catalogue-is-silence",
        SHEET_AI,
        "          if (!placesResponse.ok) {\n",
        "          if (false) {\n",
        [(AI_SPEC, ["ord0107-ai-sheet-names-why-it-could-not-plan"])],
    ),
    (
        "killE3-reason-code-stops-routing-the-copy",
        SHEET_AI,
        '  if (s.startsWith("BLOCKED:")) {\n',
        "  if (false) {\n",
        [(AI_SPEC, ["ord0107-ai-sheet-names-why-it-could-not-plan"])],
    ),
    (
        # The old defect itself: a shortlist built from the read's order.
        "killE4-sheet-picks-places-by-position",
        SHEET_AI,
        "              body: JSON.stringify({ candidate_count: 3 }),\n",
        "              body: JSON.stringify({ place_ids: [...knownIds].slice(0, 8), candidate_count: 3 }),\n",
        [(AI_SPEC, ["ord0107-ai-sheet-names-why-it-could-not-plan"])],
    ),
    (
        "killD3-escape-does-not-close-it",
        PANEL,
        '    document.addEventListener("keydown", onKeyDown);\n',
        "",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        # ORD-0090 residual 3, both faces: dropping the clause lets a refused tap back through, and
        # widening it greys the row on a journey that would have booked.  Each half is owned by a
        # different arm of the same node.
        "killD7-booking-row-ignores-the-journeys-state",
        PANEL,
        "        notPlanned ??\n",
        "",
        [(STAGE_SPEC, ["sim-booking-row-follows-the-journey-state"])],
    ),
    (
        "killD8-booking-row-refuses-even-a-planned-journey",
        PANEL,
        '    !notReady && journeyStatus !== null && journeyStatus !== "PLANNED"\n',
        "    !notReady && journeyStatus !== null\n",
        [(STAGE_SPEC, ["sim-booking-row-follows-the-journey-state"])],
    ),
    (
        "killD4-tapping-outside-does-not-close-it",
        PANEL,
        '    document.addEventListener("pointerdown", onPointerDown);\n',
        "",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killD5-ball-carries-a-sentence",
        PANEL,
        '        onClick={() => setOpen((value) => !value)}\n      >\n        <span\n',
        '        onClick={() => setOpen((value) => !value)}\n      >\n'
        '        <span className="cn-sim-ball-text">模拟舞台（场景时间由服务器给）</span>\n        <span\n',
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killD6-window-body-cannot-be-scoped",
        SHEET,
        "  min-height: 0;\n  overflow-y: auto;\n",
        "  min-height: 0;\n  overflow-y: hidden;\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killB1-running-action-has-no-signal",
        PANEL,
        '                aria-busy={running === row.id ? "true" : undefined}\n',
        "",
        [(STAGE_SPEC, ["sim-action-in-flight-is-perceivable"])],
    ),
    (
        "killB2-refusal-outlives-the-reading",
        PANEL,
        "      current?.transient && current.sceneStamp !== scene.updatedAt ? null : current,\n",
        "      current,\n",
        [(STAGE_SPEC, ["sim-refusal-does-not-outlive-the-reading"])],
    ),
    (
        "killB3-booking-row-stops-naming-its-target",
        PANEL,
        "        ? `建一个硬承诺：${bookTarget.title}`\n",
        '        ? "建一个硬承诺"\n',
        [(WALLET_SPEC, ["ord0087-booked-commitment-is-on-the-wallet-screen"])],
    ),
    (
        # A remembered local id left 接受/拒绝 pressable while GET /replans answers [] was the
        # silence ORD-0066 was opened against; the row's availability now comes from that list.
        "killB4-replan-rows-trust-local-memory-again",
        PANEL,
        '  const proposalId = openProposals.length ? String(openProposals[0].id) : null;\n',
        '  const proposalId = "ghost-proposal";\n',
        [(STAGE_SPEC, ["sim-replan-actions-follow-the-server-list"])],
    ),
    # (killC1 was here: it attacked `.cn-sim-entry:not([open]) .cn-sim { display: none }` and
    #  SURVIVED -- the browser already keeps a closed disclosure out of the layout, so that rule
    #  did nothing. It has been deleted from the CSS; the collapsed phone default (killC2) is the
    #  load-bearing part, and that one is killed.)
    (
        # The phone default *is* the no-overlap-band answer; opening on a phone must go red.
        "killC2-entry-opens-on-a-phone-anyway",
        PANEL,
        "  const phone = usePhoneLayout();\n",
        "  const phone = false;\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killC3-collapsed-line-keeps-the-jargon-only",
        PANEL,
        "          {` · ${declared}`}\n",
        "          {null}\n",
        [(STAGE_SPEC, ["sim-stage-actions-are-reachable-and-never-in-the-nav-band"])],
    ),
    (
        "killF1-sealed-evidence-reported-as-nothing",
        CLOCK,
        '  if (state === "FROZEN_WITHOUT_TTL")\n',
        '  if (state === "NEVER_MATCHES_FROZEN")\n',
        [(STAGE_SPEC, ["sim-evidence-state-says-what-is-sealed"])],
    ),
    (
        # ORD-0134 ②: the defect itself.  Putting the cooperative flag back is exactly what made a
        # finger do nothing, so the ownership gate has to go red the moment it returns.
        "killG1-cooperative-gestures-back-on",
        MAP,
        "      interactive: true,\n",
        "      interactive: true,\n      cooperativeGestures: true,\n",
        [(MAP_SPEC, ["ord0134-map-gesture-ownership"])],
    ),
    (
        # The caption band is painted over the canvas.  Give it pointer-events again and a finger that
        # lands on the words talks to a `<p>` instead of the map.
        "killG2-caption-wins-the-drag-again",
        STYLES,
        ".v8-map-tile-notice {\n  pointer-events: none;\n}",
        ".v8-map-tile-notice {\n  pointer-events: auto;\n}",
        [(MAP_SPEC, ["ord0134-map-gesture-ownership"])],
    ),
    (
        # Words on the panel must match the gesture that answers.  Restore the cooperative-era promise
        # and the gate has to notice the screen is lying.
        "killG3-hint-still-promises-two-finger-pan",
        MAP,
        '          ? "单指拖动地图 · 双指缩放 · 想翻这一页就拖地图以外的地方"\n',
        '          ? "双指拖动地图 · 单指无效 · 想翻这一页就拖地图以外的地方"\n',
        [(MAP_SPEC, ["ord0134-map-gesture-ownership"])],
    ),
    (
        # ORD-0146 ①, the defect as the order states it: the sentence stays, the entry disappears.
        "killH1-review-entry-hidden-behind-the-sentence",
        INBOX,
        "  const unreviewed = (pending ?? []).filter((item) => item.status !== \"CONFIRMED\");\n",
        "  const unreviewed = ([] as Draft[]).filter((item) => item.status !== \"CONFIRMED\");\n",
        [(INBOX_SPEC, ["ord0146-review-entry-is-on-the-page-that-asked-for-review"])],
    ),
    (
        # "前端不得自己决定哪条能过": stamp the verdict locally and never ask the server again.
        "killH2-pass-verdict-minted-in-the-browser",
        INBOX,
        "    const fresh = (await readInbox()).find((item) => item.id === draftId) ?? null;\n",
        "    const fresh = { ...draft, status: \"CONFIRMED\", confirmed_at: new Date().toISOString() };\n",
        [(INBOX_SPEC, ["ord0146-passing-a-review-is-the-servers-answer"])],
    ),
    (
        # A badge the screen asserts instead of earning: say 受保护 whether or not there is a commitment.
        "killH3-protected-badge-earned-by-nobody",
        EXPERIENCE,
        "                {item.commitment_id\n",
        "                {true\n",
        [(INBOX_SPEC, ["ord0146-a-protected-badge-needs-the-servers-commitment"])],
    ),
    # NOTE: the three ORD-0126 mutants that stood here (killJ1 refusal-drops-the-id, killJ2
    # journey-gone-branch-disabled, killJ3 health-probe-always-answers) were retired by the R14
    # rewrite, not dropped for convenience: their anchor lines and their target nodes
    # (`ord0126-*`) no longer exist, so running them would have produced NOT_MEASURED rather than a
    # verdict.  Their subject matter is carried by killJ4 and killL1-L4 below, which are applied to
    # the gates that are green on the unmutated tree.
    (
        # ORD-0169 ②: name the dead trip but keep the id -- the next reload walks into the same 404.
        "killJ4-stale-id-never-cleared",
        EXPERIENCE,
        "              const cleared = clearJourneyReferences();\n",
        "              const cleared: string[] = [];\n",
        [(EXIT_SPEC, ["ord0169-a-stale-journey-404-is-never-called-a-network-failure"])],
    ),
    (
        # R14 §7 bullet 1: stale-journey 404 mapped to OFFLINE.  This is the defect as measured on the
        # production bundle, and it is what the gate exists to catch.
        "killL1-stale-404-becomes-offline",
        ATTRIBUTION,
        "      return make(\n        \"JOURNEY_NOT_FOUND\",\n",
        "      return make(\n        \"NETWORK_UNAVAILABLE\",\n",
        [(EXIT_SPEC, ["ord0169-a-stale-journey-404-is-never-called-a-network-failure"])],
    ),
    (
        # R14 §7 bullet 2: true transport failure mapped to JOURNEY_NOT_FOUND -- the reverse direction,
        # which is how "fixing" the first one by widening "not found" would break the product.
        # SURVIVED, and the survival is informative: on this path the shell asks the health probe, the
        # probe fails, and `classifyHealthProbe(false)` overwrites the attribution -- so the classifier's
        # transport branch is not what decides the verdict.  killL2b mutates the branch that is.
        "killL2-transport-failure-becomes-journey-not-found",
        ATTRIBUTION,
        "    return make(\"NETWORK_UNAVAILABLE\", \"TRANSPORT\", null, \"TRANSPORT\", true, \"read-only-cached\", \"failure.networkUnavailable\");\n",
        "    return make(\"JOURNEY_NOT_FOUND\", \"TRANSPORT\", null, \"TRANSPORT\", true, \"choose-journey\", \"failure.journeyNotFound\");\n",
        [(EXIT_SPEC, ["ord0169-a-real-transport-failure-still-says-offline"])],
    ),
    (
        # The branch that really decides: a failed health probe is the evidence that says the network is
        # unavailable.  Turn it into "the journey is gone" and the reverse defect is in place.
        "killL2b-failed-probe-becomes-journey-not-found",
        ATTRIBUTION,
        "    : make(\"NETWORK_UNAVAILABLE\", \"HEALTH_PROBE\", null, \"TRANSPORT\", true, \"read-only-cached\", \"failure.networkUnavailable\");\n",
        "    : make(\"JOURNEY_NOT_FOUND\", \"HEALTH_PROBE\", null, \"TRANSPORT\", true, \"choose-journey\", \"failure.journeyNotFound\");\n",
        [(EXIT_SPEC, ["ord0169-a-real-transport-failure-still-says-offline"])],
    ),
    (
        # R14 §7 bullet 6 / R14-P: a broad catch choosing the message instead of the structured reason.
        # The evidence still arrives (the status is right there), so this is purely the UI inventing a
        # cause -- and it is the shape the old code had.
        "killL3-ui-catch-invents-the-cause",
        EXPERIENCE,
        "            let attribution = classifyReadFailure(error);\n",
        "            let attribution = classifyReadFailure(new TypeError(\"gate-mutant: broad catch\"));\n",
        [(EXIT_SPEC, ["ord0169-a-server-5xx-is-not-offline"])],
    ),
    (
        # R14 §8: telemetry must record what the classifier decided, not what the fallback screen
        # happened to be showing.  Reporting every failure as network_unavailable is the exact line
        # the policy forbids.
        "killL4-telemetry-borrows-the-fallback-cause",
        ATTRIBUTION,
        "    reason,\n    evidence_kind,\n    http_status,\n    source_layer,\n    retryable,\n    recovery_action,\n    message_key,\n    telemetry: [\n      `attribution_reason=${reason}`,\n",
        "    reason,\n    evidence_kind,\n    http_status,\n    source_layer,\n    retryable,\n    recovery_action,\n    message_key,\n    telemetry: [\n      `attribution_reason=NETWORK_UNAVAILABLE`,\n",
        [(EXIT_SPEC, ["ord0169-a-stale-journey-404-is-never-called-a-network-failure"])],
    ),
    (
        # ORD-0135 ②: the measured pre-fix line -- the confirmation step printed the stored key.
        "killK1-confirmation-prints-the-raw-pace-key",
        WIZARD,
        "                {optionLabels(draft.pace ? [draft.pace] : [], PACE_OPTIONS, zh) || \"—\"}\n",
        "                {draft.pace || \"—\"}\n",
        [(WIZ_SPEC, ["ord0135-the-confirmation-step-prints-no-internal-key"])],
    ),
    (
        # ③: name the missing fields but offer no route to them.
        "killK2-missing-fields-named-but-unreachable",
        WIZARD,
        "            {missingNow.map((field) => (\n",
        "            {([] as MissingField[]).map((field) => (\n",
        [(WIZ_SPEC, ["ord0135-a-missing-field-is-a-route-not-only-a-diagnosis"])],
    ),
    (
        # ①: the persistence this order asked for, switched off -- the refresh lands back on step 1.
        "killK3-draft-never-persisted",
        WIZARD,
        "    localStorage.setItem(TRIAL_DRAFT_KEY, JSON.stringify({ step, draft }));\n",
        "    void TRIAL_DRAFT_KEY; void step; void draft;\n",
        [(WIZ_SPEC, ["ord0135-the-wizard-survives-a-refresh-on-the-step-you-were-on"])],
    ),
    (
        # ORD-0178 ④(丙): the rowcount check this order asked for, removed -- a copy is claimed from
        # the request succeeding rather than from the row being read back.
        # SURVIVED, and the survival is informative: the offline branch re-reads the row for itself
        # (`readOfflineJourney` below), so this save-path check is redundant for the claim the screen
        # makes.  killM1a mutates the read-back that actually decides it.
        "killM1-copy-claimed-without-reading-it-back",
        OFFLINE_LIB,
        "    const readBack = await database.journeys.get(snapshot.journey_id);\n    return Boolean(readBack && readBack.journey_id === snapshot.journey_id);\n",
        "    return true;\n",
        [(OFFLINE_SPEC, ["ord0178-the-saved-copy-claim-follows-the-rowcount"])],
    ),
    (
        # The load-bearing check: whether the device holds a readable row is what may turn the claim
        # and the read-only action on.  Claiming it without asking is the defect the order names.
        "killM1a-claim-without-asking-the-device",
        EXPERIENCE,
        "              setCachedCopySaved(Boolean(saved));\n",
        "              setCachedCopySaved(true);\n",
        [(OFFLINE_SPEC, ["ord0178-the-saved-copy-claim-follows-the-rowcount"])],
    ),
    (
        # The other half: the screen treats the snapshot object as evidence that a copy exists,
        # which is exactly the assumption ORD-0178 asks to replace with a measurement.
        "killM2-screen-trusts-the-snapshot-object",
        EXPERIENCE,
        "      hasCachedCopy: cachedCopySaved,\n",
        "      hasCachedCopy: true,\n",
        [(OFFLINE_SPEC, ["ord0178-the-saved-copy-claim-follows-the-rowcount"])],
    ),
    (
        # ORD-0180 1: a fresh key per tap turns a replay into a second acceptance.  The gate asserts
        # one distinct key across two taps, so minting per call has to go red.
        "killN1-fresh-idempotency-key-per-tap",
        PANEL,
        "    const held = idempotencyKeys.current.get(scope);\n    if (held) return held;\n",
        "    const held = undefined;\n    if (held) return held;\n",
        [(REPLAN_SPEC, ["ord0180-the-bridge-is-marked-and-presence-is-not-permission"])],
    ),
    (
        # ORD-0183 1: the bridge loses its marker while the filter stays -- the shim then reads as a
        # contract to whoever finds it next, which is the exact failure the marker exists to prevent.
        "killN2-bridge-marker-removed",
        PANEL,
        "  /* TEMPORARY-CLIENT-FILTER-ORD-0180 -- transitional bridge, not a contract.\n",
        "  /* a client-side narrowing of the list.\n",
        [(REPLAN_SPEC, ["ord0180-the-bridge-is-marked-and-presence-is-not-permission"])],
    ),
    (
        # ORD-0135 3, the half-fix the commander named: the review step keeps printing 未填写 · 必填
        # while the button loses its blocked state -- text corrected, control unchanged.
        # First attempt appended `aria-disabled={undefined}` after the real attribute and SURVIVED:
        # a later undefined prop does not override an earlier one in JSX, so the mutant removed
        # nothing.  This one replaces the attribute itself.
        "killP1-create-button-loses-its-blocked-state",
        WIZARD,
        '            aria-disabled={blockedNow ? "true" : undefined}\n            aria-describedby={blockedNow ? "trial-required-hint" : undefined}\n            onClick={() => {\n              if (blockedNow) {\n                speak(missingLine);\n                return;\n              }\n              void submit();\n',
        "            onClick={() => {\n              void submit();\n",
        [(WIZ_SPEC, ["ord0135-the-review-step-button-carries-what-the-screen-already-says"])],
    ),
    (
        # The step-3 missing list itself: drop it and the screen still says 未填写 while nothing
        # reaches the button, which is the measured pre-fix state.
        "killP2-review-step-forgets-its-missing-list",
        WIZARD,
        "  const missingStep3 = missingStep1;\n",
        "  const missingStep3: MissingField[] = [];\n",
        [(WIZ_SPEC, ["ord0135-the-review-step-button-carries-what-the-screen-already-says"])],
    ),
    (
        # ORD-0193 / R14-P reverse face: a server-known structural state dressed as connectivity.
        # This is the exact defect the order forbids, so the gate must go red on it.
        "killQ1-structural-verdict-blamed-on-the-network",
        PREP,
        "            ? `服务器说「${capability.pending_destination_label ?? capability.query}」没有任何可追溯来源能把它定成一个目的地。这不是网络问题——服务器刚才答得出来。换个写法，或另选一个地方。`\n",
        "            ? `网络不可用，暂时没法确认这个目的地。请检查网络后重试。`\n",
        [(PREP_SPEC, ["ord0193-a-structural-verdict-is-not-called-a-network-failure"])],
    ),
    (
        # A settled state with nothing to press: the order's "禁止静默关闭与空操作".  Removing the
        # retry action from a retryable failure leaves the traveller on a dead screen.
        "killQ2-a-retryable-failure-offers-no-action",
        PREP,
        "            {job.terminal && job.retryable && (\n",
        "            {false && (\n",
        [(PREP_SPEC, ["ord0193-a-retryable-runtime-failure-offers-a-retry-and-a-structural-one-does-not"])],
    ),
    (
        # ORD-0203: the fourth cell's action stops being reachable -- the branch that renders the
        # retry is renamed so nothing matches, which is how a control silently disappears.
        "killR1-retry-later-is-not-rendered",
        PREP,
        '            ) : action === "RETRY_LATER" ? (\n',
        '            ) : action === "RETRY_LATER_DISABLED_FOR_THIS_MUTANT" ? (\n',
        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],
    ),
    (
        # ORD-0203: the fourth cell rendered with the conflation R11 froze -- plannability written
        # as coverage completeness.  This is the exact sentence the order forbids.
        "killR2-fourth-cell-claims-the-city-needs-data",
        PREP,
        "            ? `服务器说这一问没有拿到答复（${reasonCode}）——是它去问的那一头没答话，不是「这个地方不能规划」，也不是「这城市还要灌数据」。这两句服务器都没说。可以稍后重试。`\n",
        "            ? `这城市还要灌数据，服务器暂时没有它的资料。`\n",
        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],
    ),
    (
        # ORD-0208 2: the selected state goes back to colour alone.
        "killS1-chips-lose-their-spoken-state",
        WIZARD,
        "                  aria-pressed={draft.pace === option.key}\n",
        "                  aria-pressed={undefined}\n",
        [(TONGUE_SPEC, ["ord0208-chips-carry-their-state-for-ears-not-only-eyes"])],
    ),
    (
        # ORD-0208 1: the enum returns to the prose -- the measured pre-fix wording.
        "killS2-clock-sentence-prints-the-enum-again",
        EXPERIENCE,
        "                    ? \"。服务器没有给出这一分钟的执行游标，这一屏的时间按行程的时间窗来读\"\n",
        "                    ? `，游标状态 ${cursorStatus}`\n",
        [(TONGUE_SPEC, ["ord0208-the-clock-sentence-speaks-human"])],
    ),
    (
        # ORD-0208 3: the inferred default passes for a typed answer again.
        "killS3-defaults-pass-as-typed",
        WIZARD,
        "                {!touched.has(\"partySize\") && <DefaultMark zh={zh} />}\n",
        "",
        [(TONGUE_SPEC, ["ord0208-inferred-defaults-are-marked-on-the-confirmation-step"])],
    ),
    (
        # ORD-0208 4: the day card prints the raw enums again.
        "killS4-day-card-prints-raw-enums",
        EXPERIENCE,
        "                    {anchorLabel(day.anchor, locale.startsWith(\"zh\"))} \u00b7{\" \"}\n                    {modeLabel(day.mode, locale.startsWith(\"zh\"))}\n                  </small>\n",
        "                    {day.anchor} anchor · {day.mode}\n",
        [(TONGUE_SPEC, ["ord0208-the-day-card-speaks-the-language-the-screen-uses"])],
    ),
    (
        # ORD-0209: the exact defect the arbitration ruled on -- the entry creates a traveller
        # and a journey again.  The seed of the old body is restored in front of the addressing
        # branch, so the network-count gate must go red on it.
        "killT1-demo-entry-creates-again",
        EXPERIENCE,
        "      const sealedId = scene.journey_id ?? null;\n",
        "      await v8Request<{ id: string }>(\"/api/v1/travelers\", { method: \"POST\", body: JSON.stringify({ display_name: \"City traveler\" }) });\n"
        "      await v8Request<{ id: string }>(\"/api/v1/journeys\", { method: \"POST\", body: JSON.stringify({ title: \"Tianjin demo\" }) });\n"
        "      const sealedId = scene.journey_id ?? null;\n",
        [(DEMO_SPEC, ["ord0209-the-demo-entry-addresses-the-sealed-journey"])],
    ),
    (
        # ORD-0212's own warned trap: following "remove the tier" so literally that the caveat
        # is stripped while the derived number stays -- a vague sentence replaced by a
        # fake-precision figure.  The invariant tripwire must catch exactly that.
        "killU1-tight-advisory-keeps-number-drops-caveat",
        EXPERIENCE,
        "              <span>{advisory.hint}</span>\n              <div className=\"today-advisory-actions\">\n",
        "              <div className=\"today-advisory-actions\">\n",
        [(TIERS_SPEC, ["ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red"])],
    ),
    (
        # ORD-0221 ②: the other half of the pair.  A caveat with no figure behind it is the same
        # claim with nothing to check it against, so dropping the number must go red too -- this is
        # the direction killU1 does not cover.
        "killU2-tight-advisory-keeps-caveat-drops-number",
        EXPERIENCE,
        "              <strong>{advisory.text}</strong>\n              <span>{advisory.hint}</span>\n",
        "              <span>{advisory.hint}</span>\n",
        [(TIERS_SPEC, ["ord0212-the-hub-keeps-only-the-tight-verdict-and-it-keeps-its-caveat-and-action"])],
    ),
    (
        # ORD-0216 3: attempted mutant, recorded as a DOCUMENTED SURVIVOR.  Restoring the
        # anchors-only review list did not reproduce HJ-P1's reading: their flow left the visible
        # hint on step 3 through a route this node's path does not reach (the node advances only
        # after the field is filled, so the recomputed list is empty either way).  The hint's
        # recomputation-from-current-values itself is what the node guards; the survivor says the
        # old spelling is redundant on this path, not that the fix is unnecessary.
        "killV1-stale-budget-hint-follows-onto-step-3",
        WIZARD,
        "  const missingStep3 = [\n    ...missingStep1,\n    ...missingStep2,\n  ];\n",
        "  const missingStep3 = missingStep1;\n",
        [
            (WIZ2_SPEC, ["ord0216-a-fixed-field-leaves-the-hint-on-the-next-step"]),
            # ORD-0221 ②: the same mutant against the per-surface reading.  Whatever it does to the
            # visible hint is the answer to "why did the first node not catch this".
            (SURFACE_SPEC, ["ord0221-4-step3-visible-hint-and-live-region-read-apart"]),
        ],
    ),
    # ORD-0216 ④: the entry may not name a city, because /demo/scene decides which sealed journey it
    # hands over.  These two mutants put HJ-P1's wording back -- one per language arm of the gate.
    (
        "killW1-entry-copy-names-a-city-zh",
        I18N,
        '  "trial.tianjinDemo": "使用封存的演示行程",\n',
        '  "trial.tianjinDemo": "使用封存的天津演示",\n',
        [(COPY_SPEC, ["ord0216d-zh-the-wizard-never-says-a-city-name"])],
    ),
    (
        "killW2-entry-copy-names-a-city-en",
        I18N,
        '  "trial.tianjinDemo": "Use the sealed demo trip",\n',
        '  "trial.tianjinDemo": "Use the sealed Tianjin demo",\n',
        [(COPY_SPEC, ["ord0216d-en-the-wizard-never-says-a-city-name"])],
    ),
]

sha256 = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
only = sys.argv[1:] or [case[0] for case in CASES]
port = int(os.environ.get("KILL_PORT", "4531"))
# ORD-0134 ② is a phone-viewport, production-build criterion, so its mutants cannot be judged on the
# dev chain this harness defaults to.  Passing `--config` in per invocation keeps every earlier
# batch's verdicts reproducible.
extra = os.environ.get("KILL_EXTRA", "").strip()

results: dict[str, str] = {}
for name, rel, old, new, targets in CASES:
    if name not in only:
        continue
    path = f"{FRONTEND}/{rel}"
    text = open(path, encoding="utf-8", newline="").read()
    before = sha256(path)
    hits = text.count(old)
    mutated = text.replace(old, new, 1)
    open(path, "w", encoding="utf-8", newline="").write(mutated)
    on_disk = open(path, encoding="utf-8", newline="").read()
    applied = hits == 1 and on_disk == mutated
    # ORD-0221 ②: the receipt has to say how many bytes the mutant actually moved, measured on the
    # file, not inferred from the strings in this list.
    delta = len(on_disk.encode("utf-8")) - len(text.encode("utf-8"))
    print(
        f"\n{name}: {rel} anchor hits={hits} on_disk={applied} "
        f"anchor_bytes={len(old.encode('utf-8'))} bytes_changed={delta}",
        flush=True,
    )
    if not applied:
        print("  MUTANT NOT ON DISK -- skipped; the suite would be judging an untouched build")
        open(path, "w", encoding="utf-8", newline="").write(text)
        results[name] = "HARNESS_INVALID"
        continue

    # A neighbour's listener makes every verdict below meaningless: authoritative mode refuses to
    # adopt it, and the run dies as 'port already used' -- which is not evidence about any node.
    def port_free(number: int) -> bool:
        probe = socket.socket()
        probe.settimeout(0.5)
        try:
            probe.bind(("127.0.0.1", number))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    if not (port_free(port) and port_free(int(port) + 4000)):
        print("  ABORTED: this run's ports are already listening; the verdict would be noise")
        results[name] = "HARNESS_INVALID"
        open(path, "w", encoding="utf-8", newline="").write(text)
        continue

    verdicts = []
    for spec, node_ids in targets:
        run_id = f"{name.replace('-', '_')[:7]}{int(time.time()) % 100000:05d}"
        env = dict(os.environ)
        env.update(
            {
                "CITYNEXUS_E2E_AUTHORITATIVE": "1",
                "CITYNEXUS_E2E_RUN_ID": run_id,
                "CITYNEXUS_E2E_PORT": str(port),
                "CITYNEXUS_BACKEND_PORT": str(port + 4000),
                "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
                "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
                "CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
            }
        )
        env.pop("DEEPSEEK_API_KEY", None)
        env.pop("CITYNEXUS_AI_API_KEY", None)
        pattern = "|".join(node_ids)
        proc = subprocess.run(
            f'npx playwright test {spec} --reporter=list --grep "{pattern}"',
            cwd=FRONTEND,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        out = proc.stdout + proc.stderr
        quiet = [line for line in out.splitlines() if not line.startswith("[WebServer]")]
        with open(f"{LOGDIR}/{name}.{run_id}.log", "w", encoding="utf-8", newline="") as fh:
            fh.write(out + "\n")
        if "was not able to start" in out or "refuses to start" in out:
            print(f"  INVALID RUN against {spec}: a server never started", flush=True)
            verdicts.append("HARNESS_INVALID")
            continue
        red = [line for line in quiet if line.lstrip().startswith("x ") and any(n in line for n in node_ids)]
        green = [line for line in quiet if line.lstrip().startswith("ok ") and any(n in line for n in node_ids)]
        for line in quiet:
            if "Error:" in line and "Context" not in line:
                print(f"  red message: {line.strip()[:190]}", flush=True)
                break
        verdict = "KILLED" if red else ("SURVIVED" if green else "NOT_MEASURED")
        print(f"  {spec} {node_ids} -> {verdict} (rc={proc.returncode})", flush=True)
        verdicts.append(verdict)

    results[name] = "KILLED" if verdicts and all(v == "KILLED" for v in verdicts) else "/".join(verdicts)

    open(path, "w", encoding="utf-8", newline="").write(text)
    restored = sha256(path)
    print(f"  restored {'OK' if restored == before else 'MISMATCH -- STOP'}", flush=True)
    if restored != before:
        sys.exit(2)

print("\n== summary ==", flush=True)
for key, value in results.items():
    print(f"  {key}: {value}", flush=True)
print(f"total {len(results)}  killed {sum(1 for v in results.values() if v == 'KILLED')}", flush=True)
