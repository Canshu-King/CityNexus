import { useEffect, useRef, useState } from "react";
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
  describeBookingRefusal,
  describeFailure,
  NEXT_STEP,
  runStageAction,
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
  | "prepare"
  | "start"
  | "advance"
  | "event"
  | "replan"
  | "accept"
  | "reject"
  | "book"
  | "degrade"
  | "restore";

type Blocker = { zh: string; en: string; /** ORD-0086: true when the sentence is only about a reading
    that has not landed yet.  Those may not stick once a newer reading arrives. */ transient?: boolean };

type Row = {
  id: ActionId;
  zh: string;
  en: string;
  /** Why this row cannot run right now, or null when it can. */
  blocked: Blocker | null;
  /** `refused` marks a server answer that declined the step while still answering 200. */
  run: () => Promise<{ zh: string; en: string; refused?: boolean }>;
};

/* ORD-0078 (a) / ORD-0081 ①: the shell picks its journey once, at boot, from this key, and the
   stage routes create journeys the key has never heard of.  Handing over the id the server
   returned -- and only that -- is what lets a teacher get from the wizard to Today by pressing a
   button instead of someone editing storage. */
const JOURNEY_ID_KEY = "citynexus.v8.journey_id";
function handOverStage(journeyId: string | null | undefined) {
  if (!journeyId) return false;
  localStorage.setItem(JOURNEY_ID_KEY, journeyId);
  return true;
}

const newKey = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `sim-${Math.random().toString(36).slice(2, 12)}`;

const shortId = (value: string | null) => (value ? value.slice(0, 8) : "—");

/**
 * The phone breakpoint, as a fact the component can act on.
 *
 * ORD-0085 settled this: on a phone the entry opens **closed**.  The panel's action rows are
 * eleven deep, and the app's own geometry gate forbids any actionable element from overlapping the
 * fixed nav band at *any* settled scroll position -- an open panel in flow cannot satisfy that
 * (rows below the fold sit in the band), and taken out of flow it cannot either (a clipped row keeps
 * its unclipped rect, which is still in the band, and a fixed one covers the page's own primary
 * action instead).  Collapsed is the one shape with no overlap band at rest, and the summary keeps
 * saying what the stage is and whose clock is in use, so the honesty does not live behind a tap.
 */
function usePhoneLayout(): boolean {
  const [phone, setPhone] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(max-width: 680px)").matches,
  );
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(max-width: 680px)");
    const onChange = () => setPhone(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return phone;
}

