import { useCallback, useEffect, useState } from "react";
import {
  cityNexusApi,
  type GroupRendezvousRouteResult,
  type JourneyMembershipInvitationInboxItem,
  type JourneyMembershipInvitationManagerItem,
  type JourneyOperatorProjection,
  type JourneyRendezvousCoordinationSignal,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";
import { buildOpenStreetMapPinUrl } from "./memberSideQuestNavigationLinks";

type Props = {
  journeyId: string | null;
  journeyStatus?: string | null;
  recentlyJoinedJourneyId?: string | null;
  onRefreshLocation?: () => Promise<string | null>;
  onJourneyJoined: (journeyId: string) => Promise<void> | void;
};

type GroupPresence = NonNullable<JourneyOperatorProjection["group_presence"]>;
type Rendezvous = NonNullable<
  GroupPresence["rendezvous"]
>;

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

async function rendezvousAudienceSha256(members: GroupPresence["members"]): Promise<string> {
  const memberIds = members.map((member) => member.member_id).sort();
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify(memberIds)),
  );
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
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
    return zh ? "旅伴必须亲自接受后才会加入；没有写入任何成员。" : "The traveller must accept before joining. No membership was added.";
  }
  if (code.includes("MEMBER_MANAGE")) {
    return zh ? "只有当前有成员管理权限的旅伴可以发出邀请。" : "Only a current Journey member with member-management authority can invite someone.";
  }
  if (code.includes("ALREADY_PENDING")) {
    return zh ? "这位旅伴已有一个待处理邀请。" : "This traveller already has a pending invitation.";
  }
  if (code.includes("ACTIVE_JOURNEY")) {
    return zh ? "行程开始并选定当前计划后，才能邀请旅伴加入。" : "Invite a companion after the Journey is active with a selected plan.";
  }
  return zh ? "邀请没有完成；成员名单没有改变，请刷新后重试。" : "The invitation did not complete. The member set is unchanged; refresh and retry.";
}

