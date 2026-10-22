import { useCallback, useEffect, useRef, useState } from "react";
import {
  cityNexusApi,
  type GroupRendezvousRouteResult,
  type JourneyMembershipInvitationInboxItem,
  type JourneyMembershipInvitationManagerItem,
  type JourneyOperatorProjection,
  type JourneyRendezvousCoordinationSignal,
  type RendezvousBuddyExecutionProjection,
  type RendezvousBuddyHandoff,
  type RendezvousBuddyHandoffCandidates,
  type RendezvousBuddyPrivateRouteResult,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";
import { buildGoogleWalkingDirectionsUrl, buildOpenStreetMapPinUrl } from "./memberSideQuestNavigationLinks";

type Props = {
  journeyId: string | null;
  journeyStatus?: string | null;
  recentlyJoinedJourneyId?: string | null;
  onRefreshLocation?: (privateHandoffId?: string, signal?: AbortSignal) => Promise<string | null>;
  onJourneyJoined: (journeyId: string) => Promise<void> | void;
};

type GroupPresence = NonNullable<JourneyOperatorProjection["group_presence"]>;
type Rendezvous = NonNullable<
  GroupPresence["rendezvous"]
>;
type BuddyRouteConsent =
  | { handoffId: string; step: "LOCATION" }
  | { handoffId: string; step: "PROVIDER"; locationObservationId: string };
type BuddyDirectionsConsent = {
  handoff: RendezvousBuddyHandoff;
  handoffSnapshotKey: string;
  targetKey: string;
  audienceKey: string;
};
type BuddyReturnDirectionsConsent = {
  handoffId: string;
  executionId: string;
  targetKey: string;
  sharedStopName: string;
};

function groupPresenceTargetKey(presence: GroupPresence | null | undefined): string | null {
  const target = presence?.rendezvous;
  if (!target) return null;
  return JSON.stringify([
    presence?.active_plan_version_id ?? null,
    presence?.current_activity_id ?? null,
    target.activity_id,
    target.title,
    target.place_id,
    target.place_name,
    target.latitude,
    target.longitude,
    target.coordinate_system,
  ]);
}

function hasExactPublicPin(destination: Rendezvous | null | undefined): boolean {
  return destination?.coordinate_system === "WGS84"
    && typeof destination.latitude === "number"
    && typeof destination.longitude === "number"
    && Number.isFinite(destination.latitude)
    && Number.isFinite(destination.longitude)
    && destination.latitude >= -90 && destination.latitude <= 90
    && destination.longitude >= -180 && destination.longitude <= 180;
}

function rendezvousAudienceKey(members: GroupPresence["members"]): string {
  return JSON.stringify(members.map((member) => member.member_id).sort());
}

function buddyHandoffSnapshotKey(handoff: RendezvousBuddyHandoff): string {
  // Keep the user's consent attached to the exact accepted record, destination, expiry,
  // and original shared-stop reference that was shown in the dialog.
  return JSON.stringify(handoff);
}

function buddyHandoffCanNavigate(handoff: RendezvousBuddyHandoff): boolean {
  if (handoff.status !== "ACCEPTED") return false;
  const execution = handoff.execution;
  if (execution) {
    if (execution.status === "ACTIVE") {
      return execution.context_current === true
        && Boolean(execution.expires_at && Date.parse(execution.expires_at) > Date.now());
    }
    // A completed, cancelled, expired or stale pair execution cannot keep
    // licensing navigation to an obsolete private handoff destination.
    if (execution.status !== "WINDOW_OFFERED") return false;
  }
  // Legacy R79 acceptance and not-yet-accepted execution offers retain
  // the original 20-minute handoff expiry. An ACTIVE R82 lease overrides it.
  return Date.parse(handoff.expires_at) > Date.now();
}

function handoffStillTargetsCurrentSharedStop(
  handoff: RendezvousBuddyHandoff,
  presence: GroupPresence | null,
): boolean {
  const target = presence?.rendezvous;
  return Boolean(
    presence?.active_plan_version_id
    && target
    && target.activity_id === handoff.original_shared_stop.activity_id
    && target.place_id === handoff.original_shared_stop.place_id
    && target.place_name === handoff.original_shared_stop.place_name,
  );
}

function secureJourneyRequestKey(): string {
  // getRandomValues is supported on local-network HTTP pages where
  // randomUUID/subtle may be unavailable. Never fall back to Math.random
  // for an idempotency key that can authorize a signed member write.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return "journey-" + Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function routeEvidenceClass(result: GroupRendezvousRouteResult): "LIVE" | "REPLAY" | "UNKNOWN" {
  const provenance = String(result.route.provenance ?? "").toUpperCase();
  const provider = String(result.route.provider ?? "").trim();
  // A route with a mock/fixture provider is never live, even if its response
  // incorrectly advertises a live provenance token and fresh timestamp.
  const syntheticProvider = /(?:^|[^a-z])(mock|fixture|synthetic|test)(?:$|[^a-z])/i.test(provider);
  const duration = result.route.duration_min;
  const capturedAt = Date.parse(String(result.route.captured_at ?? ""));
  const ageMs = Date.now() - capturedAt;
  if (
    result.status.toUpperCase() !== "COMPLETED"
    || result.plan_unchanged !== true
    || result.target_unchanged !== true
    || !provider
    || syntheticProvider
    || typeof duration !== "number"
    || !Number.isFinite(duration)
    || duration < 0
    || !Number.isFinite(capturedAt)
    || ageMs < -30_000
    || ageMs > 5 * 60_000
  ) return "UNKNOWN";
  if (["LIVE_PROVIDER_CAPTURE", "LIVE_CAPTURE"].includes(provenance)) return "LIVE";
  if (["CAPTURED_REPLAY", "SEALED_REAL_REPLAY"].includes(provenance)) return "REPLAY";
  return "UNKNOWN";
}

function inviteFailureCopy(code: string, zh: boolean): string {
  if (code.includes("RECIPIENT_ACCEPTANCE_REQUIRED")) {
    return zh ? "旅伴接受邀请后即可加入。" : "The traveller must accept the invitation to join.";
  }
  if (code.includes("MEMBER_MANAGE")) {
    return zh ? "你当前没有邀请权限。" : "You do not have permission to invite companions.";
  }
  if (code.includes("ALREADY_PENDING")) {
    return zh ? "这位旅伴已有一个待处理邀请。" : "This traveller already has a pending invitation.";
  }
  if (code.includes("ACTIVE_JOURNEY")) {
    return zh ? "请先开始行程并选择方案。" : "Start the Journey and choose a plan first.";
  }
  return zh ? "邀请结果待确认，请刷新成员名单。" : "Invitation status unconfirmed. Refresh the member list.";
}

function coordinationFailureCopy(code: string, zh: boolean): string {
  if (code.includes("WITHDRAW_TARGET_STALE")) {
    return zh
      ? "先前的状态已过期或撤回。请刷新查看当前团队状态。"
      : "The status expired or was withdrawn. Refresh the team view.";
  }
  if (code.includes("CONTEXT_CHANGED") || code.includes("TARGET_CHANGED")) {
    return zh
      ? "行程已更新，请刷新并重新选择同行者。"
      : "The Journey changed. Refresh to see the current stop.";
  }
  if (code.includes("GROUP_RECOVERY_FOLLOWTHROUGH_ACTIVE")) {
    return zh
      ? "团队正在按已批准的方案会合；请在返场流程中确认到达。"
      : "The group is meeting under the recovery plan. Confirm arrival in the rejoin flow.";
  }
  if (code.includes("PLANNED_SPLIT_TARGET_UNSUPPORTED")) {
    return zh
      ? "你当前有独立的计划支线；请使用该支线的会合安排。"
      : "You are on a planned individual side trip. Use that trip's rendezvous flow.";
  }
  return zh
    ? "团队状态待确认，请刷新。"
    : "Refresh to update team status.";
}

function coordinationStatusLabel(signal: JourneyRendezvousCoordinationSignal, zh: boolean): string {
  return signal.signal_kind === "HEADING_TO_RENDEZVOUS"
    ? (zh ? `${signal.display_name} 自报正在前往会合点` : `${signal.display_name} self-reports heading to the rendezvous`)
    : (zh ? `${signal.display_name} 自报需要协调帮助` : `${signal.display_name} self-reports needing coordination help`);
}

export function JourneyMembershipPanel({
  journeyId,
  journeyStatus,
  recentlyJoinedJourneyId = null,
  onRefreshLocation,
  onJourneyJoined,
}: Props) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const active = String(journeyStatus ?? "").toUpperCase() === "ACTIVE";
  const [inbox, setInbox] = useState<JourneyMembershipInvitationInboxItem[]>([]);
  const [sent, setSent] = useState<JourneyMembershipInvitationManagerItem[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [targetTravelerId, setTargetTravelerId] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [mapConsent, setMapConsent] = useState(false);
  const [mapConsentKey, setMapConsentKey] = useState<string | null>(null);
  const [routeConsent, setRouteConsent] = useState(false);
  const [routeConsentKey, setRouteConsentKey] = useState<string | null>(null);
  const [navigationBusy, setNavigationBusy] = useState(false);
  const [groupPresence, setGroupPresence] = useState<GroupPresence | null>(null);
  const [coordinationConsentKind, setCoordinationConsentKind] = useState<JourneyRendezvousCoordinationSignal["signal_kind"] | null>(null);
  const [coordinationConsentKey, setCoordinationConsentKey] = useState<string | null>(null);
  const [coordinationConsentAudienceKey, setCoordinationConsentAudienceKey] = useState<string | null>(null);
  const [coordinationBusy, setCoordinationBusy] = useState(false);
  const [coordinationMessage, setCoordinationMessage] = useState<string | null>(null);
  const [buddyHandoffs, setBuddyHandoffs] = useState<RendezvousBuddyHandoff[]>([]);
  const [buddyCandidates, setBuddyCandidates] = useState<RendezvousBuddyHandoffCandidates | null>(null);
  const [buddySelectedPlaceId, setBuddySelectedPlaceId] = useState("");
  const [buddyExecutionWindowMinutes, setBuddyExecutionWindowMinutes] = useState<30 | 60 | 90>(60);
  const [buddyActionBusy, setBuddyActionBusy] = useState(false);
  const [buddyMessage, setBuddyMessage] = useState<string | null>(null);
  const [buddyMapConsentId, setBuddyMapConsentId] = useState<string | null>(null);
  const [buddyDirectionsConsent, setBuddyDirectionsConsent] = useState<BuddyDirectionsConsent | null>(null);
  const [buddyReturnDirectionsConsent, setBuddyReturnDirectionsConsent] = useState<BuddyReturnDirectionsConsent | null>(null);
  const [buddyPrivateRoutes, setBuddyPrivateRoutes] = useState<Record<string, RendezvousBuddyPrivateRouteResult>>({});
  const [buddyRouteConsent, setBuddyRouteConsent] = useState<BuddyRouteConsent | null>(null);
  const [buddyRouteBusy, setBuddyRouteBusy] = useState(false);
  const [buddyRouteMessage, setBuddyRouteMessage] = useState<string | null>(null);
  const buddyRouteLocationAbort = useRef<AbortController | null>(null);
  const [routeResult, setRouteResult] = useState<{
    key: string;
    result: GroupRendezvousRouteResult;
  } | null>(null);
  const rendezvous = groupPresence?.rendezvous ?? null;
  const currentTargetKey = groupPresenceTargetKey(groupPresence);
  const currentAudienceKey = groupPresence ? rendezvousAudienceKey(groupPresence.members) : null;

  const refresh = useCallback(async () => {
    const mine = await cityNexusApi.getMyJourneyMembershipInvitations().catch(() => []);
    setInbox(mine);
    if (!journeyId) {
      setSent([]);
      setCanManage(false);
      return;
    }
    try {
      setSent(await cityNexusApi.getJourneyMembershipInvitations(journeyId));
      setCanManage(true);
    } catch {
      setSent([]);
      setCanManage(false);
    }
  }, [journeyId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const refreshGroupPresence = useCallback(async (): Promise<GroupPresence | null> => {
    if (!journeyId || !active) {
      setGroupPresence(null);
      setBuddyHandoffs([]);
      setBuddyPrivateRoutes({});
      return null;
    }
    try {
      const [projection, handoffs] = await Promise.all([
        cityNexusApi.getJourneyOperator(journeyId),
        cityNexusApi.getCurrentRendezvousBuddyHandoffs(journeyId).catch(() => ({ items: [] })),
      ]);
      const next = projection.group_presence ?? null;
      setGroupPresence(next);
      setBuddyHandoffs(handoffs.items);
      const privateRouteEntries = await Promise.all(
        handoffs.items
          .filter((handoff) => handoff.status === "ACCEPTED")
          .map(async (handoff): Promise<[string, RendezvousBuddyPrivateRouteResult] | null> => {
            try {
              return [handoff.handoff_id, await cityNexusApi.getCurrentRendezvousBuddyPrivateRoute(journeyId, handoff.handoff_id)];
            } catch {
              return null;
            }
          }),
      );
      setBuddyPrivateRoutes(Object.fromEntries(privateRouteEntries.filter(
        (entry): entry is [string, RendezvousBuddyPrivateRouteResult] => entry !== null,
      )));
      return next;
    } catch {
      setGroupPresence(null);
      setBuddyHandoffs([]);
      setBuddyPrivateRoutes({});
      return null;
    }
  }, [active, journeyId]);

  useEffect(() => {
    // A companion still needs the shared meeting point after a reload, not
    // only during the React session in which they pressed Accept.
    if (!journeyId || !active) {
      setGroupPresence(null);
      setBuddyHandoffs([]);
      setBuddyPrivateRoutes({});
      setBuddyRouteConsent(null);
      setRouteResult(null);
      return;
    }
    void refreshGroupPresence();
  }, [journeyId, active, refreshGroupPresence]);

  useEffect(() => {
    setRouteResult((current) => current?.key === currentTargetKey ? current : null);
  }, [currentTargetKey]);

  useEffect(() => {
    // A refreshed member list changes who would see this disclosure. A user
    // who reviewed A/B/C must never silently end up sharing with a new D.
    if (!coordinationConsentKind) return;
    if (
      coordinationConsentKey === currentTargetKey
      && coordinationConsentAudienceKey === currentAudienceKey
    ) return;
    setCoordinationConsentKind(null);
    setCoordinationConsentKey(null);
    setCoordinationConsentAudienceKey(null);
    setCoordinationMessage(zh
      ? "会合点或同行者名单刚刚变化。旧分享确认已关闭；请重新查看受众并主动确认。"
      : "The stop or companion list changed. The previous consent was closed; review the new audience before sharing.");
  }, [
    currentTargetKey, currentAudienceKey, coordinationConsentKind,
    coordinationConsentKey, coordinationConsentAudienceKey, zh,
  ]);

  const coordinationSignals = groupPresence?.coordination_signals ?? [];
  const ownCoordinationSignal = coordinationSignals.find((signal) => signal.viewer_can_withdraw) ?? null;

  const openCoordinationConsent = (kind: JourneyRendezvousCoordinationSignal["signal_kind"]) => {
    if (!currentTargetKey || !currentAudienceKey || !groupPresence?.can_guide) return;
    setCoordinationMessage(null);
    setCoordinationConsentKey(currentTargetKey);
    setCoordinationConsentAudienceKey(currentAudienceKey);
    setCoordinationConsentKind(kind);
  };

  const shareCoordinationSignal = async () => {
    if (coordinationBusy || !journeyId || !coordinationConsentKind) return;
    const current = groupPresence;
    const target = current?.rendezvous;
    const activePlanId = current?.active_plan_version_id;
    if (
      !current || !target || !activePlanId
      || coordinationConsentKey !== currentTargetKey
      || coordinationConsentAudienceKey !== currentAudienceKey
      || !/^[a-f0-9]{64}$/.test(String(current.coordination_audience_sha256 ?? ""))
    ) {
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
      setCoordinationConsentAudienceKey(null);
      setCoordinationMessage(zh
        ? "同行者名单已更新，请刷新后重新确认受众。"
        : "The stop or audience changed. Refresh before sharing again.");
      await refreshGroupPresence();
      return;
    }
    setCoordinationBusy(true);
    setCoordinationMessage(null);
    try {
      const receipt = await cityNexusApi.shareRendezvousMemberSignal(
        journeyId,
        {
          signal_kind: coordinationConsentKind,
          expected_active_plan_version_id: activePlanId,
          expected_current_activity_id: current.current_activity_id ?? null,
          expected_rendezvous_activity_id: target.activity_id,
          expected_public_place_id: target.place_id,
          // Digest is derived from the signed in-force cohort on the server;
          // this action works even when crypto.subtle is unavailable on HTTP LAN.
          expected_audience_sha256: String(current.coordination_audience_sha256),
        },
        secureJourneyRequestKey(),
      );
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
      setCoordinationConsentAudienceKey(null);
      setCoordinationMessage(receipt.status === "ACTIVE"
        ? (zh
          ? "状态已分享，45 分钟后过期。"
          : "Status shared; expires in 45 minutes.")
        : (zh ? "状态已处理。" : "The status was processed."));
      await refreshGroupPresence();
    } catch (error) {
      const text = error instanceof Error ? error.message : "";
      setCoordinationMessage(coordinationFailureCopy(text, zh));
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
      setCoordinationConsentAudienceKey(null);
      await refreshGroupPresence();
    } finally {
      setCoordinationBusy(false);
    }
  };

  const withdrawCoordinationSignal = async () => {
    if (coordinationBusy || !journeyId || !ownCoordinationSignal) return;
    setCoordinationBusy(true);
    setCoordinationMessage(null);
    try {
      const receipt = await cityNexusApi.withdrawRendezvousMemberSignal(journeyId, ownCoordinationSignal.signal_id);
      await refreshGroupPresence();
      setCoordinationMessage(receipt.status === "REVOKED"
        ? (zh ? "已停止向后续查看者分享这条状态。" : "This exact status has been withdrawn from future projections.")
        : (zh
          ? "这条状态已经变化，不保证其他较新的状态已停止分享；请核对刚刷新后的团队状态。"
          : "This status changed; a newer one may still be shared. Check the refreshed team view."));
    } catch (error) {
      await refreshGroupPresence();
      setCoordinationMessage(coordinationFailureCopy(error instanceof Error ? error.message : "", zh));
    } finally {
      setCoordinationBusy(false);
    }
  };

  const acknowledgeCoordinationHelp = async (signal: JourneyRendezvousCoordinationSignal) => {
    if (coordinationBusy || !journeyId || !signal.viewer_can_acknowledge) return;
    setCoordinationBusy(true);
    setCoordinationMessage(null);
    try {
      await cityNexusApi.acknowledgeRendezvousHelpRequest(journeyId, signal.signal_id);
      setCoordinationMessage(zh ? "已回应这次求助。" : "Help request acknowledged.");
      await refreshGroupPresence();
    } catch (error) {
      setCoordinationMessage(coordinationFailureCopy(error instanceof Error ? error.message : "", zh));
      await refreshGroupPresence();
    } finally {
      setCoordinationBusy(false);
    }
  };

  const loadBuddyHandoffCandidates = async (signal: JourneyRendezvousCoordinationSignal) => {
    if (!journeyId || buddyActionBusy || signal.signal_kind !== "NEEDS_COORDINATION"
      || !signal.viewer_is_acknowledger || !signal.acknowledgement) return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      const candidates = await cityNexusApi.getRendezvousBuddyHandoffCandidates(journeyId, signal.signal_id);
      setBuddyCandidates(candidates);
      setBuddySelectedPlaceId(candidates.items[0]?.place_id ?? "");
    } catch {
      setBuddyMessage(zh
        ? "求助或同行者名单已更新，请刷新团队状态。"
        : "The request or companion list changed. Refresh team status.");
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const offerBuddyHandoff = async () => {
    const candidates = buddyCandidates;
    const current = groupPresence;
    const original = current?.rendezvous;
    if (!journeyId || !candidates || !current || !original || !buddySelectedPlaceId || buddyActionBusy) return;
    if (
      current.active_plan_version_id !== candidates.active_plan_version_id
      || (current.current_activity_id ?? null) !== candidates.current_activity_id
      || original.activity_id !== candidates.rendezvous_activity_id
      || original.place_id !== candidates.original_public_place_id
      || current.coordination_audience_sha256 !== candidates.audience_sha256
    ) {
      setBuddyCandidates(null);
      setBuddyMessage(zh
        ? "行程已更新；接应地点未提交。请刷新建议。"
        : "The plan, stop, or companion set changed. The old place was not offered; reload suggestions.");
      return;
    }
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      await cityNexusApi.offerRendezvousBuddyHandoff(journeyId, {
        help_signal_id: candidates.help_signal_id,
        expected_active_plan_version_id: candidates.active_plan_version_id,
        expected_current_activity_id: candidates.current_activity_id,
        expected_rendezvous_activity_id: candidates.rendezvous_activity_id,
        expected_original_public_place_id: candidates.original_public_place_id,
        expected_audience_sha256: candidates.audience_sha256,
        handoff_place_id: buddySelectedPlaceId,
        execution_window_minutes: buddyExecutionWindowMinutes,
      }, secureJourneyRequestKey());
      setBuddyCandidates(null);
      setBuddySelectedPlaceId("");
      setBuddyMessage(zh
        ? `已提议公开地点和 ${buddyExecutionWindowMinutes} 分钟接应窗口；对方接受后开始。`
        : `Public meeting place offered with a ${buddyExecutionWindowMinutes}-minute window. It starts after the requester accepts.`);
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh
        ? "接应提议未创建，请刷新后重试。"
        : "The handoff was not created. Refresh and recheck the request, place, and shared plan.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const respondToBuddyHandoff = async (handoff: RendezvousBuddyHandoff, decision: "ACCEPT" | "DECLINE") => {
    if (!journeyId || buddyActionBusy || handoff.viewer_role !== "REQUESTER") return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      await cityNexusApi.respondToRendezvousBuddyHandoff(journeyId, handoff.handoff_id, decision);
      setBuddyMessage(decision === "ACCEPT"
        ? (handoff.execution?.status === "WINDOW_OFFERED"
          ? (zh
            ? `你已签名接受公开接应地点和 ${handoff.execution.execution_window_minutes} 分钟执行窗口；窗口从现在开始。`
            : `You signed to accept the public handoff and its ${handoff.execution.execution_window_minutes}-minute execution window. The window starts now.`)
          : (zh ? "已接受双方公共会合提议。" : "Accepted the public meeting proposal."))
        : (zh ? "已拒绝提议。" : "Proposal declined."));
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh
        ? "提议已过期，请刷新。"
        : "The offer expired or its context changed. The stale place was not accepted; refresh.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const offerBuddyExecutionWindow = async (
    handoff: RendezvousBuddyHandoff,
    windowMinutes: 30 | 60 | 90,
  ) => {
    if (!journeyId || buddyActionBusy || handoff.viewer_role !== "HELPER" || handoff.status !== "ACCEPTED") return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      await cityNexusApi.offerRendezvousBuddyExecutionWindow(
        journeyId, handoff.handoff_id, windowMinutes, secureJourneyRequestKey(),
      );
      setBuddyMessage(zh
          ? `已提出 ${windowMinutes} 分钟接应窗口；对方签名接受后开始。`
          : `You offered a ${windowMinutes}-minute handoff window. It starts after the requester accepts.`);
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh
        ? "接应窗口未创建，请刷新后重试。"
        : "The execution window was not created. The handoff or shared context may have expired; refresh and review it.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const acceptBuddyExecutionWindow = async (handoff: RendezvousBuddyHandoff) => {
    if (!journeyId || buddyActionBusy || handoff.viewer_role !== "REQUESTER") return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      await cityNexusApi.acceptRendezvousBuddyExecutionWindow(journeyId, handoff.handoff_id);
      setBuddyMessage(zh ? "你已签名接受有限接应窗口；现在才开始计时。" : "You signed to accept the bounded assist window. Its clock starts now.");
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh
        ? "接应窗口已过期，请重新协商。"
        : "The window offer expired or its context changed. The old handoff was not extended; refresh and agree again.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const reportBuddyExecution = async (
    handoff: RendezvousBuddyHandoff,
    execution: RendezvousBuddyExecutionProjection,
    receiptKind: "BUDDY_MET_ACK" | "CANNOT_MEET" | "CANCEL_PARTICIPATION",
  ) => {
    if (!journeyId || buddyActionBusy || !execution.can_report) return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      const receipt = await cityNexusApi.reportRendezvousBuddyExecution(
        journeyId, handoff.handoff_id, execution.execution_id, receiptKind, secureJourneyRequestKey(),
      );
      setBuddyMessage(receipt.status === "MUTUALLY_ACKNOWLEDGED"
        ? (zh
          ? "双方已独立确认接应完成。"
          : "Both members confirmed the assist.")
        : receipt.status === "REPLAN_REQUIRED"
          ? (zh ? "已记录无法接应。请重新协调或按当前会合点继续。" : "Meetup unavailable. Coordinate again or continue to the current meetup.")
          : receipt.status === "CANCELLED"
            ? (zh ? "已退出接应，可单独导航回当前会合点。" : "You left the assist. You can navigate to the current meetup.")
            : (zh ? "本人状态已记录，等待对方确认。" : "Your status is recorded; waiting for the other member."));
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh
        ? "自报未保存，请刷新接应状态。"
        : "The self-report was not recorded. The window may have expired or the plan changed; refresh before deciding again.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const closeBuddyHandoff = async (handoff: RendezvousBuddyHandoff) => {
    if (!journeyId || buddyActionBusy) return;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      if (handoff.viewer_role === "HELPER") {
        await cityNexusApi.cancelRendezvousBuddyHandoff(journeyId, handoff.handoff_id);
      } else {
        await cityNexusApi.revokeRendezvousBuddyHandoff(journeyId, handoff.handoff_id);
      }
      setBuddyMessage(zh ? "双方接应提议已关闭。" : "Pair handoff closed.");
      if (buddyMapConsentId === handoff.handoff_id) setBuddyMapConsentId(null);
      if (buddyDirectionsConsent?.handoff.handoff_id === handoff.handoff_id) setBuddyDirectionsConsent(null);
      await refreshGroupPresence();
    } catch {
      setBuddyMessage(zh ? "提议已过期或已关闭；请刷新查看当前状态。" : "The handoff expired or was already closed. Refresh to see the current state.");
      await refreshGroupPresence();
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const openAcceptedBuddyMap = async () => {
    const handoffId = buddyMapConsentId;
    if (!journeyId || !handoffId || buddyActionBusy) return;
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setBuddyMessage(zh ? "浏览器阻止了新窗口；允许弹窗后重新确认。" : "The browser blocked the new tab. Allow popups and confirm again.");
      return;
    }
    popup.opener = null;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      const fresh = await cityNexusApi.getCurrentRendezvousBuddyHandoffs(journeyId);
      const handoff = fresh.items.find((item) => item.handoff_id === handoffId && item.status === "ACCEPTED");
      const place = handoff?.handoff_place;
      const stillValid = handoff && buddyHandoffCanNavigate(handoff)
        && place?.coordinate_system === "WGS84"
        && Number.isFinite(place.latitude) && place.latitude >= -90 && place.latitude <= 90
        && Number.isFinite(place.longitude) && place.longitude >= -180 && place.longitude <= 180;
      if (!stillValid || !place) {
        popup.close();
        setBuddyMessage(zh
          ? "地点提议已过期，未打开地图。"
        : "Handoff expired. Refresh before opening the map.");
        setBuddyMapConsentId(null);
        await refreshGroupPresence();
        return;
      }
      popup.location.href = buildOpenStreetMapPinUrl({
        latitude: place.latitude,
        longitude: place.longitude,
        coordinate_system: "WGS84",
      });
      setBuddyMapConsentId(null);
    } catch {
      popup.close();
      setBuddyMessage(zh
        ? "双方授权已过期，未打开地图。"
        : "Handoff status changed. Refresh before opening the map.");
      setBuddyMapConsentId(null);
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const beginBuddyDirectionsConsent = (handoff: RendezvousBuddyHandoff) => {
    if (!buddyHandoffCanNavigate(handoff) || !currentTargetKey || !currentAudienceKey
      || !handoffStillTargetsCurrentSharedStop(handoff, groupPresence)) {
      setBuddyMessage(zh
        ? "请先刷新双方接应状态。"
        : "Refresh the pair handoff first.");
      return;
    }
    setBuddyMessage(null);
    setBuddyDirectionsConsent({
      handoff,
      handoffSnapshotKey: buddyHandoffSnapshotKey(handoff),
      targetKey: currentTargetKey,
      audienceKey: currentAudienceKey,
    });
  };

  const beginBuddyReturnDirectionsConsent = (handoff: RendezvousBuddyHandoff) => {
    const stop = groupPresence?.rendezvous;
    const execution = handoff.execution;
    if (
      handoff.status !== "ACCEPTED"
      || !execution?.can_return_to_shared_stop
      || !execution.context_current
      || !currentTargetKey
      || !stop
      || !hasExactPublicPin(stop)
      || !handoffStillTargetsCurrentSharedStop(handoff, groupPresence)
    ) {
      setBuddyMessage(zh
        ? "请刷新接应状态和会合点，再打开地图。"
        : "Refresh the handoff and rendezvous before opening the map.");
      return;
    }
    setBuddyMessage(null);
    setBuddyReturnDirectionsConsent({
      handoffId: handoff.handoff_id,
      executionId: execution.execution_id,
      targetKey: currentTargetKey,
      sharedStopName: stop.place_name,
    });
  };

  const openBuddyReturnDirections = async () => {
    const consent = buddyReturnDirectionsConsent;
    if (!journeyId || !consent || buddyActionBusy) return;
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setBuddyMessage(zh
        ? "浏览器拦截了地图窗口，请允许弹窗后重试。"
        : "The browser blocked the map. Allow pop-ups and try again.");
      return;
    }
    popup.opener = null;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      // This is a fresh, destination-only consent. Recheck both the signed pair
      // outcome and current shared plan/cursor immediately before opening Maps.
      const [projection, current] = await Promise.all([
        cityNexusApi.getJourneyOperator(journeyId),
        cityNexusApi.getCurrentRendezvousBuddyHandoffs(journeyId),
      ]);
      const presence = projection.group_presence ?? null;
      const freshHandoff = current.items.find((item) => item.handoff_id === consent.handoffId);
      const execution = freshHandoff?.execution;
      const stop = presence?.rendezvous;
      const freshTargetKey = groupPresenceTargetKey(presence);
      const stillCurrent = freshHandoff?.status === "ACCEPTED"
        && execution?.execution_id === consent.executionId
        && execution.can_return_to_shared_stop
        && execution.context_current
        && freshTargetKey === consent.targetKey
        && Boolean(stop && presence?.active_plan_version_id && hasExactPublicPin(stop));

      setGroupPresence(presence);
      setBuddyHandoffs(current.items);
      if (!stillCurrent || !stop) {
        popup.close();
        setBuddyReturnDirectionsConsent(null);
        setBuddyMessage(zh
          ? "行程已更新，地点未发送。请刷新并重新授权。"
          : "The shared stop changed. Refresh and approve it again to open the map.");
        return;
      }

      popup.location.href = buildGoogleWalkingDirectionsUrl({
        kind: "SHARED_RENDEZVOUS",
        place_id: stop.place_id,
        name: stop.place_name,
        latitude: stop.latitude,
        longitude: stop.longitude,
        coordinate_system: stop.coordinate_system,
        provenance: {
          provider_key: "citynexus-current-shared-plan-stop",
          external_id: stop.activity_id,
          source_coordinate_system: stop.coordinate_system,
        },
        navigation_available: true,
        unavailable_reason: null,
      });
      setBuddyReturnDirectionsConsent(null);
      setBuddyMessage(zh
        ? "已将共同会合点交给 Google Maps。"
        : "The shared stop was sent to Google Maps.");
    } catch {
      popup.close();
      setBuddyReturnDirectionsConsent(null);
      setBuddyMessage(zh
        ? "会合点已更新，请刷新后再打开地图。"
        : "Refresh the handoff and meetup before opening the map.");
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const openAcceptedBuddyDirections = async () => {
    const consent = buddyDirectionsConsent;
    if (!journeyId || !consent || buddyActionBusy) return;
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setBuddyMessage(zh
        ? "浏览器拦截了地图窗口，请允许弹窗后重试。"
        : "The browser blocked the map. Allow pop-ups and try again.");
      return;
    }
    popup.opener = null;
    setBuddyActionBusy(true);
    setBuddyMessage(null);
    try {
      // Re-read both caller-private handoff state and the live shared plan/cursor
      // immediately before any external destination is released.
      const [projection, current] = await Promise.all([
        cityNexusApi.getJourneyOperator(journeyId),
        cityNexusApi.getCurrentRendezvousBuddyHandoffs(journeyId),
      ]);
      const presence = projection.group_presence ?? null;
      const freshHandoff = current.items.find((item) => item.handoff_id === consent.handoff.handoff_id);
      const freshTargetKey = groupPresenceTargetKey(presence);
      const freshAudienceKey = presence ? rendezvousAudienceKey(presence.members) : null;
      const place = freshHandoff?.handoff_place;
      const exactPublicDestination = place
        && (place.source_kind === "CURRENT_SHARED_PLAN_STOP" || place.source_kind === "PUBLIC_PLACE_CATALOG_RECORD")
        && place.coordinate_system === "WGS84"
        && Number.isFinite(place.latitude) && place.latitude >= -90 && place.latitude <= 90
        && Number.isFinite(place.longitude) && place.longitude >= -180 && place.longitude <= 180;
      const stillCurrent = Boolean(freshHandoff && buddyHandoffCanNavigate(freshHandoff))
        && freshHandoff !== undefined
        && buddyHandoffSnapshotKey(freshHandoff) === consent.handoffSnapshotKey
        && freshTargetKey === consent.targetKey
        && freshAudienceKey === consent.audienceKey
        && handoffStillTargetsCurrentSharedStop(freshHandoff, presence)
        && exactPublicDestination;

      setGroupPresence(presence);
      setBuddyHandoffs(current.items);
      if (!stillCurrent || !freshHandoff || !place) {
        popup.close();
        setBuddyDirectionsConsent(null);
        setBuddyMessage(zh
          ? "授权或行程已更新，地点未发送。请刷新并重新授权。"
          : "The handoff or Journey changed. Refresh and approve the current destination.");
        return;
      }

      const url = buildGoogleWalkingDirectionsUrl({
        kind: "SHARED_RENDEZVOUS",
        place_id: place.place_id,
        name: place.name,
        latitude: place.latitude,
        longitude: place.longitude,
        coordinate_system: place.coordinate_system,
        provenance: {
          provider_key: place.source_provider_key,
          external_id: place.source_external_id,
          source_coordinate_system: place.coordinate_system,
        },
        navigation_available: true,
        unavailable_reason: null,
      });
      popup.location.href = url;
      setBuddyDirectionsConsent(null);
      setBuddyMessage(zh
        ? "已在 Google Maps 打开目的地。"
        : "Destination opened in Google Maps.");
    } catch {
      popup.close();
      setBuddyDirectionsConsent(null);
      setBuddyMessage(zh
        ? "接应状态已更新，请刷新后再打开地图。"
        : "Refresh the handoff and shared stop before opening the map.");
    } finally {
      setBuddyActionBusy(false);
    }
  };

  const beginBuddyRouteCheck = (handoff: RendezvousBuddyHandoff) => {
    if (!onRefreshLocation || buddyRouteBusy || buddyActionBusy) return;
    setBuddyRouteMessage(null);
    setBuddyRouteConsent({ handoffId: handoff.handoff_id, step: "LOCATION" });
  };

  const confirmBuddyRouteLocation = async () => {
    if (!journeyId || !onRefreshLocation || !buddyRouteConsent || buddyRouteConsent.step !== "LOCATION" || buddyRouteBusy) return;
    const controller = new AbortController();
    buddyRouteLocationAbort.current = controller;
    setBuddyRouteBusy(true);
    setBuddyRouteMessage(null);
    try {
      const observationId = await onRefreshLocation(buddyRouteConsent.handoffId, controller.signal);
      if (controller.signal.aborted) return;
      if (!observationId) {
        setBuddyRouteMessage(zh
          ? "位置未保存，路线未请求。"
        : "Location capture failed. Try again to calculate a route.");
        setBuddyRouteConsent(null);
        return;
      }
      setBuddyRouteConsent({
        handoffId: buddyRouteConsent.handoffId,
        step: "PROVIDER",
        locationObservationId: observationId,
      });
    } catch {
      setBuddyRouteMessage(zh
        ? "位置读取失败，路线未请求。"
        : "Location capture failed. Try again to calculate a route.");
      setBuddyRouteConsent(null);
    } finally {
      if (buddyRouteLocationAbort.current === controller) buddyRouteLocationAbort.current = null;
      setBuddyRouteBusy(false);
    }
  };

  const confirmBuddyRouteProviderDisclosure = async () => {
    if (!journeyId || !buddyRouteConsent || buddyRouteConsent.step !== "PROVIDER" || buddyRouteBusy) return;
    const { handoffId, locationObservationId } = buddyRouteConsent;
    setBuddyRouteBusy(true);
    setBuddyRouteMessage(null);
    try {
      const result = await cityNexusApi.acquireRendezvousBuddyPrivateRoute(journeyId, handoffId, {
        location_observation_id: locationObservationId,
        requested_mode: "WALK",
        external_provider_disclosure_confirmed: true,
      });
      setBuddyPrivateRoutes((current) => ({ ...current, [handoffId]: result }));
      setBuddyRouteConsent(null);
      setBuddyRouteMessage(result.route_state === "UNKNOWN"
        ? (zh ? "路线资料不足，状态 UNKNOWN。" : "Route data is incomplete; status UNKNOWN.")
        : (zh ? "已生成仅你可见的路线。" : "Your private route is ready."));
      await refreshGroupPresence();
    } catch {
      setBuddyRouteConsent(null);
      setBuddyRouteMessage(zh
        ? "行程已更新，请刷新并重新授权路线。"
        : "The handoff or Journey changed. Refresh and approve the current route.");
      await refreshGroupPresence();
    } finally {
      setBuddyRouteBusy(false);
    }
  };

  const cancelBuddyRouteConsent = () => {
    if (buddyRouteBusy && buddyRouteConsent?.step !== "LOCATION") return;
    if (buddyRouteConsent?.step === "LOCATION" && buddyRouteBusy) {
      buddyRouteLocationAbort.current?.abort();
      setBuddyRouteBusy(false);
      setBuddyRouteConsent(null);
      setBuddyRouteMessage(zh
        ? "已取消位置读取。已提交的位置保存请求仍在处理中，请刷新查看结果。"
        : "Location capture cancelled. Refresh the status before trying again.");
      return;
    }
    const observationWasSaved = buddyRouteConsent?.step === "PROVIDER";
    setBuddyRouteConsent(null);
    if (observationWasSaved) {
      setBuddyRouteMessage(zh
        ? "位置观察已留在 Journey 中；你取消了外部路线请求。"
        : "The location observation remains in the Journey; you cancelled the external route request.");
    }
  };

  const createInvitation = async () => {
    const target = targetTravelerId.trim();
    if (!target || busyId) return;
    setBusyId("create");
    setMessage(null);
    try {
      const created = await cityNexusApi.createJourneyMembershipInvitation(
        journeyId,
        target,
        secureJourneyRequestKey(),
      );
      setTargetTravelerId("");
      setMessage(zh
        ? `邀请已发送，等待接受 · 有效期至 ${new Date(created.expires_at).toLocaleString(locale)}。`
        : `Invitation sent · pending acceptance · expires ${new Date(created.expires_at).toLocaleString(locale)}.`);
      await refresh();
    } catch (error) {
      const text = error instanceof Error ? error.message : "";
      setMessage(inviteFailureCopy(text, zh));
    } finally {
      setBusyId(null);
    }
  };

  const respond = async (
    invitation: JourneyMembershipInvitationInboxItem,
    decision: "ACCEPT" | "DECLINE",
  ) => {
    if (busyId) return;
    setBusyId(invitation.invitation_id);
    setMessage(null);
    try {
      const result = await cityNexusApi.respondToJourneyMembershipInvitation(
        invitation.invitation_id,
        decision,
      );
      await refresh();
      if (decision === "ACCEPT" && result.journey_id) {
        try {
          await onJourneyJoined(result.journey_id);
        } catch {
          setMessage(zh
            ? "你已加入这趟行程，但当前页面未能加载；刷新页面即可继续。"
            : "You joined the Journey, but this page could not load it. Refresh to continue.");
          return;
        }
        setMessage(zh
          ? "已加入行程；请重新确认待处理的地点分享和决定。"
          : "Joined the Journey. Reconfirm pending Place shares and decisions.");
      } else {
        setMessage(zh ? "已谢绝邀请。" : "Invitation declined.");
      }
    } catch (error) {
      setMessage(inviteFailureCopy(error instanceof Error ? error.message : "", zh));
      await refresh();
    } finally {
      setBusyId(null);
    }
  };

  const revoke = async (invitationId: string) => {
    if (busyId) return;
    setBusyId(invitationId);
    setMessage(null);
    try {
      await cityNexusApi.revokeJourneyMembershipInvitation(journeyId, invitationId);
      await refresh();
      setMessage(zh ? "邀请已撤回。" : "Invitation revoked.");
    } catch {
      setMessage(zh ? "邀请状态已更新，请刷新查看。" : "Invitation status updated. Refresh to view it.");
      await refresh();
    } finally {
      setBusyId(null);
    }
  };

  const openPublicMap = async () => {
    const expectedKey = mapConsentKey;
    if (!journeyId || !rendezvous || !expectedKey || navigationBusy) return;
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setMessage(zh ? "浏览器阻止了新窗口；允许此站点打开新窗口后再试。" : "The browser blocked the new tab. Allow popups for this site and try again.");
      return;
    }
    popup.opener = null;
    setNavigationBusy(true);
    setMessage(null);
    try {
      // Bind the external release to the same plan, cursor, Place and public
      // coordinates the traveller saw before confirming consent.
      const fresh = await cityNexusApi.getJourneyOperator(journeyId);
      const freshPresence = fresh.group_presence ?? null;
      const freshTarget = freshPresence?.rendezvous ?? null;
      setGroupPresence(freshPresence);
      if (!freshTarget || groupPresenceTargetKey(freshPresence) !== expectedKey) {
        popup.close();
        setMapConsent(false);
        setMapConsentKey(null);
        setMessage(zh
          ? "会合点已更新，请刷新后重新打开地图。"
          : "The meetup changed. Refresh to open its current location.");
        return;
      }
      const url = hasExactPublicPin(freshTarget)
        ? buildOpenStreetMapPinUrl({
            latitude: Number(freshTarget.latitude),
            longitude: Number(freshTarget.longitude),
            coordinate_system: "WGS84",
          })
        : `https://www.openstreetmap.org/search?query=${encodeURIComponent(freshTarget.place_name)}`;
      popup.location.href = url;
      setMapConsent(false);
      setMapConsentKey(null);
    } catch {
      popup.close();
      setMapConsent(false);
      setMapConsentKey(null);
      setMessage(zh
        ? "会合点已更新，请刷新后再打开地图。"
        : "Refresh the current meetup before opening the map.");
    } finally {
      setNavigationBusy(false);
    }
  };

  const requestRouteConsent = () => {
    if (!journeyId || !groupPresence?.can_guide || !onRefreshLocation) {
      setMessage(zh ? "共享会合点不可用，可改用公开地点地图。" : "Shared meetup unavailable. Open the public-place map instead.");
      return;
    }
    if (!hasExactPublicPin(rendezvous)) {
      setMessage(zh ? "会合点缺少可靠坐标，可按名称搜索并核对地点。" : "Meetup coordinates are unavailable. Search by name and check the place.");
      return;
    }
    if (!currentTargetKey) return;
    setRouteResult(null);
    setRouteConsentKey(currentTargetKey);
    setRouteConsent(true);
    setMessage(null);
  };

  const requestPersonalRoute = async () => {
    const expectedKey = routeConsentKey;
    if (!journeyId || !expectedKey || !onRefreshLocation || navigationBusy) return;
    setRouteConsent(false);
    setRouteConsentKey(null);
    setNavigationBusy(true);
    setRouteResult(null);
    setMessage(null);
    try {
      // Revalidate before asking for location, then again after the sample and
      // after routing. A changed plan/cursor/Place never receives a stale ETA.
      const before = await refreshGroupPresence();
      if (
        !before?.can_guide
        || groupPresenceTargetKey(before) !== expectedKey
        || !hasExactPublicPin(before.rendezvous)
      ) {
        setMessage(zh
          ? "会合点已更新，请刷新后重试。"
          : "The meetup changed. Review the current stop before sharing location.");
        return;
      }

      const observationId = await onRefreshLocation();
      if (!observationId) {
        setMessage(zh
          ? "未获取位置，可改用公开会合点地图。"
        : "Share your location to calculate a route, or open the public map.");
        return;
      }
      const afterLocation = await refreshGroupPresence();
      if (
        !afterLocation?.can_guide
        || groupPresenceTargetKey(afterLocation) !== expectedKey
        || !hasExactPublicPin(afterLocation.rendezvous)
      ) {
        setMessage(zh
          ? "行程已更新，请查看新目的地后重试。"
        : "The meetup changed during location capture. Refresh and confirm the new stop.");
        return;
      }

      const result = await cityNexusApi.routeToGroupRendezvous(journeyId, observationId);
      const afterRoute = await refreshGroupPresence();
      const latestTarget = afterRoute?.rendezvous;
      const targetMatches = Boolean(
        afterRoute
        && latestTarget
        && result.plan_unchanged
        && result.target_unchanged
        && result.plan_version_id === afterRoute.active_plan_version_id
        && result.current_activity_id === (afterRoute.current_activity_id ?? null)
        && result.target.activity_id === latestTarget.activity_id
        && result.target.place_id === latestTarget.place_id
        && result.target.place_name === latestTarget.place_name
        && result.target.latitude === latestTarget.latitude
        && result.target.longitude === latestTarget.longitude
        && result.target.coordinate_system === latestTarget.coordinate_system
        && groupPresenceTargetKey(afterRoute) === expectedKey,
      );
      if (!targetMatches) {
        setMessage(zh
          ? "路线计算期间行程已更新，请重新确认目的地。"
          : "The plan, progress, or destination changed during routing. The old route was discarded; review the current stop and confirm again.");
        return;
      }
      setRouteResult({ key: expectedKey, result });
      setMessage(routeEvidenceClass(result) === "UNKNOWN"
        ? (zh ? "暂无可靠路线时间。" : "Reliable route timing is unavailable.")
        : (zh ? "路线已绑定当前共同目的地。" : "Route bound to the current shared stop."));
    } catch {
      await refreshGroupPresence();
      setMessage(zh
        ? "路线已过期，可打开公开会合点地图。"
        : "The route is unavailable or expired; no duration is shown. The public meeting-place map remains available.");
    } finally {
      setNavigationBusy(false);
    }
  };

  const buddyMapConsentHandoff = buddyMapConsentId
    ? buddyHandoffs.find((handoff) => handoff.handoff_id === buddyMapConsentId && handoff.status === "ACCEPTED") ?? null
    : null;
  const buddyRouteConsentHandoff = buddyRouteConsent
    ? buddyHandoffs.find((handoff) => handoff.handoff_id === buddyRouteConsent.handoffId && handoff.status === "ACCEPTED") ?? null
    : null;
  const visibleRoute = routeResult?.key === currentTargetKey ? routeResult.result : null;
  const visibleRouteClass = visibleRoute ? routeEvidenceClass(visibleRoute) : null;
  return (
    <section className="journey-membership-panel" data-testid="journey-membership-panel">
      <div className="journey-membership-heading">
        <div>
          <span className="v8-kicker">{zh ? "同行者加入" : "Companion access"}</span>
          <h2>{zh ? "加入正在进行的行程" : "Join an active Journey"}</h2>
        </div>
        <button type="button" data-testid="journey-membership-refresh" onClick={() => void refresh()} disabled={busyId !== null}>
          {zh ? "刷新" : "Refresh"}
        </button>
      </div>

      {inbox.length > 0 && (
        <div className="journey-membership-inbox" aria-label={zh ? "待处理的行程邀请" : "Pending Journey invitations"}>
          {inbox.map((invitation) => (
            <article key={invitation.invitation_id} data-testid="journey-membership-invitation">
              <strong>{invitation.inviter_display_name} {zh ? "邀请你加入" : "invited you to join"} {invitation.journey_title}</strong>
              <p>
                {invitation.city_code} · {invitation.approximate_start_date} · {zh ? "同行者" : "Collaborator"}
              </p>
              <small>
                {zh ? "接受前显示行程概况和建议角色 · 有效期至 " : "Journey summary and suggested role · Expires "}
                {new Date(invitation.expires_at).toLocaleString(locale)}
              </small>
              <div className="journey-membership-actions">
                <button
                  type="button"
                  data-testid="journey-membership-accept"
                  disabled={busyId !== null}
                  onClick={() => void respond(invitation, "ACCEPT")}
                >{zh ? "接受并加入" : "Accept and join"}</button>
                <button
                  type="button"
                  data-testid="journey-membership-decline"
                  disabled={busyId !== null}
                  onClick={() => void respond(invitation, "DECLINE")}
                >{zh ? "谢绝" : "Decline"}</button>
              </div>
            </article>
          ))}
        </div>
      )}
      {inbox.length === 0 && (
        <small>{zh ? "目前没有待处理的行程邀请。" : "You have no pending Journey invitations."}</small>
      )}

      {canManage && (
        <div className="journey-membership-invite-form">
          <label htmlFor="journey-membership-target-id">
            {zh ? "已注册旅伴的 CityNexus 账户 ID" : "Existing traveller’s CityNexus account ID"}
          </label>
          <div className="journey-membership-actions">
            <input
              id="journey-membership-target-id"
              data-testid="journey-membership-target-id"
              value={targetTravelerId}
              onChange={(event) => setTargetTravelerId(event.target.value)}
              placeholder="traveler-id"
              autoComplete="off"
            />
            <button
              type="button"
              data-testid="journey-membership-send"
              disabled={!active || !targetTravelerId.trim() || busyId !== null}
              onClick={() => void createInvitation()}
            >{busyId === "create" ? (zh ? "发送中…" : "Sending…") : (zh ? "邀请为同行者" : "Invite as companion")}</button>
          </div>
          <small>
            {zh
              ? "邀请 24 小时内有效；对方接受后以同行者身份加入。"
              : "The invitation lasts 24 hours. The recipient joins as a companion after accepting."}
          </small>
          {!active && <small>{zh ? "请先开始行程并选择方案。" : "Start the Journey and choose a plan first."}</small>}
          {sent.filter((item) => item.state === "OFFERED").map((invitation) => (
            <article key={invitation.invitation_id} data-testid="journey-membership-sent-invitation">
              <span>{invitation.target_display_name} · {zh ? "待接受" : "Awaiting acceptance"}</span>
              <button
                type="button"
                disabled={busyId !== null}
                onClick={() => void revoke(invitation.invitation_id)}
              >{zh ? "撤回" : "Revoke"}</button>
            </article>
          ))}
        </div>
      )}

      {journeyId && active && (
        <div className="journey-membership-catchup" data-testid="journey-membership-catchup">
          <strong>{recentlyJoinedJourneyId === journeyId
            ? (zh ? "如何追上同行者？" : "How do I catch up?")
            : (zh ? "下一处共同会合点" : "Next shared meeting stop")}</strong>
          {rendezvous ? (
            <>
              <p>{zh ? `当前计划指定的会合地点：${rendezvous.place_name}。` : `Plan-selected meeting stop: ${rendezvous.place_name}.`}</p>
              <small>{hasExactPublicPin(rendezvous)
                ? (zh ? "地图标记来自当前计划的公共地点。" : "Map pin from the public Place in the current plan.")
                : (zh ? "暂无精确坐标，可按名称搜索；出发前请核对地点。" : "Exact coordinates are unavailable. Search by name and check the place before leaving.")}</small>
              <small data-testid="journey-membership-location-truth">{visibleRoute
                ? visibleRouteClass === "UNKNOWN"
                  ? (zh
                    ? "路线时长待确认；前台位置可能已保存至 Journey。"
                    : "This route request did not establish a trustworthy ETA. Your consented foreground location observation may already be stored on this Journey.")
                  : (zh
                    ? "下方路线来自你主动授权的检查；前台位置观察可能保留在 Journey，旅伴可能看到变化后的粗粒度队伍状态。"
                    : "The route below follows your explicit location consent. The foreground observation may remain on this Journey and can change companions' coarse group-presence view.")
                : (zh
                  ? "个人 ETA 需要重新授权一次前台定位；此前的位置观察仍保存在 Journey。"
                  : "Checking a personal ETA needs fresh foreground location consent. Earlier observations remain on this Journey.")}</small>
              <button type="button" onClick={() => {
                setMapConsentKey(currentTargetKey);
                setMapConsent(true);
              }}>
                {hasExactPublicPin(rendezvous)
                  ? (zh ? "打开会合点精确地图…" : "Open exact meeting-place pin…")
                  : (zh ? "按名称查找会合点（需核对）…" : "Search for meeting place (verify result)…")}
              </button>
              {groupPresence?.can_guide && onRefreshLocation && (
                <button
                  type="button"
                  data-testid="journey-membership-route-check"
                  disabled={navigationBusy}
                  onClick={requestRouteConsent}
                >{zh ? "检查我到下一处会合点的路线…" : "Check my route to our next stop…"}</button>
              )}
              {groupPresence?.can_guide && (
                <section data-testid="journey-rendezvous-coordination">
                  <strong>{zh ? "为这个共同会合点协调" : "Coordinate around this shared stop"}</strong>
                  <small>
                    {zh
                      ? "路线检查与状态分享分开；确认后，同行者会看到你的到达报告。"
                      : "Route checks and status sharing are separate. Confirm to share your arrival report with companions."}
                  </small>
                  <div className="journey-membership-actions">
                    <button
                      type="button"
                      data-testid="journey-rendezvous-heading-share"
                      disabled={coordinationBusy}
                      onClick={() => openCoordinationConsent("HEADING_TO_RENDEZVOUS")}
                    >{zh ? "告诉同行者我正在赶往会合点" : "Tell companions I'm on my way"}</button>
                    <button
                      type="button"
                      data-testid="journey-rendezvous-help-share"
                      disabled={coordinationBusy}
                      onClick={() => openCoordinationConsent("NEEDS_COORDINATION")}
                    >{zh ? "我需要帮助协调" : "I need help coordinating"}</button>
                    <button
                      type="button"
                      data-testid="journey-rendezvous-refresh"
                      disabled={coordinationBusy}
                      onClick={() => void refreshGroupPresence()}
                    >{zh ? "刷新团队状态" : "Refresh team status"}</button>
                  </div>
                  {coordinationSignals.length > 0 ? (
                    <div data-testid="journey-rendezvous-status-list">
                      {coordinationSignals.map((signal) => (
                        <article key={signal.signal_id} data-testid="journey-rendezvous-status" data-signal-id={signal.signal_id}>
                          <strong>{coordinationStatusLabel(signal, zh)}</strong>
                          <small>
                            {zh
                              ? `会合点：${signal.public_place_name}。自报时间：${new Date(signal.reported_at).toLocaleString(locale)}。有效至：${new Date(signal.expires_at).toLocaleString(locale)}。`
                              : `Stop: ${signal.public_place_name}. Self-reported ${new Date(signal.reported_at).toLocaleString(locale)}; expires ${new Date(signal.expires_at).toLocaleString(locale)}.`}
                          </small>
                          <small>{zh ? "接应意向 · 由成员主动发起" : "Help request · shared by this member"}</small>
                          {signal.acknowledgement && (
                            <small data-testid="journey-rendezvous-help-acknowledgement">
                              {zh
                                ? `${signal.acknowledgement.display_name} 已回应这次求助。`
                                : `${signal.acknowledgement.display_name} acknowledged this request.`}
                            </small>
                          )}
                          {signal.signal_kind === "NEEDS_COORDINATION"
                            && signal.viewer_is_acknowledger
                            && signal.acknowledgement
                            && !buddyHandoffs.some((handoff) => handoff.help_signal_id === signal.signal_id)
                            && (
                              <button
                                type="button"
                                data-testid="journey-buddy-load-candidates"
                                disabled={buddyActionBusy}
                                onClick={() => void loadBuddyHandoffCandidates(signal)}
                              >{zh ? "提议一个公开接应地点" : "Offer a public meeting point"}</button>
                            )}
                          {buddyCandidates?.help_signal_id === signal.signal_id && (
                            <section data-testid="journey-buddy-candidate-chooser">
                              <strong>{zh ? "选择一个双方可见的公共地点" : "Choose a public place for this private offer"}</strong>
                              <p>{zh
                                ? "地点来自当前会合点或服务器目录 · 显示直线距离 · 营业、无障碍与路线信息待补充。"
                                : "Places come from the current stop or server catalog. Distance is shown as a straight line; opening hours, accessibility, and reachability are unavailable. Review the place before travelling."}</p>
                              <label htmlFor="journey-buddy-candidate-select">{zh ? "接应地点" : "Public handoff place"}</label>
                              <select
                                id="journey-buddy-candidate-select"
                                data-testid="journey-buddy-candidate-select"
                                value={buddySelectedPlaceId}
                                onChange={(event) => setBuddySelectedPlaceId(event.target.value)}
                              >
                                {buddyCandidates.items.map((place) => (
                                  <option key={place.place_id} value={place.place_id}>
                                    {place.name} · {place.distance_from_original_m} m straight-line · {place.source_label}
                                  </option>
                                ))}
                              </select>
                              {buddyCandidates.items.find((place) => place.place_id === buddySelectedPlaceId) && (
                                <small data-testid="journey-buddy-candidate-provenance">
                                  {buddyCandidates.items.find((place) => place.place_id === buddySelectedPlaceId)?.source_label}
                                  {zh ? "；路线、开放时间和无障碍状态均未知。" : "; route, opening hours, and accessibility are UNKNOWN."}
                                </small>
                              )}
                              <label htmlFor="journey-buddy-execution-window">
                                {zh ? "双方同意后的接应执行时长" : "Bounded assist window after both accept"}
                              </label>
                              <select
                                id="journey-buddy-execution-window"
                                data-testid="journey-buddy-execution-window"
                                value={buddyExecutionWindowMinutes}
                                onChange={(event) => setBuddyExecutionWindowMinutes(Number(event.target.value) as 30 | 60 | 90)}
                              >
                                {[30, 60, 90].map((minutes) => (
                                  <option key={minutes} value={minutes}>{minutes} minutes</option>
                                ))}
                              </select>
                              <small>
                                {zh
                                  ? "提议须在 20 分钟内接受；接应窗口由求助者确认后开始。"
                                  : "Accept the offer within 20 minutes. The assist window starts after the requester accepts."}
                              </small>
                              <div className="journey-membership-actions">
                                <button
                                  type="button"
                                  data-testid="journey-buddy-offer"
                                  disabled={buddyActionBusy || !buddySelectedPlaceId}
                                  onClick={() => void offerBuddyHandoff()}
                                >{zh ? "向求助者发送此地点" : "Offer this place to the requester"}</button>
                                <button
                                  type="button"
                                  data-testid="journey-buddy-candidate-cancel"
                                  disabled={buddyActionBusy}
                                  onClick={() => {
                                    setBuddyCandidates(null);
                                    setBuddySelectedPlaceId("");
                                  }}
                                >{zh ? "取消" : "Cancel"}</button>
                              </div>
                            </section>
                          )}
                          {signal.viewer_can_acknowledge && (
                            <button
                              type="button"
                              data-testid="journey-rendezvous-help-acknowledge"
                              disabled={coordinationBusy}
                              onClick={() => void acknowledgeCoordinationHelp(signal)}
                            >{zh ? "我可以帮忙协调" : "I can help coordinate"}</button>
                          )}
                          {signal.viewer_can_withdraw && (
                            <button
                              type="button"
                              data-testid="journey-rendezvous-withdraw"
                              disabled={coordinationBusy}
                              onClick={() => void withdrawCoordinationSignal()}
                            >{zh ? "停止分享此状态" : "Stop sharing this status"}</button>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <small data-testid="journey-rendezvous-no-status">
                      {zh ? "目前没有同行者主动分享此会合点状态。" : "No companion has voluntarily shared a status for this stop."}
                    </small>
                  )}
                  {buddyHandoffs.length > 0 && (
                    <div data-testid="journey-buddy-handoffs">
                      {buddyHandoffs.map((handoff) => {
                        const privateRoute = buddyPrivateRoutes[handoff.handoff_id];
                        const outboundLeg = privateRoute?.outbound_leg ?? null;
                        const returnLeg = privateRoute?.return_leg ?? null;
                        const legHasUsableEvidence = (leg: typeof outboundLeg) => Boolean(
                          leg
                          && (leg.route_state === "LIVE" || leg.route_state === "REPLAY")
                          && typeof leg.duration_min === "number"
                          && Number.isFinite(leg.duration_min)
                          && leg.duration_min >= 0
                          && leg.provider
                          && leg.provenance,
                        );
                        const topLevelRouteUsable = privateRoute?.route_state === "LIVE" || privateRoute?.route_state === "REPLAY";
                        const handoffIsOriginalSharedStop =
                          handoff.handoff_place.place_id === handoff.original_shared_stop.place_id;
                        // The exact original shared stop needs NO separate second leg.
                        // R81 marks that leg SAME_PUBLIC_DESTINATION with 0 minutes;
                        // don't hide a valid caller-private outbound ETA in this case.
                        const returnSatisfied = handoffIsOriginalSharedStop
                          ? returnLeg?.route_state === "SAME_PUBLIC_DESTINATION" && returnLeg.duration_min === 0
                          : legHasUsableEvidence(returnLeg);
                        const hasBothUsableBuddyLegs = legHasUsableEvidence(outboundLeg)
                          && returnSatisfied
                          && topLevelRouteUsable;
                        const routeIsStale = privateRoute?.status === "STALE" || privateRoute?.route_state === "STALE";
                        const displayedRouteState = hasBothUsableBuddyLegs
                          ? privateRoute?.route_state ?? "UNKNOWN"
                          : routeIsStale
                            ? "STALE"
                            : privateRoute?.route_state === "TEST_PROVIDER_EMULATOR"
                              ? "TEST_PROVIDER_EMULATOR"
                              : "UNKNOWN";
                        const risk = privateRoute?.shared_commitment_risk;
                        const oneRiskLeg = risk?.legs_used?.length === 1 ? risk.legs_used[0] : null;
                        const oneRiskLegIsLive = oneRiskLeg === "TO_HANDOFF"
                          ? outboundLeg?.route_state === "LIVE" && legHasUsableEvidence(outboundLeg)
                          : oneRiskLeg === "RETURN_TO_SHARED_STOP"
                            ? returnLeg?.route_state === "LIVE" && legHasUsableEvidence(returnLeg)
                            : false;
                        const oneVerifiedLegAloneAtRisk = risk?.state === "COMMITMENT_AT_RISK"
                          && risk.basis === "ONE_VERIFIED_ROUTE_LEG_ALONE_EXCEEDS_PROTECTED_COMMITMENT"
                          && oneRiskLegIsLive;
                        const displayedCommitmentRisk = hasBothUsableBuddyLegs
                          ? risk?.state ?? "UNKNOWN"
                          : oneVerifiedLegAloneAtRisk ? "COMMITMENT_AT_RISK" : "UNKNOWN";
                        const execution = handoff.execution ?? null;
                        const returnDirectionsButton = execution?.can_return_to_shared_stop ? (
                          <button
                            type="button"
                            data-testid="journey-buddy-return-open"
                            disabled={buddyActionBusy || !currentTargetKey}
                            onClick={() => beginBuddyReturnDirectionsConsent(handoff)}
                          >{zh ? "单独同意后导航回当前共同会合点…" : "Navigate back to the current shared stop with separate consent…"}</button>
                        ) : null;
                        return (
                        <article key={handoff.handoff_id} data-testid="journey-buddy-handoff" data-handoff-id={handoff.handoff_id}>
                          <strong>{handoff.status === "ACCEPTED"
                            ? (zh ? "双方已接受公开接应意向" : "Mutually accepted public handoff intention")
                            : (zh ? "收到一处公开接应地点提议" : "Public handoff place offered")}</strong>
                          <p>{handoff.helper_display_name} → {handoff.requester_display_name}: {handoff.handoff_place.name}</p>
                          <small>{zh
                            ? `${handoff.handoff_place.source_label} · 距原会合点直线 ${handoff.handoff_place.distance_from_original_m} 米。`
                            : `${handoff.handoff_place.source_label} · ${handoff.handoff_place.distance_from_original_m} m straight-line from the original stop.`}</small>
                          <small>{zh
                            ? `提议有效至 ${new Date(handoff.expires_at).toLocaleString(locale)}。路线、营业和无障碍信息待补充；原会合点：${handoff.original_shared_stop.place_name}。`
                            : `Offer expires ${new Date(handoff.expires_at).toLocaleString(locale)}. Route, opening and accessibility details pending · original stop: ${handoff.original_shared_stop.place_name}.`}</small>
                          {execution?.status === "ACTIVE" && execution.context_current && (
                            <small data-testid="journey-buddy-active-lease-truth">
                              {zh
                                ? `提议接受截止：${new Date(handoff.expires_at).toLocaleString(locale)}；接应窗口截止：${execution.expires_at ? new Date(execution.expires_at).toLocaleString(locale) : "未知"}。`
                                : `Offer acceptance deadline: ${new Date(handoff.expires_at).toLocaleString(locale)}. Assist window ends: ${execution.expires_at ? new Date(execution.expires_at).toLocaleString(locale) : "unknown"}.`}
                            </small>
                          )}
                          {handoff.status === "OFFERED" && execution?.status === "WINDOW_OFFERED" && (
                            <small data-testid="journey-buddy-window-offer-truth">
                              {zh
                                ? `接受该地点即同意 ${execution.execution_window_minutes} 分钟接应窗口；由你确认后开始。`
                                : `Accepting this place agrees to a ${execution.execution_window_minutes}-minute assist window, started by your confirmation.`}
                            </small>
                          )}
                          {handoff.status === "OFFERED" && handoff.viewer_role === "REQUESTER" && (
                            <div className="journey-membership-actions">
                              <button type="button" data-testid="journey-buddy-accept" disabled={buddyActionBusy}
                                onClick={() => void respondToBuddyHandoff(handoff, "ACCEPT")}>
                                {execution?.status === "WINDOW_OFFERED"
                                  ? (zh
                                    ? `接受地点与 ${execution.execution_window_minutes} 分钟执行窗口`
                                    : `Accept place and ${execution.execution_window_minutes}-minute window`)
                                  : (zh ? "接受此接应地点" : "Accept this handoff place")}
                              </button>
                              <button type="button" data-testid="journey-buddy-decline" disabled={buddyActionBusy}
                                onClick={() => void respondToBuddyHandoff(handoff, "DECLINE")}>
                                {zh ? "拒绝" : "Decline"}
                              </button>
                            </div>
                          )}
                          {handoff.status === "ACCEPTED" && (
                            <>
                              <small data-testid="journey-buddy-accepted-truth">
                                {zh ? "双方已同意公共会合点；各自决定是否导航。" : "Both travellers agreed on the public meeting point. Each chooses whether to navigate."}
                              </small>
                              {execution?.status === "WINDOW_OFFERED" && handoff.viewer_role === "REQUESTER" && execution.can_accept_window && (
                                <section data-testid="journey-buddy-window-acceptance">
                                  <p>{zh
                                    ? `对方单独同意了 ${execution.execution_window_minutes} 分钟执行窗口。提议仍受原 20 分钟接受期限约束；由你签名接受后才开始计时。`
                                    : `The helper separately offered a ${execution.execution_window_minutes}-minute execution window. The proposal remains subject to the original 20-minute deadline; its clock starts only when you sign to accept.`}</p>
                                  <button
                                    type="button"
                                    data-testid="journey-buddy-execution-window-accept"
                                    disabled={buddyActionBusy}
                                    onClick={() => void acceptBuddyExecutionWindow(handoff)}
                                  >{zh ? `接受 ${execution.execution_window_minutes} 分钟执行窗口` : `Accept ${execution.execution_window_minutes}-minute window`}</button>
                                </section>
                              )}
                              {handoff.execution_window_offer_available && handoff.viewer_role === "HELPER" && (
                                <section data-testid="journey-buddy-window-upgrade">
                                  <p>{zh
                                    ? "接应按旧版本接受；延长执行窗口需重新同意。"
                                    : "Earlier agreement accepted. Offer a new execution window."}</p>
                                  <label htmlFor={`journey-buddy-upgrade-window-${handoff.handoff_id}`}>
                                    {zh ? "提议执行时长" : "Proposed execution window"}
                                  </label>
                                  <select
                                    id={`journey-buddy-upgrade-window-${handoff.handoff_id}`}
                                    data-testid="journey-buddy-upgrade-window-select"
                                    value={buddyExecutionWindowMinutes}
                                    onChange={(event) => setBuddyExecutionWindowMinutes(Number(event.target.value) as 30 | 60 | 90)}
                                  >
                                    {[30, 60, 90].map((minutes) => (
                                      <option key={minutes} value={minutes}>{minutes} minutes</option>
                                    ))}
                                  </select>
                                  <button
                                    type="button"
                                    data-testid="journey-buddy-execution-window-offer"
                                    disabled={buddyActionBusy}
                                    onClick={() => void offerBuddyExecutionWindow(handoff, buddyExecutionWindowMinutes)}
                                  >{zh ? "单独提议此执行时长" : "Offer this bounded window separately"}</button>
                                </section>
                              )}
                              {execution?.status === "WINDOW_OFFERED" && handoff.viewer_role === "HELPER" && handoff.status === "ACCEPTED" && (
                                <small data-testid="journey-buddy-window-waiting">
                                  {zh ? `已提出 ${execution.execution_window_minutes} 分钟窗口，等待求助者签名接受。` : `A ${execution.execution_window_minutes}-minute window is offered; awaiting the requester's signed acceptance.`}
                                </small>
                              )}
                              {execution?.status === "ACTIVE" && (
                                <section data-testid="journey-buddy-execution-active">
                                  <strong>{zh ? "双方同意的接应正在执行" : "Mutually agreed buddy assist in progress"}</strong>
                                  <small>{zh
                                    ? `接应窗口 ${execution.execution_window_minutes} 分钟；开始 ${execution.started_at ? new Date(execution.started_at).toLocaleString(locale) : "—"}；截止 ${execution.expires_at ? new Date(execution.expires_at).toLocaleString(locale) : "—"}。`
                                    : `Assist window: ${execution.execution_window_minutes} minutes; started ${execution.started_at ? new Date(execution.started_at).toLocaleString(locale) : "—"}; ends ${execution.expires_at ? new Date(execution.expires_at).toLocaleString(locale) : "—"}.`}</small>
                                  <small data-testid="journey-buddy-execution-confirmations">
                                    {execution.helper_confirmed
                                      ? (zh ? `${handoff.helper_display_name} 已本人确认。` : `${handoff.helper_display_name} confirmed personally.`)
                                      : (zh ? `${handoff.helper_display_name} 尚未确认。` : `${handoff.helper_display_name} has not confirmed.`)}
                                    {" "}
                                    {execution.requester_confirmed
                                      ? (zh ? `${handoff.requester_display_name} 已本人确认。` : `${handoff.requester_display_name} confirmed personally.`)
                                      : (zh ? `${handoff.requester_display_name} 尚未确认。` : `${handoff.requester_display_name} has not confirmed.`)}
                                    {execution.viewer_receipt_kind === "BUDDY_MET_ACK" && !execution.partner_receipt_kind
                                      ? (zh ? "等待对方独立确认。" : "Waiting for the other member’s independent confirmation.")
                                      : ""}
                                  </small>
                                  <small>{zh
                                    ? "下方按钮记录你本人的到达确认。"
                                    : "Use the buttons below to confirm your arrival."}</small>
                                  {execution.can_report && (
                                    <div className="journey-membership-actions">
                                      <button
                                        type="button"
                                        data-testid="journey-buddy-met-ack"
                                        disabled={buddyActionBusy}
                                        onClick={() => void reportBuddyExecution(handoff, execution, "BUDDY_MET_ACK")}
                                      >{zh ? "我在约定地点看到伙伴，确认接应协作完成" : "I am at the agreed place and can see my buddy"}</button>
                                      <button
                                        type="button"
                                        data-testid="journey-buddy-cannot-meet"
                                        disabled={buddyActionBusy}
                                        onClick={() => void reportBuddyExecution(handoff, execution, "CANNOT_MEET")}
                                      >{zh ? "我无法在这里接应，需要重新协调" : "I cannot meet here; I need to replan"}</button>
                                      <button
                                        type="button"
                                        data-testid="journey-buddy-cancel-participation"
                                        disabled={buddyActionBusy}
                                        onClick={() => void reportBuddyExecution(handoff, execution, "CANCEL_PARTICIPATION")}
                                      >{zh ? "退出我自己的接应参与" : "Cancel my participation"}</button>
                                    </div>
                                  )}
                                </section>
                              )}
                              {execution?.status === "MUTUALLY_ACKNOWLEDGED" && (
                                <section data-testid="journey-buddy-mutual-outcome">
                                  <strong>{zh ? "双方已独立确认接应协作完成" : "Both members independently confirmed the assist"}</strong>
                                  <small>{zh
                                    ? "双方已签名确认接应完成。共享行程按原计划继续。"
                                    : "Both members confirmed the assist. The shared Journey continues as planned."}</small>
                                  {returnDirectionsButton}
                                </section>
                              )}
                              {execution?.status === "REPLAN_REQUIRED" && (
                                <section data-testid="journey-buddy-replan-required">
                                  <strong>{zh ? "此接应无法按原约定完成" : "This handoff cannot finish as agreed"}</strong>
                                  <small>{zh ? "接应未完成。可发起新请求或导航回当前会合点。" : "Assist incomplete. Create a new request or navigate to the current meetup."}</small>
                                  <button type="button" data-testid="journey-buddy-replan-help" disabled={coordinationBusy}
                                    onClick={() => openCoordinationConsent("NEEDS_COORDINATION")}>
                                    {zh ? "请求重新协调帮助…" : "Request fresh help…"}
                                  </button>
                                  {returnDirectionsButton}
                                </section>
                              )}
                              {execution?.status === "CANCELLED" && (
                                <section data-testid="journey-buddy-execution-cancelled">
                                  <small>{zh ? "一位成员已退出，等待另一位成员确认。" : "One member left; awaiting the other member's confirmation."}</small>
                                  {returnDirectionsButton}
                                </section>
                              )}
                              {execution?.status === "EXPIRED" && (
                                <section data-testid="journey-buddy-execution-expired">
                                  <small>{zh ? "接应窗口已过期，需重新同意后继续。" : "Assist window expired. Renew consent to continue."}</small>
                                  <button type="button" data-testid="journey-buddy-replan-help" disabled={coordinationBusy}
                                    onClick={() => openCoordinationConsent("NEEDS_COORDINATION")}>
                                    {zh ? "重新协调帮助…" : "Replan help…"}
                                  </button>
                                  {returnDirectionsButton}
                                </section>
                              )}
                              {execution?.status === "STALE" && (
                                <section data-testid="journey-buddy-execution-stale">
                                  <small>{zh ? `原接应上下文已暂停（${execution.stale_reason ?? "需要重新核对"}）；刷新当前计划并重新取得双方同意。` : `The original handoff context is paused (${execution.stale_reason ?? "revalidation required"}); refresh the current plan and obtain consent again.`}</small>
                                  <button type="button" data-testid="journey-buddy-replan-help" disabled={coordinationBusy}
                                    onClick={() => openCoordinationConsent("NEEDS_COORDINATION")}>
                                    {zh ? "按当前计划重新协调帮助…" : "Request fresh help for the current plan…"}
                                  </button>
                                </section>
                              )}
                              <button type="button" data-testid="journey-buddy-map-open"
                                disabled={buddyActionBusy || !buddyHandoffCanNavigate(handoff)}
                                onClick={() => setBuddyMapConsentId(handoff.handoff_id)}>
                                {zh ? "打开接应地点精确地图…" : "Open exact handoff map pin…"}
                              </button>
                              <button
                                type="button"
                                data-testid="journey-buddy-directions-open"
                                disabled={buddyActionBusy || !buddyHandoffCanNavigate(handoff) || !currentTargetKey || !currentAudienceKey}
                                onClick={() => beginBuddyDirectionsConsent(handoff)}
                              >{zh ? "单独同意后打开外部步行导航…" : "Open external walking directions with separate consent…"}</button>
                              {onRefreshLocation && (
                                <button
                                  type="button"
                                  data-testid="journey-buddy-route-start"
                                  disabled={buddyActionBusy || buddyRouteBusy || !buddyHandoffCanNavigate(handoff)}
                                  onClick={() => beginBuddyRouteCheck(handoff)}
                                >{zh ? "检查我到这处接应点的步行路线…" : "Check MY walking route to this handoff…"}</button>
                              )}
                              {privateRoute && (
                                <article
                                  data-testid="journey-buddy-route-result"
                                  data-route-state={displayedRouteState}
                                  data-handoff-id={handoff.handoff_id}
                                >
                                  <strong>{displayedRouteState === "LIVE"
                                    ? (zh ? "当前路线服务结果（仅你可见）" : "Current route-provider result (only you can see it)")
                                    : displayedRouteState === "REPLAY"
                                        ? (zh ? "历史路线回放" : "Historical route replay")
                                      : displayedRouteState === "STALE"
                                        ? (zh ? "路线上下文已过期；没有可用预计时间" : "Route context is stale; no actionable estimate")
                                      : displayedRouteState === "TEST_PROVIDER_EMULATOR"
                                        ? (zh ? "测试路线服务结果" : "Test route-provider result")
                                      : (zh ? "路线状态：UNKNOWN / ROUTE_UNAVAILABLE" : "Route status: UNKNOWN / ROUTE_UNAVAILABLE")}</strong>
                                  <p>{zh
                                    ? `目的地：${privateRoute.target_place_name}（${privateRoute.target_source_label}）。全体会合点：${privateRoute.original_shared_stop_name}。`
                                    : `Destination: ${privateRoute.target_place_name} (${privateRoute.target_source_label}). Group meeting point: ${privateRoute.original_shared_stop_name}.`}</p>
                                  <div data-testid="journey-buddy-route-legs">
                                    {([
                                      ["outbound", outboundLeg, zh ? "本人到接应点" : "Your origin to the handoff"],
                                      ["return", returnLeg, zh ? "接应点回原共同会合点" : "Handoff to the original shared stop"],
                                    ] as const).map(([legKey, leg, label]) => (
                                      <section
                                        key={legKey}
                                        data-testid="journey-buddy-route-leg"
                                        data-leg={legKey}
                                        data-route-state={leg?.route_state ?? "UNKNOWN"}
                                      >
                                        <strong>{label}: {leg?.route_state ?? "UNKNOWN"}</strong>
                                        <small>
                                          {leg?.provider ?? (zh ? "路线服务未配置或未提供" : "provider unavailable")}
                                          {" · "}{leg?.provenance ?? (zh ? "没有独立路线证据" : "no separate leg evidence")}
                                          {leg?.reason ? ` · ${leg.reason}` : ""}
                                        </small>
                                        {leg?.route_state === "TEST_PROVIDER_EMULATOR" ? (
                                          <small>{zh ? `测试服务时长：${leg.duration_min ?? "未知"} 分钟。` : `Test service duration: ${leg.duration_min ?? "unknown"} min.`}</small>
                                        ) : leg?.duration_min !== null && leg?.duration_min !== undefined
                                          && (leg.route_state === "LIVE" || leg.route_state === "REPLAY") ? (
                                            <small>{zh ? `本段约 ${leg.duration_min} 分钟。` : `Leg estimate: about ${leg.duration_min} minutes.`}</small>
                                          ) : (
                                            <small>{zh ? "本段时长未知。" : "Duration unavailable."}</small>
                                          )}
                                      </section>
                                    ))}
                                  </div>
                                  {privateRoute.duration_min !== null && hasBothUsableBuddyLegs && displayedRouteState !== "UNKNOWN" ? (
                                    <small>{handoffIsOriginalSharedStop
                                      ? (zh
                                        ? `接应点就是原共同会合点，本人步行约 ${privateRoute.duration_min} 分钟，无需第二段路线。`
                                        : `The handoff is already the original shared stop. Your walking estimate is about ${privateRoute.duration_min} minutes; no second leg is required.`)
                                      : (zh
                                        ? `两段移动时间合计约 ${privateRoute.duration_min} 分钟（不含接应停留时间）。`
                                        : `Both travel legs total about ${privateRoute.duration_min} minutes (excluding time spent at the handoff).`)}</small>
                                  ) : (
                                    <small>{zh ? "两段路线未全部得到可用证据；总时间与承诺安全余量保持 UNKNOWN。可单独同意打开外部目的地导航。" : "Both legs lack usable evidence; total time and commitment slack remain UNKNOWN. You may separately consent to external destination-only directions."}</small>
                                  )}
                                  <small>
                                    {zh ? "来源：" : "Source: "}{privateRoute.provider ?? (zh ? "未配置" : "not configured")}
                                    {" · "}{zh ? "证据：" : "Evidence: "}{privateRoute.provenance}
                                    {privateRoute.captured_at && (
                                      <>{" · "}{zh ? "回执时间：" : "Receipt time: "}{new Date(privateRoute.captured_at).toLocaleString(locale)}</>
                                    )}
                                    {privateRoute.origin_age_seconds !== null && (
                                      <>{" · "}{zh ? "本人的位置观察年龄：" : "your observation age: "}{privateRoute.origin_age_seconds}s</>
                                    )}
                                  </small>
                                  <small>{zh ? "受保护承诺风险：" : "Protected-commitment risk: "}{displayedCommitmentRisk}
                                    {displayedCommitmentRisk === "UNKNOWN" && handoff.handoff_place.place_id !== handoff.original_shared_stop.place_id
                                      && returnLeg?.route_state !== "LIVE"
                                      ? (zh ? "；接应点到共同会合点的路线资料缺失，无法计算安全余量。" : "; route data to the shared rendezvous is missing, so the safety buffer cannot be calculated.")
                                      : ""}</small>
                                  {risk?.basis === "TWO_LEG_TRAVEL_ONLY_HANDOFF_DWELL_UNKNOWN" && (
                                    <small data-testid="journey-buddy-dwell-unknown">
                                      {zh
                                        ? "路线时间不含接应和等待，返程请预留缓冲。"
                                        : "Route time excludes handoff and waiting; leave a return buffer."}
                                    </small>
                                  )}
                                  {displayedCommitmentRisk === "COMMITMENT_AT_RISK" && (
                                    <strong role="alert" data-testid="journey-buddy-route-commitment-warning">
                                      {oneVerifiedLegAloneAtRisk
                                        ? (zh
                                          ? "一段已验证路线显示可能错过受保护安排。返回原会合点，或请求团队恢复。"
                                          : "One verified route leg alone exceeds the protected commitment. Return to the original shared stop or request group recovery.")
                                        : (zh
                                          ? "两段路线显示可能错过受保护安排。返回原会合点，或请求团队恢复。"
                                          : "The two legs indicate that you may miss the protected commitment. Return to the original shared stop or request group recovery.")}
                                    </strong>
                                  )}
                                  <small>{zh
                                    ? "路线与精确起点仅本人可见；此结果用于路线风险评估。到达状态由你确认。"
                                    : "Your route and precise origin are visible only to you."}</small>
                                </article>
                              )}
                            </>
                          )}
                          {(!execution || execution.status === "WINDOW_OFFERED") && (
                            <button type="button" data-testid="journey-buddy-close" disabled={buddyActionBusy}
                              onClick={() => void closeBuddyHandoff(handoff)}>
                              {handoff.viewer_role === "HELPER"
                                ? (zh ? "取消接应提议" : "Cancel handoff")
                                : (zh ? "撤回我的接应同意" : "Revoke my handoff agreement")}
                            </button>
                          )}
                        </article>
                        );
                      })}
                    </div>
                  )}
                  {coordinationMessage && (
                    <small role="status" data-testid="journey-rendezvous-message">{coordinationMessage}</small>
                  )}
                  {buddyMessage && <small role="status" data-testid="journey-buddy-message">{buddyMessage}</small>}
                  {buddyRouteMessage && <small role="status" data-testid="journey-buddy-route-message">{buddyRouteMessage}</small>}
                  {coordinationConsentKind && (
                    <section
                      role="dialog"
                      aria-modal="true"
                      aria-labelledby="journey-rendezvous-consent-title"
                      data-testid="journey-rendezvous-consent"
                    >
                      <strong id="journey-rendezvous-consent-title">
                        {coordinationConsentKind === "HEADING_TO_RENDEZVOUS"
                          ? (zh ? "确认分享正在前往的自报状态？" : "Confirm sharing your self-reported intention?")
                          : (zh ? "确认向同行者请求协调帮助？" : "Confirm asking companions for coordination help?")}
                      </strong>
                      <p>
                        {zh
                          ? `可见同行者：${groupPresence.members.filter((item) => !item.is_viewer).map((item) => item.display_name).join("、")}。分享会合点“${rendezvous.place_name}”和你的自报状态，有效期 45 分钟。`
                          : `Visible to: ${groupPresence.members.filter((item) => !item.is_viewer).map((item) => item.display_name).join(", ")}. Shares your status at “${rendezvous.place_name}” for 45 minutes.`}
                      </p>
                      <p>
                        {zh
                          ? "只分享自报状态和公开会合点；精确位置与个人路线仅你可见。"
                          : "Shares your self-reported status and the public rendezvous; your exact location and private route are visible only to you."}
                      </p>
                      <div className="journey-membership-actions">
                        <button
                          type="button"
                          data-testid="journey-rendezvous-consent-confirm"
                          disabled={coordinationBusy || coordinationConsentKey !== currentTargetKey || coordinationConsentAudienceKey !== currentAudienceKey}
                          onClick={() => void shareCoordinationSignal()}
                        >{coordinationConsentKind === "HEADING_TO_RENDEZVOUS"
                          ? (zh ? "确认分享我正在前往" : "Share that I'm on my way")
                          : (zh ? "确认请求帮助" : "Share my help request")}</button>
                        <button
                          type="button"
                          disabled={coordinationBusy}
                          onClick={() => {
                            setCoordinationConsentKind(null);
                            setCoordinationConsentKey(null);
                            setCoordinationConsentAudienceKey(null);
                          }}
                        >{zh ? "取消" : "Cancel"}</button>
                      </div>
                    </section>
                  )}
                </section>
              )}
            </>
          ) : (
            <small>{zh ? "暂时没有可确认的共同会合点。" : "No shared rendezvous is available."}</small>
          )}
        </div>
      )}

      {mapConsent && rendezvous && (
        <section className="journey-membership-map-consent" role="dialog" aria-modal="true" aria-labelledby="journey-membership-map-title" data-testid="journey-membership-map-consent">
          <strong id="journey-membership-map-title">{zh ? "打开公开会合点地图？" : "Open a public map of the rendezvous?"}</strong>
          <p>{hasExactPublicPin(rendezvous)
            ? (zh
            ? `OpenStreetMap 将接收公共地点“${rendezvous.place_name}”的坐标并显示地图标点。`
              : `OpenStreetMap will receive the public Place coordinates for the map pin.`)
            : (zh
              ? `OpenStreetMap 将按公开地点名称“${rendezvous.place_name}”搜索；结果可能有多个。`
              : `OpenStreetMap will search the public Place name “${rendezvous.place_name}”; results may vary.`)}</p>
          <div className="journey-membership-actions">
            <button type="button" data-testid="journey-membership-map-confirm" onClick={() => void openPublicMap()} disabled={navigationBusy}>
              {zh ? "同意并打开地图" : "Agree and open map"}
            </button>
            <button type="button" onClick={() => {
              setMapConsent(false);
              setMapConsentKey(null);
            }}>{zh ? "取消" : "Cancel"}</button>
          </div>
        </section>
      )}

      {buddyMapConsentHandoff && (
        <section
          className="journey-membership-map-consent"
          role="dialog"
          aria-modal="true"
          aria-labelledby="journey-buddy-map-title"
          data-testid="journey-buddy-map-consent"
        >
          <strong id="journey-buddy-map-title">{zh ? "打开双方同意的接应地点？" : "Open the mutually accepted handoff place?"}</strong>
          <p>{zh
            ? `确认后将公开地点“${buddyMapConsentHandoff.handoff_place.name}”的坐标发送至 OpenStreetMap。`
            : `Confirm to send the public Place “${buddyMapConsentHandoff.handoff_place.name}” coordinates to OpenStreetMap.`}</p>
          <p>{zh
            ? "地图显示所选公共会合点。"
            : "The map opens at this public meeting place."}</p>
          <div className="journey-membership-actions">
            <button type="button" data-testid="journey-buddy-map-confirm" onClick={() => void openAcceptedBuddyMap()} disabled={buddyActionBusy}>
              {zh ? "同意并打开地图" : "Agree and open map"}
            </button>
            <button type="button" data-testid="journey-buddy-map-cancel" onClick={() => setBuddyMapConsentId(null)} disabled={buddyActionBusy}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}

      {buddyDirectionsConsent && (
        <section
          className="journey-membership-map-consent"
          role="dialog"
          aria-modal="true"
          aria-labelledby="journey-buddy-directions-title"
          data-testid="journey-buddy-directions-consent"
        >
          <strong id="journey-buddy-directions-title">
            {zh ? "把双方同意的接应目的地交给外部步行导航？" : "Send the mutually agreed handoff destination to an external walking map?"}
          </strong>
          <p>{zh
            ? `仅将公开地点“${buddyDirectionsConsent.handoff.handoff_place.name}”的坐标发送给 Google Maps；设备定位由 Google Maps 的权限设置管理。`
            : `Google Maps receives the public Place “${buddyDirectionsConsent.handoff.handoff_place.name}” pin. Device location follows Google Maps permissions.`}</p>
          <p>{zh
            ? "打开地图后，可自行返回行程更新会合状态。地图不可用时，可选择静态地点标点。"
            : "Return to the Journey to update meetup status."}</p>
          <div className="journey-membership-actions">
            <button type="button" data-testid="journey-buddy-directions-confirm" onClick={() => void openAcceptedBuddyDirections()} disabled={buddyActionBusy}>
              {zh ? "同意并打开步行导航" : "Agree and open walking directions"}
            </button>
            <button type="button" data-testid="journey-buddy-directions-cancel" onClick={() => setBuddyDirectionsConsent(null)} disabled={buddyActionBusy}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}

      {buddyReturnDirectionsConsent && (
        <section
          className="journey-membership-map-consent"
          role="dialog"
          aria-modal="true"
          aria-labelledby="journey-buddy-return-directions-title"
          data-testid="journey-buddy-return-directions-consent"
        >
          <strong id="journey-buddy-return-directions-title">
            {zh ? "导航回当前共同会合点？" : "Navigate back to the current shared stop?"}
          </strong>
          <p>{zh
            ? `将共同会合点“${buddyReturnDirectionsConsent.sharedStopName}”的坐标发送给 Google Maps；设备定位由其权限设置管理。`
            : `Google Maps receives the shared stop “${buddyReturnDirectionsConsent.sharedStopName}” pin. Device location follows Google Maps permissions.`}</p>
          <p>{zh
            ? "计划或会合点变化时，请重新确认后再打开导航。"
            : "If the plan or meeting place changes, confirm again before opening directions."}</p>
          <div className="journey-membership-actions">
            <button type="button" data-testid="journey-buddy-return-directions-confirm" onClick={() => void openBuddyReturnDirections()} disabled={buddyActionBusy}>
              {zh ? "单独同意并导航回共同会合点" : "Separately consent and navigate to the shared stop"}
            </button>
            <button type="button" data-testid="journey-buddy-return-directions-cancel" onClick={() => setBuddyReturnDirectionsConsent(null)} disabled={buddyActionBusy}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}

      {buddyRouteConsent && buddyRouteConsentHandoff && (
        <section
          className="journey-membership-map-consent"
          role="dialog"
          aria-modal="true"
          aria-labelledby="journey-buddy-route-title"
          data-testid="journey-buddy-route-consent"
          data-consent-step={buddyRouteConsent.step}
        >
          <strong id="journey-buddy-route-title">
            {buddyRouteConsent.step === "LOCATION"
              ? (zh ? "只为我自己记录一次前台位置？" : "Record one foreground location for my route?")
              : (zh ? "单独同意把我的起点发送给路线服务？" : "Separately allow sending my origin to a routing provider?")}
          </strong>
          {buddyRouteConsent.step === "LOCATION" ? (
            <>
              <p>{zh
                ? "读取一次前台位置并保存为本人可见的接应路线输入。确认后再计算路线。"
                : "Read one foreground location and save it as your private handoff-route input. Route calculation follows confirmation."}</p>
              <div className="journey-membership-actions">
                <button type="button" data-testid="journey-buddy-route-location-confirm" onClick={() => void confirmBuddyRouteLocation()} disabled={buddyRouteBusy}>
                  {zh ? "同意并读取一次位置" : "Agree and read location once"}
                </button>
                <button type="button" data-testid="journey-buddy-route-cancel" onClick={cancelBuddyRouteConsent} disabled={buddyRouteBusy && buddyRouteConsent.step !== "LOCATION"}>
                  {zh ? "取消" : "Cancel"}
                </button>
              </div>
            </>
          ) : (
            <>
              <p>{zh
            ? `已保存一次仅本人可见的位置。继续后将精确起点发送至路线服务，计算到「${buddyRouteConsentHandoff.handoff_place.name}」的步行路线。`
                : `One private location is saved. Continuing sends your precise origin to the route provider for walking directions to “${buddyRouteConsentHandoff.handoff_place.name}”.`}</p>
              <p>{zh
            ? `地点来源：${buddyRouteConsentHandoff.handoff_place.source_label}。到原会合点的后续路线待确认。`
                : `Source: ${buddyRouteConsentHandoff.handoff_place.source_label}. Route onward to the original meetup is pending.`}</p>
              <div className="journey-membership-actions">
                <button type="button" data-testid="journey-buddy-route-provider-confirm" onClick={() => void confirmBuddyRouteProviderDisclosure()} disabled={buddyRouteBusy}>
                  {zh ? "单独同意并检查我的步行路线" : "Separately agree and check MY walking route"}
                </button>
                <button type="button" data-testid="journey-buddy-route-cancel" onClick={cancelBuddyRouteConsent} disabled={buddyRouteBusy}>
                  {zh ? "取消" : "Cancel"}
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {routeConsent && rendezvous && (
        <section
          className="journey-membership-map-consent"
          role="dialog"
          aria-modal="true"
          aria-labelledby="journey-membership-route-title"
          data-testid="journey-membership-route-consent"
        >
          <strong id="journey-membership-route-title">
            {zh ? "允许这次前台位置路线检查？" : "Allow this foreground route check?"}
          </strong>
          <p>{zh
            ? `授权后读取并保存一次前台位置，精确起点发送至路线服务，用于路线和队伍概况。风险规则可能触发 Guardian；不使用后台定位。`
            : `Consent reads and saves one foreground location. Your precise origin goes to the route provider for directions and group status. Risk rules may trigger Guardian; no background location is used.`}</p>
          <p>{zh
            ? `目的地是当前共享计划中的公共地点：${rendezvous.place_name}。`
            : `Destination: ${rendezvous.place_name}, a public Place in the current shared plan.`}</p>
          <div className="journey-membership-actions">
            <button
              type="button"
              data-testid="journey-membership-route-confirm"
              onClick={() => void requestPersonalRoute()}
              disabled={navigationBusy}
            >{zh ? "同意并检查路线" : "Agree and check route"}</button>
            <button
              type="button"
              data-testid="journey-membership-route-cancel"
              onClick={() => {
                setRouteConsent(false);
                setRouteConsentKey(null);
              }}
              disabled={navigationBusy}
            >{zh ? "取消，保留公开地图" : "Cancel and keep public map"}</button>
          </div>
        </section>
      )}

      {visibleRoute && (
        <article
          className="journey-membership-catchup"
          data-testid="journey-membership-route-result"
          data-evidence={visibleRouteClass ?? "UNKNOWN"}
          data-provenance={visibleRoute.route.provenance ?? "UNKNOWN"}
        >
          <strong>{visibleRouteClass === "LIVE"
            ? (zh ? "当前路线服务结果" : "Current route-provider result")
            : visibleRouteClass === "REPLAY"
              ? (zh ? "历史路线回放（不是当前路况）" : "Captured historical route (not current traffic)")
              : (zh ? "路线状态：UNKNOWN / ROUTE_UNAVAILABLE" : "Route status: UNKNOWN / ROUTE_UNAVAILABLE")}</strong>
          <p>{zh
            ? `路线目的地：${visibleRoute.target.place_name}。`
            : `Route destination: ${visibleRoute.target.place_name}.`}</p>
          {visibleRouteClass === "UNKNOWN" ? (
            <small>{zh ? "路线时长待确认；可查看地图或联系旅伴。" : "Route duration pending. Check the map or contact your companion."}</small>
          ) : (
            <small>{zh
              ? `步行约 ${visibleRoute.route.duration_min} 分钟。`
              : `Walking estimate: about ${visibleRoute.route.duration_min} minutes.`}</small>
          )}
          <small>
            {zh ? "来源：" : "Source: "}{visibleRoute.route.provider ?? (zh ? "未知" : "unknown")}
            {" · "}{zh ? "证据：" : "Evidence: "}{visibleRoute.route.provenance ?? "UNKNOWN"}
            {visibleRoute.route.captured_at && (
              <>{" · "}{zh ? "路线回执时间：" : "Route receipt time: "}{new Date(visibleRoute.route.captured_at).toLocaleString(locale)}</>
            )}
          </small>
          <small>
            {zh ? "定位依据：" : "Location authority: "}{visibleRoute.authority}
          </small>
          {visibleRouteClass !== "UNKNOWN" && visibleRoute.shared_commitment_risk && (
            <small>
              {zh ? "下一项受保护承诺风险：" : "Next protected-commitment risk: "}
              {visibleRoute.shared_commitment_risk.state}
              {typeof visibleRoute.shared_commitment_risk.slack_after_buffer_min === "number"
                ? ` · ${zh ? "扣除缓冲后的余量" : "slack after buffer"}: ${visibleRoute.shared_commitment_risk.slack_after_buffer_min} min`
                : ""}
            </small>
          )}
          <small>
            {zh ? "Guardian 服务器回执：" : "Guardian server receipt: "}
            {visibleRoute.guardian_triggered ? "triggered" : "not triggered"}
            {" · "}{zh ? "风险事件已记录：" : "risk event recorded: "}
            {visibleRoute.member_risk_event_id ? (zh ? "是" : "yes") : (zh ? "否" : "no")}
            {" · "}{zh ? "处理状态：" : "status: "}
            {String(visibleRoute.guardian?.status ?? "NO_HANDOFF_STATUS_RETURNED")}
          </small>
        </article>
      )}

      {message && <small role="status" data-testid="journey-membership-message">{message}</small>}
    </section>
  );
}
