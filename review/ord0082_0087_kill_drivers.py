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
SHEET = "src/features/simulation/SimulationPanel.css"
CLOCK = "src/lib/sceneClock.ts"
STAGE_SPEC = "e2e/qoder-today-follows-the-stage.spec.ts"
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
]

sha256 = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
only = sys.argv[1:] or [case[0] for case in CASES]
port = int(os.environ.get("KILL_PORT", "4531"))

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
    print(f"\n{name}: {rel} anchor hits={hits} on_disk={applied}", flush=True)
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