export function SimulationPanel({
  viewingJourneyId = null,
  onStageChanged = null,
  onClose = null,
}: {
  /** The journey the shell is showing, so the panel can say when the stage is a different one. */
  viewingJourneyId?: string | null;
  /** ORD-0082: Today renders from the shell's own journey read, so any action that moves the
      stage has to tell that read to refresh.  Without it the panel advances while the hero keeps
      showing the cursor it loaded with -- a new way to show two answers on one screen. */
  onStageChanged?: ((action: ActionId) => void) | null;
  /** ORD-0085: on a phone the open panel is laid out above the fixed nav, where its own close is
      the way back -- a sheet the traveller can only leave by finding a summary off-screen is its
      own trap. */
  onClose?: (() => void) | null;
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
  /* ORD-0082 (b): whether a proposal exists is the server's fact, not this screen's memory.  A
     remembered id left 接受/拒绝 clickable on a journey whose `GET /replans` answers [] -- the tap
     then did nothing at all, which is the same silence ORD-0066 was opened against. */
  const replans = useQuery({
    queryKey: ["sim-replans", journeyId],
    enabled: Boolean(journeyId),
    queryFn: () => cityNexusApi.listReplans(journeyId as string),
  });
  const openProposals = (replans.data ?? []).filter(
    (item) =>
      !["ACCEPTED", "REJECTED", "DECLINED", "SUPERSEDED"].includes(String(item.status ?? "").toUpperCase()),
  );
  const proposalId = openProposals.length ? String(openProposals[0].id) : null;
  const [outcome, setOutcome] = useState<{
    ok: boolean;
    zh: string;
    en: string;
    /** The scene reading this line was written against, and whether it was only about a read. */
    transient: boolean;
    sceneStamp: number | null;
  } | null>(null);

  /* ORD-0086: a refusal that said "still reading" must not survive the reading.  E measured it
     stuck -- throttle the round trip, press, lift the throttle, `GET /demo/scene` answers 200, and
     the line stayed on screen until a reload, so the only way back was to leave the screen. */
  useEffect(() => {
    setOutcome((current) =>
      current?.transient && current.sceneStamp !== scene.updatedAt ? null : current,
    );
    // The stamp is deliberately the only dependency: this retires an old line, it never writes one.
  }, [scene.updatedAt]);

  /* ORD-0082 (wiring): `POST /replans/{id}/accept` requires an `Idempotency-Key` (measured: without
     it the server answers 422) and a *different* key is a *different* request.  So one key per
     proposal, kept across retries -- a second tap replays, it does not open a second acceptance. */
  const idempotencyKeys = useRef(new Map<string, string>());
  const keyFor = (scope: string) => {
    const held = idempotencyKeys.current.get(scope);
    if (held) return held;
    const created = newKey();
    idempotencyKeys.current.set(scope, created);
    return created;
  };

  const refreshAll = (action?: ActionId) => {
    if (action) onStageChanged?.(action);
    invalidateScene(client);
    void client.invalidateQueries({
      queryKey: ["v12-authoritative-twin", journeyId],
    });
    void client.invalidateQueries({
      queryKey: ["sim-stage-plan", planVersionId],
    });
    void client.invalidateQueries({
      queryKey: ["sim-replans", journeyId],
    });
  };

  const notReady =
    scene.phase !== "ready"
      ? {
          transient: true,
          zh:
            scene.phase === "loading"
              ? "还在读服务器的场景状态。"
              : "场景状态没读到，先看下面的原因。",
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
    ? {
        transient: true,
        zh: "服务器游标还在读，读完才知道有没有可推进的活动。",
        en: "The server cursor is still being read.",
      }
    : !twin.data?.current_activity_id
      ? (scene.scene?.journeyStatus ?? null) !== "ACTIVE"
        ? /* ORD-0078/0088 shape: `65e184d` stopped reset from starting the journey, so "no cursor"
             is now the normal state after 重置/准备舞台.  Saying "没有可推进的一步" alone sends the
             teacher looking for a broken button; the step exists and has a name. */
          {
            zh: `这趟还没有开始执行（服务器说行程状态是 ${scene.scene?.journeyStatus ?? "未知"}）。先按上面「开始执行」，才会有可推进的游标。`,
            en: `This journey is not executing yet (the server says ${scene.scene?.journeyStatus ?? "unknown"}). Press "Put the journey into execution" above; that is what gives a step to advance.`,
          }
        : {
            zh: "服务器说这趟在执行中，但游标是空的（没有任何活动在进行），所以这一步没有可推进的位置。",
            en: "The server says the journey is executing but the cursor is empty (no activity is in progress), so there is no position to advance from.",
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
    plan.data?.activities.find(
      (item) => item.id === twin.data?.current_activity_id,
    ) ?? null;
  const nextStep = currentActivity
    ? (NEXT_STEP[currentActivity.status] ?? null)
    : null;
  const stepBlocked =
    plan.isPending && Boolean(twin.data?.current_activity_id)
      ? {
          transient: true,
          zh: "还在读这份计划里当前活动的状态。",
          en: "The current activity's status is still being read.",
        }
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

  /* Which activity 「建一个硬承诺」 is aiming at.  The candidates are the server's own plan
     activities that are still open, with the ones it gave a service identity first -- that ordering
     is a hint about where to look, not a claim that any of them can be booked.  The label names the
     target before the tap, and the row beside it moves to the next candidate. */
  const [bookIndex, setBookIndex] = useState(0);
  const bookCandidates = (plan.data?.activities ?? [])
    .filter(
      (item) =>
        item &&
        !["COMPLETED", "SKIPPED", "CANCELLED"].includes(String(item.status)),
    )
    .sort((a, b) => Number(Boolean((b as {city_service_id?: string | null}).city_service_id)) - Number(Boolean((a as {city_service_id?: string | null}).city_service_id)));
  const bookIndexClamped = bookCandidates.length
    ? Math.min(bookIndex, bookCandidates.length - 1)
    : 0;
  const bookTarget = bookCandidates[bookIndexClamped] ?? null;
  const bookNext = bookCandidates.length
    ? bookCandidates[(bookIndexClamped + 1) % bookCandidates.length]
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
        const advance = result.advance;
        const refused =
          advance?.steps.find((step) => step.refused !== undefined) ?? null;
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
        if (result.status === "reset" && handOverStage(result.journey_id)) {
          /* A moment to read the line, then the shell re-boots onto the journey it now names; the
             longer pause on a refused advance is so the refusal itself is readable first. */
          window.setTimeout(
            () => window.location.reload(),
            reachedActive ? 1_200 : 2_400,
          );
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
      id: "prepare",
      zh: "准备舞台（生成并选定计划）",
      en: "Put a plan on the stage",
      blocked:
        notReady ??
        noJourney ??
        (scene.scene?.journeyStatus === "ACTIVE"
          ? {
              zh: "服务器说这趟已经在执行中，不需要再准备一次。",
              en: "The server says this journey is already executing; preparing again is not the step.",
            }
          : null),
      run: async () => {
        const report = await runStageAction("prepare-scenario");
        handOverStage(report.journeyId);
        const refused = Boolean(report.code);
        return {
          refused,
          zh: refused
            ? `服务器拒绝了这一步（具名 ${report.code}），行程状态仍是 ${report.journeyStatus ?? "未知"}。`
            : `服务器已把计划放上舞台：状态 ${report.journeyStatus ?? "未知"} · 计划 ${shortId(report.planVersionId)}${report.advance?.totalMs != null ? ` · ${report.advance.totalMs}ms` : ""}。`,
          en: refused
            ? `The server refused this step (code ${report.code}); the journey is still ${report.journeyStatus ?? "unknown"}.`
            : `The server put a plan on the stage: status ${report.journeyStatus ?? "unknown"} · plan ${shortId(report.planVersionId)}${report.advance?.totalMs != null ? ` · ${report.advance.totalMs}ms` : ""}.`,
        };
      },
    },
    {
      id: "book",
      zh: bookTarget
        ? `建一个硬承诺：${bookTarget.title}`
        : "建一个硬承诺",
      en: bookTarget ? `Book a commitment: ${bookTarget.title}` : "Book a commitment",
      /* Only some of the demo stage's activities can actually be booked (`_service_for_activity`
         maps a `city_service_id` or two known `place_id`s; the rest match nothing), so the row says
         *which* activity it will send before it is pressed, and offers the next candidate instead
         of silently aiming at one the server will refuse.  When it still refuses, the traveller
         reads the server's own sentence, not this screen's guess. */
      blocked:
        notReady ??
        noJourney ??
        (!bookTarget
          ? {
              zh: "服务器给的这份计划里没有可下单的活动，所以这里没有可建承诺的东西。",
              en: "The plan the server gave carries no activity that can be ordered, so there is nothing here to book.",
            }
          : null),
      run: async () => {
        const target = bookTarget as { id: string; title: string };
        try {
          const booking = await cityNexusApi.createBooking(
            journeyId as string,
            target.id,
          );
          return {
            zh: `服务器建了承诺 ${shortId(booking.id)}（${target.title} · ${booking.status} · ${formatMinorMoney(booking.amount.amount_minor, booking.amount.currency, locale)}）。`,
            en: `The server created commitment ${shortId(booking.id)} (${target.title} · ${booking.status} · ${formatMinorMoney(booking.amount.amount_minor, booking.amount.currency, locale)}).`,
          };
        } catch (error) {
          const named = describeBookingRefusal(error, target.title);
          return { refused: true, zh: named.zh, en: named.en };
        }
      },
    },
    {
      id: "start",
      zh: "开始执行（真实 /start）",
      en: "Put the journey into execution",
      blocked:
        notReady ??
        noJourney ??
        (scene.scene?.journeyStatus === "ACTIVE"
          ? {
              zh: "服务器说这趟已经在执行中，不需要再开始一次。",
              en: "The server says this journey is already executing.",
            }
          : !planVersionId
            ? {
                zh: "舞台上还没有计划（服务器回的 plan_version_id 是空的）。先按上面「准备舞台」，才有可开始的东西。",
                en: "No plan on the stage yet (the server's plan_version_id is empty). Put a plan on it first; that is what there is to start.",
              }
            : null),
      run: async () => {
        const report = await runStageAction("start-scenario");
        handOverStage(report.journeyId);
        const refused = Boolean(report.code);
        return {
          refused,
          zh: refused
            ? `服务器拒绝了这一步（具名 ${report.code}），行程状态仍是 ${report.journeyStatus ?? "未知"}。`
            : `服务器说这趟开始执行了：状态 ${report.journeyStatus ?? "未知"} · 用时 ${report.advance?.totalMs ?? 0}ms。游标在哪一站，由它下面那行说。`,
          en: refused
            ? `The server refused this step (code ${report.code}); the journey is still ${report.journeyStatus ?? "unknown"}.`
            : `The server put the journey into execution: status ${report.journeyStatus ?? "unknown"} · ${report.advance?.totalMs ?? 0}ms. Where the cursor sits is its line to say, not mine.`,
        };
      },
    },
    {
      id: "advance",
      zh: nextStep ? `推进当前活动：${nextStep.zh}` : "推进当前活动",
      en: nextStep
        ? `Advance the current activity: ${nextStep.en}`
        : "Advance the current activity",
      blocked: notReady ?? noJourney ?? cursorless ?? stepBlocked,
      run: async () => {
        if (!nextStep || !currentActivity)
          throw new Error("NO_NEXT_STEP_OFFERED");
        const after = await transitionStage(
          journeyId as string,
          currentActivity.id,
          nextStep.step,
        );
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
      blocked:
        notReady ??
        noJourney ??
        noPlan ??
        (lastEventId
          ? null
          : {
              zh: "重规划要由一个中断触发（服务器要求 trigger_event_id）。先按上面「触发一次中断」。",
              en: "A replan needs a triggering event (the server requires trigger_event_id). Raise a disruption above first.",
            }),
      run: async () => {
        const proposal = await cityNexusApi.generateReplans(
          journeyId as string,
          lastEventId as string,
          3,
          newKey(),
        );
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
      blocked:
        notReady ??
        noJourney ??
        (proposalId
          ? null
          : {
              zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可接受的东西。",
              en: "The server has not offered a proposal (its list is empty), so there is nothing to accept.",
            }),
      run: async () => {
        const accepted = await cityNexusApi.acceptReplan(
          proposalId as string,
          keyFor(`accept:${proposalId}`),
        );
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
      blocked:
        notReady ??
        noJourney ??
        (proposalId
          ? null
          : {
              zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可拒绝的东西。",
              en: "The server has not offered a proposal (its list is empty), so there is nothing to reject.",
            }),
      run: async () => {
        const rejected = await cityNexusApi.rejectReplan(
          proposalId as string,
          keyFor(`reject:${proposalId}`),
        );
        return {
          zh: `服务器记下了拒绝 ${shortId(rejected.id)}，原计划不变。`,
          en: `The server recorded the rejection of ${shortId(rejected.id)}; the plan stands.`,
        };
      },
    },
    {
      id: "degrade",
      zh: "提供方降级",
      en: "Degrade the provider",
      blocked: notReady ?? noJourney,
      run: async () => {
        const fixture = await cityNexusApi.setGuardianProviderFixture(
          journeyId as string,
          "OUTAGE",
        );
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
        const fixture = await cityNexusApi.setGuardianProviderFixture(
          journeyId as string,
          "NORMAL",
        );
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
        /* ORD-0086: a refusal about a read that has not landed is only true of *that* read.  Without
           the stamp there was no way to tell it apart from a refusal about the world, and the
           "还在读" sentence stayed up after the scene answered 200. */
        transient: Boolean(row.blocked?.transient) || Boolean(running),
        sceneStamp: scene.updatedAt,
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
      setOutcome({
        ok: !result.refused,
        transient: false,
        sceneStamp: scene.updatedAt,
        zh: result.zh,
        en: result.en,
      });
    } catch (error) {
      const named = describeFailure(error);
      setOutcome({
        ok: false,
        transient: false,
        sceneStamp: scene.updatedAt,
        zh: named.zh,
        en: named.en,
      });
    } finally {
      setRunning(null);
      refreshAll(row.id);
    }
  };

  return (
    <section
      className="cn-sim"
      data-testid="sim-panel"
      aria-labelledby="sim-banner"
      aria-busy={scene.phase === "loading" ? "true" : undefined}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose?.();
      }}
    >
      {onClose && (
        <button
          type="button"
          className="v8-quiet-button cn-sim-close"
          data-testid="sim-close"
          onClick={onClose}
        >
          {zh ? "收起舞台" : "Close the stage"}
        </button>
      )}
      <p
        className="cn-sim-banner"
        id="sim-banner"
        data-testid="sim-banner"
        data-scene-phase={scene.phase}
        role="status"
      >
        {scene.phase === "loading" &&
          (zh
            ? "正在读服务器上的场景状态…"
            : "Reading the stage state from the server…")}
        {scene.phase === "unavailable" &&
          (zh
            ? `场景状态没读到：${scene.reason ?? "未知"}。`
            : `The stage state could not be read: ${scene.reason ?? "unknown"}.`)}
        {scene.phase === "ready" &&
          scene.scene?.demoMode &&
          (zh
            ? `这是教学模拟场景，不是真实出行提醒 · 屏幕上的“现在”由服务器给定：${sceneInstant(scene.scene.effectiveNow)}`
            : `This is a teaching simulation, not live travel advice · the server supplies "now": ${sceneInstant(scene.scene.effectiveNow)}`)}
        {scene.phase === "ready" &&
          !scene.scene?.demoMode &&
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
        <button
          type="button"
          className="v8-outline-button cn-sim-retry"
          data-testid="sim-retry"
          onClick={scene.refresh}
        >
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
          <dd data-testid="sim-basis">
            {basisWord(scene.scene?.basis ?? null, zh)}
          </dd>
        </div>
        <div>
          <dt>{zh ? "证据" : "Evidence"}</dt>
          <dd data-testid="sim-evidence">{`${evidenceWord(scene.scene?.evidenceState ?? null, zh)} · ${
            scene.scene?.evidenceExpiresAt
              ? sceneInstant(scene.scene.evidenceExpiresAt)
              : zh
                ? "没有到期时间"
                : "no expiry"
          }`}</dd>
        </div>
      </dl>

      {viewingJourneyId && journeyId && viewingJourneyId !== journeyId && (
        <p
          className="cn-sim-mismatch"
          data-testid="sim-journey-mismatch"
          role="status"
        >
          {zh
            ? `注意：台上是行程 ${shortId(journeyId)}，而你现在这屏看的是 ${shortId(viewingJourneyId)}。下面的动作打在台上那一趟。`
            : `Note: the stage holds journey ${shortId(journeyId)} while this screen is showing ${shortId(viewingJourneyId)}. The actions below hit the one on stage.`}
        </p>
      )}

      <ul className="cn-sim-actions" data-testid="sim-actions">
        {rows.map((row) => {
          const reasonId = `sim-reason-${row.id}`;
          const busy = running !== null && running !== row.id;
          const blocked =
            row.blocked ??
            (busy
              ? {
                  zh: "上一个动作还没回来。",
                  en: "The previous action is still running.",
                }
              : null);
          return (
            <li key={row.id} className="cn-sim-row">
              <button
                type="button"
                className="v8-outline-button cn-sim-button"
                data-testid={`sim-action-${row.id}`}
                aria-busy={running === row.id ? "true" : undefined}
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
              {/* The way out of a refusal that names the activity: move the booking row to the next
                  candidate the server's plan lists, instead of pressing the same 422 again. */}
              {row.id === "book" && bookCandidates.length > 1 && (
                <button
                  type="button"
                  className="v8-quiet-button cn-sim-book-next"
                  data-testid="sim-book-next"
                  onClick={() =>
                    setBookIndex((bookIndexClamped + 1) % bookCandidates.length)
                  }
                >
                  {zh
                    ? `换一个活动（下一个：${bookNext?.title ?? "—"}）`
                    : `Try another activity (next: ${bookNext?.title ?? "—"})`}
                </button>
              )}
              {blocked && (
                <p
                  className="cn-sim-reason"
                  id={reasonId}
                  data-testid={`sim-blocked-${row.id}`}
                  role="status"
                >
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
          data-transient={outcome.transient ? "true" : "false"}
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
export function SimulationEntry({
  viewingJourneyId = null,
  onStageChanged = null,
  defaultOpen = null,
}: {
  viewingJourneyId?: string | null;
  onStageChanged?: ((action: ActionId) => void) | null;
  /** Closed on the wizard, where the form owns the screen and the stage is one line to open.
      `null` means "ask the layout": open on a tablet/desktop, closed on a phone (see
      `usePhoneLayout` for why a phone cannot carry eleven rows past a fixed nav). */
  defaultOpen?: boolean | null;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const phone = usePhoneLayout();
  const scene = useDemoScene();
  /* The disclosure belongs to the browser. Mirroring it in React state made every open attempt
     cancel itself: the click set the attribute, then the details' own default action toggled the
     same attribute back, and the panel never appeared. The initial pose is still this screen's to
     choose -- open on a wide layout, collapsed on a phone (see `usePhoneLayout`). */
  const detailsRef = useRef<HTMLDetailsElement | null>(null);
  useEffect(() => {
    const element = detailsRef.current;
    if (!element) return;
    const wasUntouched = !element.hasAttribute("data-user-toggled");
    if (wasUntouched) element.open = defaultOpen ?? !phone;
  }, [defaultOpen, phone]);
  /* The declaration the stage owes the traveller is in the line they see without opening
     anything: that this is a teaching simulation, and whose clock "now" comes from. */
  const declared =
    scene.phase === "loading"
      ? zh
        ? "正在读服务器上的场景状态…"
        : "Reading the stage state from the server…"
      : scene.phase === "unavailable"
        ? zh
          ? `场景状态没读到：${scene.reason ?? "未知"}`
          : `The stage state could not be read: ${scene.reason ?? "unknown"}`
        : scene.scene?.demoMode
          ? zh
            ? `教学模拟舞台 · 屏幕上的“现在”由服务器给定：${sceneInstant(scene.scene.effectiveNow)}`
            : `teaching simulation stage · the server supplies "now": ${sceneInstant(scene.scene.effectiveNow)}`
          : zh
            ? "这台部署没有开模拟舞台"
            : "this deployment has no simulation stage switched on";
  return (
    <details
      ref={detailsRef}
      className="cn-sim-entry"
      data-testid="sim-entry"
      onToggle={(event) =>
        (event.currentTarget as HTMLDetailsElement).setAttribute(
          "data-user-toggled",
          "1",
        )
      }
    >
      <summary
        className="cn-sim-summary"
        data-testid="sim-entry-summary"
        data-scene-phase={scene.phase}
      >
        {zh ? "模拟舞台（场景时间由服务器给）" : "Simulation stage (the server owns the scene time)"}
        <span className="cn-sim-summary-decl" data-testid="sim-entry-decl">
          {` · ${declared}`}
        </span>
      </summary>
      <SimulationPanel
        viewingJourneyId={viewingJourneyId}
        onStageChanged={onStageChanged}
        onClose={() => {
          if (detailsRef.current) detailsRef.current.open = false;
        }}
      />
    </details>
  );
}
