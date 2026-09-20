import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale } from "../../i18n/LocaleContext";
import { cityNexusApi } from "../../api/citynexus";
import { formatMinorMoney } from "../../lib/money";
import { useAuthoritativeTwin } from "../../api/v12Authoritative";
import {
  basisWord,
  evidenceWord,
  invalidateScene,
  sceneInstant,
  useDemoScene,
} from "../../lib/sceneClock";
import {
  describeFailure,
  NEXT_STEP,
  postSimulatedEvent,
  resetStage,
  transitionStage,
} from "./simulationAdapter";
import "./SimulationPanel.css";

/**
 * ORD-0059 (b) -- the visible Simulation entry.
 *
 * What this screen is allowed to know comes from two server reads and nothing else: the stage
 * (`GET /demo/scene`) and the journey's twin.  It owns no scenario state, no clock, and no
 * lifecycle of its own -- every row below is one existing product endpoint, and the line the
 * traveller gets afterwards is what the server answered, not a promise this screen made.
 *
 * So the disabled states are the design, not decoration.  A stage where "推进一个活动" is greyed
 * out because the seeded journey has no cursor yet must say why in the traveller's language and
 * stay reachable (same 甲 discipline as the wizard's blocked Next: aria-disabled, focusable, the
 * reason attached); a grey box that explains nothing is how a person ends up clicking around for
 * ten minutes against a refusal they were never told about.
 */

type ActionId =
  | "reset"
  | "advance"
  | "event"
  | "replan"
  | "accept"
  | "reject"
  | "book"
  | "degrade"
  | "restore";

type Row = {
  id: ActionId;
  zh: string;
  en: string;
  /** Why this row cannot run right now, or null when it can. */
  blocked: null | { zh: string; en: string };
  run: () => Promise<{ zh: string; en: string }>;
};

const newKey = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `sim-${Math.random().toString(36).slice(2, 12)}`;

const shortId = (value: string | null) => (value ? value.slice(0, 8) : "—");

