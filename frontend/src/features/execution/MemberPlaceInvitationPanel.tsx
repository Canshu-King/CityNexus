import { useState } from "react";
import {
  cityNexusApi,
  type MemberPlaceInvitationFeasibilityPreviewResult,
  type MemberPlaceInvitationOwnProgress,
  type MemberPlaceInvitationProgressParticipant,
  type MemberPlaceInvitationProjection,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";
import { buildOpenStreetMapPinUrl } from "./memberSideQuestNavigationLinks";

export function MemberPlaceInvitationPanel({
  journeyId,
  projection,
  onRefreshLocation,
  onUpdated,
}: {
  journeyId: string;
  projection: MemberPlaceInvitationProjection | null | undefined;
  onRefreshLocation?: () => Promise<string | null>;
  onUpdated: () => Promise<void>;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pinConsentId, setPinConsentId] = useState<string | null>(null);
  const [routeConsentId, setRouteConsentId] = useState<string | null>(null);
  const [progressConsent, setProgressConsent] = useState<{
    invitationId: string;
    placeName: string;
    action: "SHARE_ARRIVAL" | "SHARE_HEADING_BACK";
  } | null>(null);
  const [feasibilityById, setFeasibilityById] = useState<Record<string, MemberPlaceInvitationFeasibilityPreviewResult | null>>({});
  const [dwellById, setDwellById] = useState<Record<string, 10 | 20 | 30>>({});
  const invitations = projection?.incoming ?? [];
  const sentInvitations = projection?.sent ?? [];
  const joinedInvitations = projection?.joined ?? [];
  if (!invitations.length && !sentInvitations.length && !joinedInvitations.length) return null;

  const respond = async (
    invitationId: string,
    decision: "ACCEPT" | "DECLINE",
    feasibility?: { token?: string; acknowledgeUnknown?: boolean; acknowledgeRisk?: boolean },
  ) => {
    if (busyId) return;
    setBusyId(invitationId);
    setMessage(null);
    try {
      await cityNexusApi.respondToMemberPlaceInvitation(journeyId, invitationId, decision, feasibility);
      await onUpdated();
      setMessage(decision === "ACCEPT"
        ? (zh ? "已为你创建独立支线；共享行程未改变，也没有自动打开地图。" : "Your own side trip is ready. The shared plan is unchanged and no map was opened.")
        : (zh ? "已谢绝这个地点邀请。" : "Place invitation declined."));
    } catch {
      setMessage(zh
        ? "邀请已失效、你的行程状态有冲突，或暂时无法完成；没有覆盖你现有的支线。刷新后可查看状态。"
        : "The invitation may be stale or your current trip state conflicts. Your existing side trip was not replaced; refresh to review the status.");
      await onUpdated();
    } finally {
      setBusyId(null);
    }
  };

  const checkFeasibility = async (invitationId: string) => {
    if (busyId) return;
    setBusyId(invitationId);
    setRouteConsentId(null);
    setMessage(null);
    try {
      const observationId = onRefreshLocation ? await onRefreshLocation() : null;
      const result = await cityNexusApi.previewMemberPlaceInvitationFeasibility(
        journeyId,
        invitationId,
        observationId,
        dwellById[invitationId] ?? 20,
      );
      setFeasibilityById((current) => ({ ...current, [invitationId]: result }));
    } catch {
      setFeasibilityById((current) => {
        const next = { ...current };
        delete next[invitationId];
        return next;
      });
      setMessage(zh
        ? "路线检查未完成，不能把请求失败当作已确认的“时间未核实”结果。请刷新重试；如不愿共享位置，可在同意弹窗中主动选择跳过。"
        : "The route check failed; this is not a verified UNKNOWN preview. Refresh and retry, or explicitly skip location sharing in the consent dialog.");
    } finally {
      setBusyId(null);
    }
  };

  const updateProgress = async (
    invitationId: string,
    action: "SHARE_ARRIVAL" | "WITHDRAW_ARRIVAL" | "SHARE_HEADING_BACK" | "WITHDRAW_HEADING_BACK",
  ) => {
    if (busyId) return;
    setBusyId(invitationId);
    setMessage(null);
    try {
      await cityNexusApi.updateMemberPlaceInvitationProgress(journeyId, invitationId, action);
      await onUpdated();
      setMessage(action.startsWith("SHARE_")
        ? (zh ? "已向本次邀请中已加入的同行者分享你的自述；它不是 GPS 验证。" : "Your self-report is shared with members who joined this invitation; it is not GPS verified.")
        : (zh ? "已停止在后续视图中分享；此前已看见的信息无法撤回。" : "Future views no longer show this report; information already seen cannot be recalled."));
    } catch {
      setMessage(zh
        ? "无法更新分享状态。你的行程没有被更改；刷新后可查看当前进度。"
        : "The sharing status could not be updated. Your Journey was not changed; refresh to review progress.");
      await onUpdated();
    } finally {
      setBusyId(null);
    }
  };

  const renderProgressBoard = (
    invitationId: string,
    placeName: string,
    rendezvousTitle: string,
    participants: MemberPlaceInvitationProgressParticipant[],
    ownProgress: MemberPlaceInvitationOwnProgress,
    title: string,
    parentState?: string,
  ) => (
    <section className="journey-member-place-progress" data-testid="member-place-progress-board">
      <strong>{title} · {placeName}</strong>
      <small>
        {zh
          ? `共同会合点：${rendezvousTitle}。停留时长只是计划估计；本进度板不验证路线或准时情况，时间按未核实处理。`
          : `Shared rendezvous: ${rendezvousTitle}. Visit duration is a plan estimate; this board does not verify route or arrival timing, so timing remains unverified here.`}
      </small>
      <small>{zh ? "仅显示已加入者主动分享的粗粒度状态；所有报告均为成员自述，未经 GPS 验证。" : "Only coarse statuses explicitly shared by joined members appear here. Every status is member-reported and not GPS verified."}</small>
      {parentState && parentState !== "OPEN" && (
        <small>
          {zh
            ? "邀请已过期、撤回或失效，不再接受新加入；已加入成员的独立支线与历史自愿报告保留。"
            : "This invitation is expired, withdrawn, or stale and cannot accept new members; joined members’ own trips and prior voluntary reports remain."}
        </small>
      )}
      <ul>
        {participants.map((participant) => (
          <li key={participant.member_id} data-testid="member-place-progress-participant">
            <strong>
              {participant.display_name}{" "}
              <span>{participant.membership === "INVITER" ? (zh ? "· 发起者" : "· inviter") : (zh ? "· 已加入" : "· joined")}</span>
            </strong>
            {participant.at_invited_place ? (
              <small>
                {zh ? "报告已到达 · " : "Reported here · "}
                {new Date(participant.at_invited_place.reported_at).toLocaleString(locale)}
                {zh ? " · 自述，非 GPS 验证" : " · self-reported, not GPS verified"}
              </small>
            ) : (
              <small>{zh ? "尚无已分享的到达报告" : "No arrival report shared"}</small>
            )}
            {participant.heading_back && (
              <small>
                {zh ? "报告正在返回 · " : "Reported heading back · "}
                {new Date(participant.heading_back.reported_at).toLocaleString(locale)}
                {zh ? " · 自述，非 GPS 验证" : " · self-reported, not GPS verified"}
              </small>
            )}
          </li>
        ))}
      </ul>
      <div className="journey-side-quest-actions">
        {ownProgress.can_share_arrival && !ownProgress.arrival_shared && (
          <button
            type="button"
            data-testid="member-place-progress-share-arrival"
            disabled={busyId !== null}
            onClick={() => setProgressConsent({ invitationId, placeName, action: "SHARE_ARRIVAL" })}
          >
            {zh ? "分享我报告已到达…" : "Share that I reported arriving…"}
          </button>
        )}
        {ownProgress.arrival_shared && (
          <button
            type="button"
            data-testid="member-place-progress-withdraw-arrival"
            disabled={busyId !== null}
            onClick={() => void updateProgress(invitationId, "WITHDRAW_ARRIVAL")}
          >
            {zh ? "停止分享我的到达状态" : "Stop sharing my arrival status"}
          </button>
        )}
        {ownProgress.can_share_heading_back && !ownProgress.heading_back_shared && (
          <button
            type="button"
            data-testid="member-place-progress-share-heading-back"
            disabled={busyId !== null}
            onClick={() => setProgressConsent({ invitationId, placeName, action: "SHARE_HEADING_BACK" })}
          >
            {zh ? "分享我报告正在返回…" : "Share that I reported heading back…"}
          </button>
        )}
        {ownProgress.heading_back_shared && (
          <button
            type="button"
            data-testid="member-place-progress-withdraw-heading-back"
            disabled={busyId !== null}
            onClick={() => void updateProgress(invitationId, "WITHDRAW_HEADING_BACK")}
          >
            {zh ? "停止分享我的返程状态" : "Stop sharing my return status"}
          </button>
        )}
      </div>
    </section>
  );

  const openPlacePin = (invitationId: string) => {
    const invitation = invitations.find((row) => row.invitation_id === invitationId);
    if (!invitation) return;
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setMessage(zh ? "浏览器阻止了新窗口；允许此站点打开新窗口后再试。" : "The browser blocked the new tab. Allow popups for this site and try again.");
      return;
    }
    popup.opener = null;
    try {
      popup.location.href = buildOpenStreetMapPinUrl(invitation.place);
      setPinConsentId(null);
    } catch {
      popup.close();
      setMessage(zh ? "这个公开地点暂时没有有效地图坐标。" : "This public Place does not have a usable exact map pin.");
    }
  };

  return (
    <div className="journey-member-place-invitations" data-testid="member-place-invitations">
      {sentInvitations.map((invitation) => (
        <article key={invitation.invitation_id} data-testid="member-place-progress-sent-invitation">
          <span className="v8-kicker">{zh ? "你发起的临时同行" : "Your invited micro-adventure"}</span>
          {renderProgressBoard(
            invitation.invitation_id,
            invitation.place.name,
            invitation.rendezvous.title,
            invitation.participants,
            invitation.own_progress,
            zh ? "同行进度" : "Companion progress",
            invitation.state,
          )}
        </article>
      ))}
      {joinedInvitations.map((invitation) => (
        <article key={invitation.invitation_id} data-testid="member-place-invitation-joined">
          <span className="v8-kicker">{zh ? "你已加入的临时同行" : "An invited micro-adventure you joined"}</span>
          <strong>{invitation.inviter_display_name} · {invitation.place.name}</strong>
          {renderProgressBoard(
            invitation.invitation_id,
            invitation.place.name,
            invitation.rendezvous.title,
            invitation.participants,
            invitation.own_progress,
            zh ? "同行进度" : "Companion progress",
            invitation.state,
          )}
        </article>
      ))}
      {invitations.length > 0 && (
      <div data-testid="member-place-invitations-incoming">
      {invitations.map((invitation) => {
        const canRespond = invitation.can_respond;
        const completing = ["ACCEPTANCE_NEEDS_COMPLETION", "ACCEPTANCE_IN_PROGRESS"].includes(invitation.state);
        const hasFeasibility = Object.prototype.hasOwnProperty.call(feasibilityById, invitation.invitation_id);
        const feasibility = feasibilityById[invitation.invitation_id];
        const canAccept = completing || (hasFeasibility && feasibility?.state !== "BLOCKED");
        return (
          <article key={invitation.invitation_id} data-testid="member-place-invitation" data-state={invitation.state}>
            <span className="v8-kicker">{zh ? "同行者分享的公开地点" : "A companion shared a public place"}</span>
            <strong>{invitation.inviter_display_name} · {invitation.place.name}</strong>
            <small>
              {zh
                ? `公开精确坐标：${invitation.place.latitude.toFixed(5)}, ${invitation.place.longitude.toFixed(5)}（${invitation.place.coordinate_system}）`
                : `Exact public pin: ${invitation.place.latitude.toFixed(5)}, ${invitation.place.longitude.toFixed(5)} (${invitation.place.coordinate_system})`}
            </small>
            <small>
              {zh
                ? `来源：${invitation.place.source}。共同会合点：「${invitation.rendezvous.title}」· ${invitation.rendezvous.place_name}${invitation.rendezvous.scheduled_at ? ` · ${new Date(invitation.rendezvous.scheduled_at).toLocaleString(locale)}` : " · 时间未知"}。`
                : `Source: ${invitation.place.source}. Shared rendezvous: ${invitation.rendezvous.title} at ${invitation.rendezvous.place_name}${invitation.rendezvous.scheduled_at ? ` · ${new Date(invitation.rendezvous.scheduled_at).toLocaleString(locale)}` : " · time unknown"}.`}
            </small>
            <small>
              {zh
                ? "先检查能否赶上共同会合；没有可靠证据时不会显示绿色结论。接受后只创建你的独立支线，共享行程保持不变。"
                : "Check whether the detour fits before accepting. Missing evidence never appears green. Acceptance creates only your own side trip; the shared Journey stays unchanged."}
            </small>
            <small>
              {zh
                ? "路线检查会单独征求同意：获取一次前台位置并记录为本人 Journey 位置观察，用于路线估算。它可能更新其他成员可见的粗粒度团队状态，但不会把精确坐标直接显示给同行者。地图导航仍需另行确认。"
                : "A route check asks separately: it records one foreground location observation on your Journey for route estimation. This may update coarse group-presence status seen by companions, but does not show them your exact coordinates. Map navigation needs separate consent."}
            </small>
            {canRespond && !completing && (
              <button
                type="button"
                data-testid="member-place-invitation-check-feasibility"
                disabled={busyId !== null}
                onClick={() => setRouteConsentId(invitation.invitation_id)}
              >
                {hasFeasibility
                  ? (zh ? "重新检查能否赶上" : "Check feasibility again")
                  : (zh ? "检查能否赶上会合…" : "Check if I can make it…")}
              </button>
            )}
            {hasFeasibility && (
              <section
                data-testid="member-place-invitation-feasibility"
                data-state={feasibility?.state ?? "UNKNOWN"}
              >
                <strong>
                  {feasibility?.state === "CAN_MAKE_IT"
                    ? (zh ? "现有路线证据显示可以赶上" : "Current route evidence fits the rendezvous")
                    : feasibility?.state === "AT_RISK"
                      ? (zh ? "时间缓冲较紧" : "Timing is at risk")
                      : feasibility?.state === "BLOCKED"
                        ? (zh ? "当前安排不允许安全接受" : "Current commitments block a safe acceptance")
                        : (zh ? "时间尚未核实" : "Timing is unverified")}
                </strong>
                {feasibility?.travel_duration_min !== null && feasibility?.travel_duration_min !== undefined && (
                  <small>
                    {zh
                      ? `路线、${feasibility.dwell_minutes} 分钟停留与返程合计约 ${feasibility.travel_duration_min} 分钟；缓冲 ${feasibility.slack_min ?? "未知"} 分钟。`
                      : `Outbound route, ${feasibility.dwell_minutes} minute visit, and return total ${feasibility.travel_duration_min} minutes; ${feasibility.slack_min ?? "unknown"} minutes of slack.`}
                  </small>
                )}
                {feasibility?.evidence.captured_at && (
                  <small>
                    {zh ? "路线证据：" : "Route evidence: "}
                    {feasibility.evidence.source_type ?? (zh ? "来源未知" : "source unknown")}
                    {feasibility.evidence.provider ? ` · ${feasibility.evidence.provider}` : ""}
                    {` · ${new Date(feasibility.evidence.captured_at).toLocaleString(locale)}`}
                    {feasibility.evidence.age_seconds !== null ? ` · ${feasibility.evidence.age_seconds}s` : ""}
                  </small>
                )}
                <small>
                  {feasibility?.state === "UNKNOWN"
                    ? (zh ? "没有新鲜本人位置或可靠路线证据；没有估算到达时间。你可以在明确知情后继续。" : "There is no fresh personal location or qualifying route evidence, so no arrival time is estimated. You may continue only after acknowledging that timing is unverified.")
                    : feasibility?.state === "BLOCKED"
                      ? (zh ? "受保护安排或你现有的支线与此选择冲突；共享计划未改变。" : "A protected commitment or your existing side trip conflicts with this choice; the shared plan is unchanged.")
                      : (zh ? "这是路线建议，不是实际到达证明；预览不会改动共享计划。" : "This is route guidance, not proof of physical arrival. The preview does not change the shared plan.")}
                </small>
              </section>
            )}
            <button
              type="button"
              data-testid="member-place-invitation-view-pin"
              disabled={busyId !== null}
              onClick={() => setPinConsentId(invitation.invitation_id)}
            >
              {zh ? "查看地点地图标记…" : "Review place pin…"}
            </button>
            {canRespond ? (
              <div className="journey-side-quest-actions">
                {canAccept && (
                  <button
                    type="button"
                    data-testid="member-place-invitation-accept"
                    disabled={busyId !== null}
                    onClick={() => void respond(
                      invitation.invitation_id,
                      "ACCEPT",
                      completing
                        ? undefined
                        : feasibility?.state === "CAN_MAKE_IT"
                          ? { token: feasibility.feasibility_token }
                          : feasibility?.state === "AT_RISK"
                            ? { token: feasibility.feasibility_token, acknowledgeRisk: true }
                            : { token: feasibility?.feasibility_token, acknowledgeUnknown: true },
                    )}
                  >
                    {busyId === invitation.invitation_id
                      ? (zh ? "正在准备你的支线…" : "Preparing your side trip…")
                      : completing
                        ? (zh ? "继续完成我的支线" : "Finish setting up my side trip")
                        : feasibility?.state === "AT_RISK"
                          ? (zh ? "我了解时间风险，仍要接受" : "Accept despite the timing risk")
                          : feasibility?.state === "UNKNOWN"
                            ? (zh ? "接受，且知晓时间未核实" : "Accept knowing timing is unverified")
                            : (zh ? "接受并添加到我的私人支线" : "Accept and add to my side trip")}
                  </button>
                )}
                {feasibility?.state === "BLOCKED" && (
                  <small>{zh ? "无法安全接受；请保留现有安排或先解决冲突。" : "Acceptance is blocked. Keep your current plans or resolve the conflict first."}</small>
                )}
                {!completing && (
                  <button
                    type="button"
                    data-testid="member-place-invitation-decline"
                    disabled={busyId !== null}
                    onClick={() => void respond(invitation.invitation_id, "DECLINE")}
                  >
                    {zh ? "谢绝" : "Decline"}
                  </button>
                )}
              </div>
            ) : (
              <small>
                {invitation.state === "EXPIRED"
                  ? (zh ? "邀请已过期。" : "This invitation expired.")
                  : invitation.state === "STALE"
                    ? (zh ? "来源支线或共同会合安排已变化，不能再接受。" : "The source stop or shared rendezvous changed; this invitation can no longer be accepted.")
                    : invitation.state === "WITHDRAWN"
                      ? (zh ? "邀请已撤回。" : "This invitation was withdrawn.")
                      : (zh ? "当前无法响应此邀请。" : "This invitation can no longer be answered.")}
              </small>
            )}
          </article>
        );
      })}
      </div>
      )}
      {routeConsentId && invitations.some((row) => row.invitation_id === routeConsentId) && (
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="member-place-invitation-route-title"
          data-testid="member-place-invitation-route-consent"
        >
          <strong id="member-place-invitation-route-title">
            {zh ? "为这次路线检查分享一次当前位置？" : "Share one current location for this route check?"}
          </strong>
          <p>
            {zh
              ? "同意后，CityNexus 会记录一条与你的身份绑定的 Journey 前台位置观察，并把起点、公开地点和会合点交给已配置的路线服务估算。其他成员不会在团队视图中看到你的精确坐标或私有路线，但可能看到更新后的粗粒度团队状态。不会改动共享计划；拒绝定位或缺少路线证据时结果是“时间未核实”。"
              : "If you agree, CityNexus records one identity-bound foreground location observation on your Journey and sends your origin, the public Place, and rendezvous to the configured route service for this estimate. Companions do not see your exact coordinates or private route in the group view, but their coarse group-presence status may update. The shared plan is unchanged. Denied location or missing route evidence means unverified timing."}
          </p>
          <label htmlFor="member-place-invitation-dwell">
            {zh ? "你计划在这里停留多久？" : "How long would you stay?"}
          </label>
          <select
            id="member-place-invitation-dwell"
            data-testid="member-place-invitation-dwell"
            value={dwellById[routeConsentId] ?? 20}
            disabled={busyId !== null}
            onChange={(event) => {
              const minutes = Number(event.target.value) as 10 | 20 | 30;
              setDwellById((current) => ({ ...current, [routeConsentId]: minutes }));
              setFeasibilityById((current) => {
                const next = { ...current };
                delete next[routeConsentId];
                return next;
              });
            }}
          >
            <option value={10}>{zh ? "10 分钟" : "10 minutes"}</option>
            <option value={20}>{zh ? "20 分钟" : "20 minutes"}</option>
            <option value={30}>{zh ? "30 分钟" : "30 minutes"}</option>
          </select>
          <div className="journey-side-quest-actions">
            <button
              type="button"
              data-testid="member-place-invitation-route-confirm"
              disabled={busyId !== null}
              onClick={() => void checkFeasibility(routeConsentId)}
            >
              {zh ? "同意并检查一次" : "Agree and check once"}
            </button>
            <button
              type="button"
              data-testid="member-place-invitation-route-skip"
              onClick={() => {
                setFeasibilityById((current) => ({ ...current, [routeConsentId]: null }));
                setRouteConsentId(null);
              }}
            >
              {zh ? "不分享位置，按未核实继续…" : "Skip location sharing; continue unverified…"}
            </button>
            <button type="button" onClick={() => setRouteConsentId(null)}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}
      {pinConsentId && invitations.some((row) => row.invitation_id === pinConsentId) && (
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="member-place-invitation-pin-title"
          data-testid="member-place-invitation-pin-consent"
        >
          <strong id="member-place-invitation-pin-title">{zh ? "将公开地点坐标发送给 OpenStreetMap？" : "Send the public Place coordinates to OpenStreetMap?"}</strong>
          <p>
            {zh
              ? "只会打开已分享地点的精确地图标记；不会发送你的起点或设备位置。OpenStreetMap 可能按浏览器自己的权限访问位置。此操作不会接受邀请或报告到达。"
              : "Only the shared Place’s exact pin is opened. Your origin and device location are not sent by CityNexus. OpenStreetMap may use location under your browser’s own permissions. This does not accept the invitation or report arrival."}
          </p>
          <div className="journey-side-quest-actions">
            <button
              type="button"
              data-testid="member-place-invitation-pin-confirm"
              onClick={() => openPlacePin(pinConsentId)}
            >
              {zh ? "同意并打开 OpenStreetMap" : "Agree and open OpenStreetMap"}
            </button>
            <button type="button" onClick={() => setPinConsentId(null)}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}
      {progressConsent && (
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="member-place-progress-consent-title"
          data-testid="member-place-progress-consent"
        >
          <strong id="member-place-progress-consent-title">
            {progressConsent.action === "SHARE_ARRIVAL"
              ? (zh ? "要向已加入的同行者分享这条到达自述吗？" : "Share this arrival self-report with joined companions?")
              : (zh ? "要向已加入的同行者分享这条返程自述吗？" : "Share this return self-report with joined companions?")}
          </strong>
          <p>
            {zh
              ? "你将只向“" + progressConsent.placeName + "”邀请中已加入的成员分享这一粗粒度状态。内容是你自己的报告，不是 GPS 到场验证，也不含坐标或路线。你可以停止后续展示；别人已经看见的信息无法撤回。"
              : "Only members who joined the invitation for “" + progressConsent.placeName + "” will see this coarse status. It is your report, not GPS-verified presence, and contains no coordinates or route. You can stop future projections; information already seen cannot be recalled."}
          </p>
          <div className="journey-side-quest-actions">
            <button
              type="button"
              data-testid="member-place-progress-consent-confirm"
              disabled={busyId !== null}
              onClick={() => {
                const consent = progressConsent;
                void updateProgress(consent.invitationId, consent.action).then(() => setProgressConsent(null));
              }}
            >
              {zh ? "同意并分享这条自述" : "Agree and share this self-report"}
            </button>
            <button type="button" onClick={() => setProgressConsent(null)}>
              {zh ? "取消" : "Cancel"}
            </button>
          </div>
        </section>
      )}
      {message && <small role="status" data-testid="member-place-invitation-message">{message}</small>}
    </div>
  );
}