function coordinationFailureCopy(code: string, zh: boolean): string {
  if (code.includes("WITHDRAW_TARGET_STALE")) {
    return zh
      ? "你先前看到的状态已被替换、过期或撤回。它不代表当前状态已停止分享；请查看刚刷新后的团队状态。"
      : "The previously displayed status was replaced, expired, or revoked. This does not stop a newer status; check the refreshed team view.";
  }
  if (code.includes("CONTEXT_CHANGED") || code.includes("TARGET_CHANGED")) {
    return zh
      ? "共享计划或会合点刚刚变化。状态没有分享，请刷新后重新确认对象。"
      : "The shared plan or rendezvous changed. Nothing was shared; refresh and confirm the current stop.";
  }
  if (code.includes("GROUP_RECOVERY_FOLLOWTHROUGH_ACTIVE")) {
    return zh
      ? "团队正在完成已批准的恢复会合；此状态暂不可替代恢复确认。"
      : "The group is completing an approved recovery rendezvous. This self-report cannot replace its confirmation.";
  }
  if (code.includes("PLANNED_SPLIT_TARGET_UNSUPPORTED")) {
    return zh
      ? "你当前有独立的计划支线；请使用该支线的会合安排。"
      : "You are on a planned individual side trip. Use that trip's rendezvous flow.";
  }
  return zh
    ? "状态没有更新。请刷新团队状态后重试；当前共享计划没有改变。"
    : "The status was not updated. Refresh the team status and retry; the shared plan is unchanged.";
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
  const [coordinationBusy, setCoordinationBusy] = useState(false);
  const [coordinationMessage, setCoordinationMessage] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<{
    key: string;
    result: GroupRendezvousRouteResult;
  } | null>(null);
  const rendezvous = groupPresence?.rendezvous ?? null;
  const currentTargetKey = groupPresenceTargetKey(groupPresence);

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
      return null;
    }
    try {
      const projection = await cityNexusApi.getJourneyOperator(journeyId);
      const next = projection.group_presence ?? null;
      setGroupPresence(next);
      return next;
    } catch {
      setGroupPresence(null);
      return null;
    }
  }, [active, journeyId]);

  useEffect(() => {
    // A companion still needs the shared meeting point after a reload, not
    // only during the React session in which they pressed Accept.
    if (!journeyId || !active) {
      setGroupPresence(null);
      setRouteResult(null);
      return;
    }
    let cancelled = false;
    void cityNexusApi.getJourneyOperator(journeyId).then((projection) => {
      if (!cancelled) setGroupPresence(projection.group_presence ?? null);
    }).catch(() => {
      if (!cancelled) setGroupPresence(null);
    });
    return () => { cancelled = true; };
  }, [journeyId, active]);

  useEffect(() => {
    setRouteResult((current) => current?.key === currentTargetKey ? current : null);
  }, [currentTargetKey]);

  useEffect(() => {
    setCoordinationConsentKind(null);
    setCoordinationConsentKey(null);
  }, [currentTargetKey]);

  const coordinationSignals = groupPresence?.coordination_signals ?? [];
  const ownCoordinationSignal = coordinationSignals.find((signal) => signal.viewer_can_withdraw) ?? null;

  const openCoordinationConsent = (kind: JourneyRendezvousCoordinationSignal["signal_kind"]) => {
    if (!currentTargetKey || !groupPresence?.can_guide) return;
    setCoordinationMessage(null);
    setCoordinationConsentKey(currentTargetKey);
    setCoordinationConsentKind(kind);
  };

  const shareCoordinationSignal = async () => {
    if (coordinationBusy || !journeyId || !coordinationConsentKind) return;
    const current = groupPresence;
    const target = current?.rendezvous;
    const activePlanId = current?.active_plan_version_id;
    if (!current || !target || !activePlanId || coordinationConsentKey !== currentTargetKey) {
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
      setCoordinationMessage(zh
        ? "会合点视图已经变化，请刷新后重新选择。"
        : "The rendezvous view changed. Refresh before sharing a status.");
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
          expected_audience_sha256: await rendezvousAudienceSha256(current.members),
        },
        crypto.randomUUID(),
      );
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
      setCoordinationMessage(receipt.status === "ACTIVE"
        ? (zh
          ? "你的自愿状态已分享给当前同行者；它会在 45 分钟后过期，不证明已到场。"
          : "Your voluntary status is shared with current companions for up to 45 minutes; it does not prove arrival.")
        : (zh ? "状态已处理。" : "The status was processed."));
      await refreshGroupPresence();
    } catch (error) {
      const text = error instanceof Error ? error.message : "";
      setCoordinationMessage(coordinationFailureCopy(text, zh));
      setCoordinationConsentKind(null);
      setCoordinationConsentKey(null);
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
      setCoordinationMessage(zh
        ? "已用你的签名身份回应这次求助；这不表示你在现场等待。"
        : "You acknowledged this help request with your signed identity; this does not mean you are physically waiting there.");
      await refreshGroupPresence();
    } catch (error) {
      setCoordinationMessage(coordinationFailureCopy(error instanceof Error ? error.message : "", zh));
      await refreshGroupPresence();
    } finally {
      setCoordinationBusy(false);
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
        crypto.randomUUID(),
      );
      setTargetTravelerId("");
      setMessage(zh
        ? `已邀请这位旅伴作为 COLLABORATOR。TA 接受前不会出现在成员名单中。有效期至 ${new Date(created.expires_at).toLocaleString(locale)}。`
        : `Collaborator invitation sent. They will not enter the member set until they accept. Expires ${new Date(created.expires_at).toLocaleString(locale)}.`);
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
          ? "你已作为 COLLABORATOR 加入这趟行程。现有地点分享或待决策可能因成员名单变化而需要重新确认。"
          : "You joined as a collaborator. Existing Place shares and pending decisions may need renewed consent because the member set changed.");
      } else {
        setMessage(zh ? "已谢绝邀请；成员名单没有改变。" : "Invitation declined. The member set is unchanged.");
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
      setMessage(zh ? "邀请已撤回；对方不会因此加入。" : "Invitation revoked. The recipient was not added.");
    } catch {
      setMessage(zh ? "邀请状态已变化或暂时无法撤回，请刷新查看。" : "The invitation changed state or could not be revoked. Refresh to review it.");
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
          ? "计划进度或会合点刚刚变化；没有打开旧地点。请查看更新后的会合点，再重新确认。"
          : "The plan or meeting stop changed. No stale place was opened; review the updated stop and confirm again.");
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
        ? "无法重新确认当前会合点；没有向地图服务发送地点。请刷新后再试。"
        : "The current meeting stop could not be revalidated; no place was sent to the map service. Refresh and try again.");
    } finally {
      setNavigationBusy(false);
    }
  };

  const requestRouteConsent = () => {
    if (!journeyId || !groupPresence?.can_guide || !onRefreshLocation) {
      setMessage(zh ? "当前没有可用于计算路线的共享会合点；公开地点回退仍可使用。" : "A shared route target is not currently available. The public-place fallback remains available.");
      return;
    }
    if (!hasExactPublicPin(rendezvous)) {
      setMessage(zh ? "会合地点缺少可靠的 WGS84 坐标，无法安全计算路线；可按名称核对公开地点。" : "The shared stop has no reliable WGS84 coordinates, so routing is unavailable. You can still verify the public place by name.");
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
          ? "计划或会合点已变化；没有读取位置。请查看新的共同会合点并重新确认。"
          : "The plan or meeting stop changed; no location was read. Review the new stop and confirm again.");
        return;
      }

      const observationId = await onRefreshLocation();
      if (!observationId) {
        setMessage(zh
          ? "没有取得这次前台位置；没有请求路线。你仍可打开公开会合点地图。"
          : "No foreground location was recorded, so no route was requested. The public meeting-place map is still available.");
        return;
      }
      const afterLocation = await refreshGroupPresence();
      if (
        !afterLocation?.can_guide
        || groupPresenceTargetKey(afterLocation) !== expectedKey
        || !hasExactPublicPin(afterLocation.rendezvous)
      ) {
        setMessage(zh
          ? "获取位置期间计划或会合点发生变化；没有计算路线。请查看更新后的目的地并重新确认。"
          : "The plan or meeting stop changed while location was being recorded. No route was calculated; review and confirm the updated destination.");
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
          ? "路线计算期间计划、进度或目的地已变化；旧路线已丢弃，请查看当前会合点后重新确认。"
          : "The plan, progress, or destination changed during routing. The old route was discarded; review the current stop and confirm again.");
        return;
      }
      setRouteResult({ key: expectedKey, result });
      setMessage(routeEvidenceClass(result) === "UNKNOWN"
        ? (zh ? "路线服务没有提供可验证且新鲜的路线；显示 UNKNOWN，不显示预计分钟数。" : "No fresh, verifiable route was returned. Guidance remains UNKNOWN; no duration is shown.")
        : (zh ? "路线结果已绑定到当前共享目的地；它不会改变行程或证明同行者已到达。" : "The route is bound to the current shared stop. It does not change the plan or prove that anyone has arrived."));
    } catch {
      await refreshGroupPresence();
      setMessage(zh
        ? "当前路线不可用或已过期；没有显示预计时间。公开会合点地图仍可使用。"
        : "The route is unavailable or expired; no duration is shown. The public meeting-place map remains available.");
    } finally {
      setNavigationBusy(false);
    }
  };

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
                {invitation.city_code} · {invitation.approximate_start_date} · COLLABORATOR
              </p>
              <small>
                {zh ? "仅显示行程概况和建议角色；接受前不会显示地点、成员名单或路线。邀请有效期至 " : "This preview omits Places, the member roster, and routes. Expires "}
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
              ? "邀请仅授予 COLLABORATOR。只有收件人本人签名接受后才会加入；邀请 24 小时后失效。"
              : "The invitation offers COLLABORATOR only. Membership begins after the recipient’s own signed acceptance; the invitation expires in 24 hours."}
          </small>
          {!active && <small>{zh ? "此 Journey 尚未开始或没有当前计划，暂不能邀请加入。" : "This Journey must be active with a selected plan before inviting a companion."}</small>}
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
                ? (zh ? "地图使用当前共享计划中的 WGS84 公共地点坐标，不使用任何成员的实时位置。" : "Map pin comes from the shared active-plan public Place (WGS84), not a member's live location.")
                : (zh ? "没有可靠的公共地点坐标。地图只能按名称搜索，可能出现多个同名地点，出发前请核对。" : "No reliable public destination coordinates are available. Map search by name may be ambiguous; verify the place before traveling.")}</small>
              <small data-testid="journey-membership-location-truth">{visibleRoute
                ? visibleRouteClass === "UNKNOWN"
                  ? (zh
                    ? "本次路线请求没有得到可靠 ETA；你自愿提交的前台位置观察可能已保存在 Journey 中。"
                    : "This route request did not establish a trustworthy ETA. Your consented foreground location observation may already be stored on this Journey.")
                  : (zh
                    ? "下方路线来自你主动授权的检查；前台位置观察可能保留在 Journey，旅伴可能看到变化后的粗粒度队伍状态。"
                    : "The route below follows your explicit location consent. The foreground observation may remain on this Journey and can change companions' coarse group-presence view.")
                : (zh
                  ? "如需个人 ETA，请主动授权新的前台位置检查；此前提交的 Journey 位置观察可能仍被保存，不会因为本页未请求路线就自动删除。"
                  : "To check a personal ETA, explicitly authorize a new foreground location sample. Earlier Journey observations may still be retained even when this panel has no route result.")}</small>
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
                      ? "路线检查与状态分享是分开的。只有你明确确认后，当前同行者才会看到这条自报状态；它不代表真实到场。"
                      : "Route checks and status sharing are separate. Current companions see a status only after your explicit confirmation; it is not proof of arrival."}
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
                          <small>{zh ? "自报意向 · 未验证，不含 GPS 起点或个人路线，也不表示已到场。" : "Self-reported and unverified; no GPS origin or private route is shared, and this does not mean arrival."}</small>
                          {signal.acknowledgement && (
                            <small data-testid="journey-rendezvous-help-acknowledgement">
                              {zh
                                ? `${signal.acknowledgement.display_name} 已用本人身份回应这次求助；这不是现场等待或会合确认。`
                                : `${signal.acknowledgement.display_name} acknowledged this request with their own identity; this is not a promise to wait there or an arrival confirmation.`}
                            </small>
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
                  {coordinationMessage && (
                    <small role="status" data-testid="journey-rendezvous-message">{coordinationMessage}</small>
                  )}
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
                          ? `当前会看到的同行者：${groupPresence.members.filter((item) => !item.is_viewer).map((item) => item.display_name).join("、")}。对象仅是当前共享计划的公共会合点“${rendezvous.place_name}”，状态最多保留 45 分钟。`
                          : `Current companions who can see this: ${groupPresence.members.filter((item) => !item.is_viewer).map((item) => item.display_name).join(", ")}. It is only about the shared-plan public stop “${rendezvous.place_name}” and expires within 45 minutes.`}
                      </p>
                      <p>
                        {zh
                          ? "不会读取或分享 GPS 起点、位置观察 ID 或个人路线；路线请求不会自动分享状态。此内容是未经验证的本人自报，不是路线危险、物理到场或 R69 会合确认。"
                          : "This does not read or share GPS origin, observation IDs, or private routes; a route request never shares status automatically. It is your unverified self-report, not evidence of route danger, physical arrival, or R69 reunion."}
                      </p>
                      <div className="journey-membership-actions">
                        <button
                          type="button"
                          data-testid="journey-rendezvous-consent-confirm"
                          disabled={coordinationBusy || coordinationConsentKey !== currentTargetKey}
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
                          }}
                        >{zh ? "取消" : "Cancel"}</button>
                      </div>
                    </section>
                  )}
                </section>
              )}
            </>
          ) : (
            <small>{zh ? "暂时没有可确认的共同会合点（UNKNOWN / ROUTE_UNAVAILABLE）；没有读取位置或报告到达。" : "No shared rendezvous is currently available (UNKNOWN / ROUTE_UNAVAILABLE). No location was read and no arrival was reported."}</small>
          )}
        </div>
      )}

      {mapConsent && rendezvous && (
        <section className="journey-membership-map-consent" role="dialog" aria-modal="true" aria-labelledby="journey-membership-map-title" data-testid="journey-membership-map-consent">
          <strong id="journey-membership-map-title">{zh ? "打开公开会合点地图？" : "Open a public map of the rendezvous?"}</strong>
          <p>{hasExactPublicPin(rendezvous)
            ? (zh
              ? `同意后，会把共享计划中公共地点“${rendezvous.place_name}”的精确 WGS84 目的地坐标发送给 OpenStreetMap 标点。不会发送你的起点或位置，不会生成路线、ETA 或到达记录；这也不是队伍当前所在位置的证明。`
              : `If you agree, the shared public Place's exact WGS84 destination coordinates are sent to OpenStreetMap for a map pin. Your origin is not sent; no route, ETA or arrival record is created, and this does not prove where the group currently is.`)
            : (zh
              ? `同意后，只会向 OpenStreetMap 发送公开地点名称“${rendezvous.place_name}”进行搜索；结果可能不唯一。不会发送你的起点或位置，不会生成路线、ETA 或到达记录。`
              : `If you agree, only the public Place name “${rendezvous.place_name}” is sent to OpenStreetMap search; results may be ambiguous. Your origin is not sent; no route, ETA or arrival record is created.`)}</p>
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
            ? `继续会为这趟 Journey 记录一次由你主动发起的前台位置观察；该观察会保留，并可能以粗略同行状态供旅伴查看。你的精确起点可能发送给明确配置的路线服务。若现有路线风险规则判定需要，可能记录承诺风险并触发 Guardian。拒绝后仍可查看公开会合点地图。不会后台采样、持续追踪、静默修改共享计划，也不会把路线结果当作已到达或已与大家会合。`
            : `Continuing records a Journey-bound foreground location observation that you explicitly request; it is retained and may affect the coarse group-presence state companions can see. Your precise origin may be sent to the configured routing provider. Existing route-risk rules may record a protected-commitment risk and trigger Guardian. Declining keeps the public meeting-place map available. There is no background sampling or tracking, the shared plan is not silently changed, and a route result is not an arrival or proof that the group is together.`}</p>
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
            ? `共享计划目的地：${visibleRoute.target.place_name}。这表示路线目的地，不表示队伍当前就在此处。`
            : `Shared-plan destination: ${visibleRoute.target.place_name}. This identifies the planned stop, not where the group is physically located.`}</p>
          {visibleRouteClass === "UNKNOWN" ? (
            <small>{zh ? "没有显示预计分钟数；请使用公开地点地图或手动联系旅伴。" : "No duration is shown. Use the public-place map or coordinate with companions manually."}</small>
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