export function SimulationPanel({
  viewingJourneyId = null,
}: {
  /** The journey the shell is showing, so the panel can say when the stage is a different one. */
  viewingJourneyId?: string | null;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const client = useQueryClient();
  const scene = useDemoScene();
  const journeyId = scene.scene?.journeyId ?? null;
  const twin = useAuthoritativeTwin(journeyId);
  /* The transition graph lives on the server, so the row has to ask which state the current
     activity is in before it can name a step.  `plan_version_id` comes from the scene read, and
     the plan itself from the ordinary product endpoint -- no second source of truth. */
  const planVersionId = scene.scene?.planVersionId ?? null;
  const plan = useQuery({
    queryKey: ["sim-stage-plan", planVersionId],
    enabled: Boolean(planVersionId),
    queryFn: () => cityNexusApi.getPlan(planVersionId as string),
  });
  const [running, setRunning] = useState<ActionId | null>(null);
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<{ ok: boolean; zh: string; en: string } | null>(null);

  const refreshAll = () => {
    invalidateScene(client);
    void client.invalidateQueries({ queryKey: ["v12-authoritative-twin", journeyId] });
    void client.invalidateQueries({ queryKey: ["sim-stage-plan", planVersionId] });
  };

  const notReady =
    scene.phase !== "ready"
      ? {
          zh: scene.phase === "loading" ? "还在读服务器的场景状态。" : "场景状态没读到，先看下面的原因。",
          en:
            scene.phase === "loading"
              ? "The stage state is still being read from the server."
              : "The stage state could not be read; see the reason below.",
        }
      : null;
  const noJourney =
    !notReady && !journeyId
      ? {
          zh: "台上没有场景：服务器回的是 NO_SCENARIO。先在产品里建一趟行程，或按下面的重置播一个演示场景。",
          en: "There is no scenario on stage (the server answered NO_SCENARIO). Create a trip in the product, or re-seed one below.",
        }
      : null;
  const cursorless = twin.isPending
    ? { zh: "服务器游标还在读，读完才知道有没有可推进的活动。", en: "The server cursor is still being read." }
    : !twin.data?.current_activity_id
      ? {
          zh: `服务器没给进行中的活动（游标为空，行程状态 ${scene.scene?.journeyStatus ?? "未知"}）。这趟还没有可推进的一步，先让行程进入执行状态。`,
          en: `The server reports no activity in progress (empty cursor, journey status ${scene.scene?.journeyStatus ?? "unknown"}). This trip has no step to advance yet.`,
        }
      : null;
  const noPlan =
    !notReady && !journeyId
      ? noJourney
      : !twin.data?.active_plan_version_id
        ? {
            zh: "这趟还没有 ACTIVE 计划（服务器没返回计划版本），重规划需要它。",
            en: "No ACTIVE plan on this journey (the server returned no plan version), and a replan needs one.",
          }
        : null;

  /* The step this row may offer is whichever one the server's state graph allows from the
     current activity's status -- not the one this screen would like.  A panel that hard-codes
     "complete" gets `INVALID_ACTIVITY_TRANSITION:NOT_STARTED->COMPLETED` on every frozen plan and
     then has to explain a refusal it invented itself. */
  const currentActivity =
    plan.data?.activities.find((item) => item.id === twin.data?.current_activity_id) ?? null;
  const nextStep = currentActivity ? NEXT_STEP[currentActivity.status] ?? null : null;
  const stepBlocked =
    plan.isPending && Boolean(twin.data?.current_activity_id)
      ? { zh: "还在读这份计划里当前活动的状态。", en: "The current activity's status is still being read." }
      : !currentActivity
        ? {
            zh: "服务器给的当前活动不在这份计划的清单里，所以没有可执行的下一步。",
            en: "The cursor points at an activity that is not on this plan, so there is no next step to offer.",
          }
        : !nextStep
          ? {
              zh: `这项活动在服务器已经是 ${currentActivity.status}，它的状态图里没有下一步。`,
              en: `The server holds this activity as ${currentActivity.status}; its state graph has no next step.`,
            }
          : null;

  const rows: Row[] = [
    {
      id: "reset",
      zh: "重置到场景起点",
      en: "Re-seed the scenario",
      blocked:
        scene.phase === "ready" && !scene.scene?.demoMode
          ? {
              zh: "服务器说这台部署不是模拟舞台（demo_mode=false），而重置会删演示数据，所以这里不给按。",
              en: "The server says this deployment is not a simulation stage (demo_mode=false), and re-seeding deletes demo rows, so this is refused.",
            }
          : null,
      run: async () => {
        const result = await resetStage();
        setLastEventId(null);
        setProposalId(null);
        const advance = result.advance;
        const refused = advance?.steps.find((step) => step.refused !== undefined) ?? null;
        /* ORD-0078 (a): the shell decides which journey to show once, at boot, from
           `localStorage["citynexus.v8.journey_id"]` (V8Experience.tsx:493), and `demo/reset`
           deletes the rows the old id pointed at without writing the new one.  So a teacher who
           presses 重置 is dropped back on the three-step wizard holding a journey that does exist
           on the server.  Handing over the id the server just returned is not an invented trip --
           it is the trip `demo/reset` answered with. */
        const reachedActive = advance?.journeyStatus === "ACTIVE";
        /* Written whenever the server really created a journey.  Requiring ACTIVE here looked
           safer and was a false gate: with a seeded ACTIVE journey already in the database the
           single-ACTIVE-plan rule refuses the advance, so the id was never handed over and the
           teacher stayed in the wizard -- the exact defect ORD-0078 (a) names.  My own node
           `sim-reset-hands-the-stage-to-today` caught this by going red, not by being relaxed.
           Whether the stage is executable is said in the outcome line, not used to hide the id. */
        if (result.status === "reset" && result.journey_id) {
          localStorage.setItem("citynexus.v8.journey_id", result.journey_id);
          /* A moment to read the line, then the shell re-boots onto the journey it now names; the
             longer pause on a refused advance is so the refusal itself is readable first. */
          window.setTimeout(() => window.location.reload(), reachedActive ? 1_200 : 2_400);
        }
        if (!advance) {
          return {
            zh: `服务器回的是 ${result.status}，但没有报上推进结果，所以这一步到底到没到可执行状态，我们不说。`,
            en: `The server answered ${result.status} with no advance report, so whether the stage is executable is not claimed here.`,
          };
        }
        if (refused) {
          return {
            zh: `服务器重新播了场景（行程 ${shortId(result.journey_id)}），但推进到可执行状态被挡在「${refused.step}」（${refused.refused}）：这趟现在的状态是 ${advance.journeyStatus ?? "未知"}。`,
            en: `The server re-seeded (journey ${shortId(result.journey_id)}) but the advance was refused at "${refused.step}" (${refused.refused}): the trip is now ${advance.journeyStatus ?? "unknown"}.`,
          };
        }
        return {
          zh: `服务器重新播了场景并走完真实流水线：行程 ${shortId(result.journey_id)} · 状态 ${advance.journeyStatus ?? "未知"} · 计划 ${shortId(advance.selectedPlanVersionId)} · 用时 ${advance.totalMs ?? 0}ms。`,
          en: `The server re-seeded and ran the real pipeline: journey ${shortId(result.journey_id)} · status ${advance.journeyStatus ?? "unknown"} · plan ${shortId(advance.selectedPlanVersionId)} · ${advance.totalMs ?? 0}ms.`,
        };
      },
    },
    {
      id: "advance",
      zh: nextStep ? `推进当前活动：${nextStep.zh}` : "推进当前活动",
      en: nextStep ? `Advance the current activity: ${nextStep.en}` : "Advance the current activity",
      blocked: notReady ?? noJourney ?? cursorless ?? stepBlocked,
      run: async () => {
        if (!nextStep || !currentActivity) throw new Error("NO_NEXT_STEP_OFFERED");
        const after = await transitionStage(journeyId as string, currentActivity.id, nextStep.step);
        setLastEventId(null);
        return {
          zh: `服务器接了「${nextStep.zh}」这一转移（原来这项活动是 ${currentActivity.status}）：游标 ${shortId(after.current_activity_id)}，投影 ${after.projection_status}。新状态由它说，不由我说。`,
          en: `The server took the "${nextStep.en}" transition (the activity was ${currentActivity.status}): cursor ${shortId(after.current_activity_id)}, projection ${after.projection_status}. Its state, not my guess.`,
        };
      },
    },
    {
      id: "event",
      zh: "触发一次中断",
      en: "Raise a disruption",
      blocked: notReady ?? noJourney,
      run: async () => {
        const created = await postSimulatedEvent(journeyId as string, {
          eventType: "TRAFFIC_DELAY",
          severity: "MAJOR",
          activityId: twin.data?.current_activity_id ?? null,
        });
        setLastEventId(created.id);
        setProposalId(null);
        return {
          zh: `服务器记下一次中断 ${shortId(created.id)}，发生时间按它自己的 ${sceneInstant(created.occurred_at)}；来源由服务器判定为模拟。`,
          en: `The server recorded disruption ${shortId(created.id)} at its own ${sceneInstant(created.occurred_at)}; provenance is assigned server-side as simulated.`,
        };
      },
    },
    {
      id: "replan",
      zh: "请求重规划",
      en: "Ask for a replan",
      blocked: notReady ?? noJourney ?? noPlan ?? (lastEventId ? null : {
        zh: "重规划要由一个中断触发（服务器要求 trigger_event_id）。先按上面「触发一次中断」。",
        en: "A replan needs a triggering event (the server requires trigger_event_id). Raise a disruption above first.",
      }),
      run: async () => {
        const proposal = await cityNexusApi.generateReplans(journeyId as string, lastEventId as string, 3, newKey());
        setProposalId(proposal.id);
        return {
          zh: `服务器给出方案 ${shortId(proposal.id)}（状态 ${proposal.status}）。接受才会换计划。`,
          en: `The server produced proposal ${shortId(proposal.id)} (status ${proposal.status}). Accepting is what changes the plan.`,
        };
      },
    },
    {
      id: "accept",
      zh: "接受方案",
      en: "Accept the proposal",
      blocked: notReady ?? noJourney ?? (proposalId ? null : {
        zh: "还没有待定的方案：先「请求重规划」拿到一个，服务器才有东西可接受。",
        en: "There is no proposal yet: request a replan so the server has something to accept.",
      }),
      run: async () => {
        const accepted = await cityNexusApi.acceptReplan(proposalId as string, newKey());
        setProposalId(null);
        return {
          zh: `服务器已接受 ${shortId(accepted.proposal.id)}，新 ACTIVE 计划 ${shortId(accepted.twin.active_plan_version_id ?? null)}。`,
          en: `The server accepted ${shortId(accepted.proposal.id)}; new ACTIVE plan ${shortId(accepted.twin.active_plan_version_id ?? null)}.`,
        };
      },
    },
    {
      id: "reject",
      zh: "拒绝方案",
      en: "Reject the proposal",
      blocked: notReady ?? noJourney ?? (proposalId ? null : {
        zh: "同上：没有待定方案可拒绝。",
        en: "As above: there is no proposal to reject yet.",
      }),
      run: async () => {
        const rejected = await cityNexusApi.rejectReplan(proposalId as string);
        setProposalId(null);
        return {
          zh: `服务器记下了拒绝 ${shortId(rejected.id)}，原计划不变。`,
          en: `The server recorded the rejection of ${shortId(rejected.id)}; the plan stands.`,
        };
      },
    },
    {
      id: "book",
      zh: "建一个硬承诺",
      en: "Book a commitment",
      blocked: notReady ?? noJourney ?? cursorless,
      run: async () => {
        const booking = await cityNexusApi.createBooking(journeyId as string, twin.data?.current_activity_id as string);
        return {
          zh: `服务器建了承诺 ${shortId(booking.id)}（${booking.status} · ${formatMinorMoney(booking.amount.amount_minor, booking.amount.currency, locale)}）。`,
          en: `The server created commitment ${shortId(booking.id)} (${booking.status} · ${formatMinorMoney(booking.amount.amount_minor, booking.amount.currency, locale)}).`,
        };
      },
    },
    {
      id: "degrade",
      zh: "提供方降级",
      en: "Degrade the provider",
      blocked: notReady ?? noJourney,
      run: async () => {
        const fixture = await cityNexusApi.setGuardianProviderFixture(journeyId as string, "OUTAGE");
        return {
          zh: `服务器把信号夹具设为 OUTAGE${fixture?.state ? `（现值 ${fixture.state}）` : ""}。这只影响这台演示舞台，不是真实世界变了。`,
          en: `The server set the signal fixture to OUTAGE${fixture?.state ? ` (now ${fixture.state})` : ""}. This moves the stage only, not the real world.`,
        };
      },
    },
    {
      id: "restore",
      zh: "提供方恢复",
      en: "Restore the provider",
      blocked: notReady ?? noJourney,
      run: async () => {
        const fixture = await cityNexusApi.setGuardianProviderFixture(journeyId as string, "NORMAL");
        return {
          zh: `服务器把信号夹具设回 NORMAL${fixture?.state ? `（现值 ${fixture.state}）` : ""}。`,
          en: `The server returned the fixture to NORMAL${fixture?.state ? ` (now ${fixture.state})` : ""}.`,
        };
      },
    },
  ];

  const act = async (row: Row) => {
    if (row.blocked || running) {
      setOutcome({
        ok: false,
        zh: row.blocked
          ? `这个动作现在做不了：${row.blocked.zh}`
          : "上一个动作还没回来，先等它。",
        en: row.blocked
          ? `This action is unavailable right now: ${row.blocked.en}`
          : "The previous action has not returned yet.",
      });
      return;
    }
    setRunning(row.id);
    setOutcome(null);
    try {
      const result = await row.run();
      setOutcome({ ok: true, ...result });
    } catch (error) {
      const named = describeFailure(error);
      setOutcome({ ok: false, zh: named.zh, en: named.en });
    } finally {
      setRunning(null);
      refreshAll();
    }
  };

  return (
    <section className="cn-sim" data-testid="sim-panel" aria-labelledby="sim-banner">
      <p
        className="cn-sim-banner"
        id="sim-banner"
        data-testid="sim-banner"
        data-scene-phase={scene.phase}
        role="status"
      >
        {scene.phase === "loading" && (zh ? "正在读服务器上的场景状态…" : "Reading the stage state from the server…")}
        {scene.phase === "unavailable" &&
          (zh
            ? `场景状态没读到：${scene.reason ?? "未知"}。`
            : `The stage state could not be read: ${scene.reason ?? "unknown"}.`)}
        {scene.phase === "ready" && scene.scene?.demoMode &&
          (zh
            ? `这是教学模拟场景，不是真实出行提醒 · 屏幕上的“现在”由服务器给定：${sceneInstant(scene.scene.effectiveNow)}`
            : `This is a teaching simulation, not live travel advice · the server supplies "now": ${sceneInstant(scene.scene.effectiveNow)}`)}
        {scene.phase === "ready" && !scene.scene?.demoMode &&
          (zh
            ? "这台部署没有开模拟舞台，下面的动作不会被执行"
            : "This deployment has no simulation stage switched on, so the actions below will not run")}
      </p>
      {/* The flag itself stays available -- the declaration may be in human words, but a lane that
          needs to know which switch the server answered must not have to guess. */}
      <p className="cn-sim-diag" data-testid="sim-diag">
        {`demo_mode=${scene.scene ? String(scene.scene.demoMode) : "—"} · basis=${scene.scene?.basis ?? "—"} · evidence=${scene.scene?.evidenceState ?? "—"}`}
      </p>

      {scene.phase === "unavailable" && (
        <button type="button" className="v8-outline-button cn-sim-retry" data-testid="sim-retry" onClick={scene.refresh}>
          {zh ? "再读一次" : "Read it again"}
        </button>
      )}

      <dl className="cn-sim-facts" data-testid="sim-scene-facts">
        <div>
          <dt>{zh ? "台上行程" : "On stage"}</dt>
          <dd data-testid="sim-journey">{`${shortId(scene.scene?.journeyId ?? null)} · ${scene.scene?.journeyStatus ?? "—"}`}</dd>
        </div>
        <div>
          <dt>{zh ? "场景窗口" : "Scene window"}</dt>
          <dd data-testid="sim-window">{`${sceneInstant(scene.scene?.sceneStartAt ?? null)} → ${sceneInstant(scene.scene?.sceneEndAt ?? null)}`}</dd>
        </div>
        <div>
          <dt>{zh ? "依据" : "Basis"}</dt>
          <dd data-testid="sim-basis">{basisWord(scene.scene?.basis ?? null, zh)}</dd>
        </div>
        <div>
          <dt>{zh ? "证据" : "Evidence"}</dt>
          <dd data-testid="sim-evidence">{`${evidenceWord(scene.scene?.evidenceState ?? null, zh)} · ${
            scene.scene?.evidenceExpiresAt ? sceneInstant(scene.scene.evidenceExpiresAt) : zh ? "没有到期时间" : "no expiry"
          }`}</dd>
        </div>
      </dl>

      {viewingJourneyId && journeyId && viewingJourneyId !== journeyId && (
        <p className="cn-sim-mismatch" data-testid="sim-journey-mismatch" role="status">
          {zh
            ? `注意：台上是行程 ${shortId(journeyId)}，而你现在这屏看的是 ${shortId(viewingJourneyId)}。下面的动作打在台上那一趟。`
            : `Note: the stage holds journey ${shortId(journeyId)} while this screen is showing ${shortId(viewingJourneyId)}. The actions below hit the one on stage.`}
        </p>
      )}

      <ul className="cn-sim-actions" data-testid="sim-actions">
        {rows.map((row) => {
          const reasonId = `sim-reason-${row.id}`;
          const busy = running !== null && running !== row.id;
          const blocked = row.blocked ?? (busy ? { zh: "上一个动作还没回来。", en: "The previous action is still running." } : null);
          return (
            <li key={row.id} className="cn-sim-row">
              <button
                type="button"
                className="v8-outline-button cn-sim-button"
                data-testid={`sim-action-${row.id}`}
                aria-disabled={blocked ? "true" : undefined}
                aria-describedby={blocked ? reasonId : undefined}
                onClick={() => void act(row)}
              >
                {running === row.id
                  ? zh
                    ? `正在执行：${row.zh}`
                    : `Running: ${row.en}`
                  : zh
                    ? row.zh
                    : row.en}
              </button>
              {blocked && (
                <p className="cn-sim-reason" id={reasonId} data-testid={`sim-blocked-${row.id}`} role="status">
                  {zh ? blocked.zh : blocked.en}
                </p>
              )}
            </li>
          );
        })}
      </ul>

      {outcome && (
        <p
          className={outcome.ok ? "cn-sim-outcome" : "cn-sim-refusal"}
          data-testid="sim-outcome"
          data-outcome={outcome.ok ? "ok" : "refused"}
          role={outcome.ok ? "status" : "alert"}
        >
          {zh ? outcome.zh : outcome.en}
        </p>
      )}
      {outcome && !outcome.ok && (
        <p className="cn-sim-outcome-note" data-testid="sim-outcome-note">
          {zh
            ? "界面没有替服务器圆场：这一步没有发生，行程保持原样。"
            : "Nothing is smoothed over: this step did not happen and the trip is unchanged."}
        </p>
      )}
    </section>
  );
}

/**
 * The one line the shell mounts.  Open by default -- an entry a traveller has to hunt for is not
 * an entry -- and collapsible with the same `<details>` shape the wizard's Advanced settings
 * already uses, so this adds no new overlay machinery to reason about.
 */
export function SimulationEntry({ viewingJourneyId = null }: { viewingJourneyId?: string | null }) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [opened, setOpened] = useState<boolean | null>(null);
  return (
    <details
      className="cn-sim-entry"
      data-testid="sim-entry"
      open={opened ?? true}
      onToggle={(event) => setOpened((event.target as HTMLDetailsElement).open)}
    >
      <summary className="cn-sim-summary" data-testid="sim-entry-summary">
        {zh ? "模拟舞台（场景时间由服务器给）" : "Simulation stage (the server owns the scene time)"}
      </summary>
      <SimulationPanel viewingJourneyId={viewingJourneyId} />
    </details>
  );
}
