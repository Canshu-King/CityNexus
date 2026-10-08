import { useState } from "react";
import { cityNexusApi, type MemberPlaceInvitationProjection } from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";
import { buildOpenStreetMapPinUrl } from "./memberSideQuestNavigationLinks";

export function MemberPlaceInvitationPanel({
  journeyId,
  projection,
  onUpdated,
}: {
  journeyId: string;
  projection: MemberPlaceInvitationProjection | null | undefined;
  onUpdated: () => Promise<void>;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pinConsentId, setPinConsentId] = useState<string | null>(null);
  const invitations = projection?.incoming ?? [];
  if (!invitations.length) return null;

  const respond = async (invitationId: string, decision: "ACCEPT" | "DECLINE") => {
    if (busyId) return;
    setBusyId(invitationId);
    setMessage(null);
    try {
      await cityNexusApi.respondToMemberPlaceInvitation(journeyId, invitationId, decision);
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
    <div className="journey-member-place-invitations" data-testid="member-place-invitations-incoming">
      {invitations.map((invitation) => {
        const canRespond = invitation.can_respond;
        const completing = invitation.state === "ACCEPTANCE_NEEDS_COMPLETION";
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
                ? "这是同行者发出的社交邀请，不代表路线或停留时间一定赶得上共同会合。接受后会为你创建独立支线，共享行程保持不变。"
                : "This is a social invitation, not a promise that the visit fits the route or shared meetup time. Accepting creates your own side trip; the shared Journey stays unchanged."}
            </small>
            <small>
              {zh
                ? "接受不会自动打开地图，也不会向 CityNexus 发送你的位置或起点。之后如需导航，可在支线卡片中单独确认打开地图。"
                : "Accepting does not open a map or send CityNexus your location or origin. You can separately confirm map navigation from your side-quest card later."}
            </small>
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
                <button
                  type="button"
                  data-testid="member-place-invitation-accept"
                  disabled={busyId !== null}
                  onClick={() => void respond(invitation.invitation_id, "ACCEPT")}
                >
                  {busyId === invitation.invitation_id
                    ? (zh ? "正在准备你的支线…" : "Preparing your side trip…")
                    : completing
                      ? (zh ? "继续完成我的支线" : "Finish setting up my side trip")
                      : (zh ? "接受并添加到我的私人支线" : "Accept and add to my side trip")}
                </button>
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
      {message && <small role="status" data-testid="member-place-invitation-message">{message}</small>}
    </div>
  );
}
