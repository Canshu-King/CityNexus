import { useCallback, useEffect, useState } from "react";
import {
  cityNexusApi,
  type JourneyMembershipInvitationInboxItem,
  type JourneyMembershipInvitationManagerItem,
  type JourneyOperatorProjection,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";

type Props = {
  journeyId: string | null;
  journeyStatus?: string | null;
  recentlyJoinedJourneyId?: string | null;
  onJourneyJoined: (journeyId: string) => Promise<void> | void;
};

type Rendezvous = NonNullable<
  NonNullable<JourneyOperatorProjection["group_presence"]>["rendezvous"]
>;

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

export function JourneyMembershipPanel({
  journeyId,
  journeyStatus,
  recentlyJoinedJourneyId = null,
  onJourneyJoined,
}: Props) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [inbox, setInbox] = useState<JourneyMembershipInvitationInboxItem[]>([]);
  const [sent, setSent] = useState<JourneyMembershipInvitationManagerItem[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [targetTravelerId, setTargetTravelerId] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [mapConsent, setMapConsent] = useState(false);
  const [rendezvous, setRendezvous] = useState<Rendezvous | null>(null);

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

  useEffect(() => {
    if (!journeyId || recentlyJoinedJourneyId !== journeyId) return;
    let cancelled = false;
    setRendezvous(null);
    void cityNexusApi.getJourneyOperator(journeyId).then((projection) => {
      if (!cancelled) setRendezvous(projection.group_presence?.rendezvous ?? null);
    }).catch(() => {
      if (!cancelled) setRendezvous(null);
    });
    return () => { cancelled = true; };
  }, [journeyId, recentlyJoinedJourneyId]);

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

  const openPublicMap = () => {
    if (!rendezvous) return;
    const url = `https://www.openstreetmap.org/search?query=${encodeURIComponent(rendezvous.place_name)}`;
    window.open(url, "_blank", "noopener,noreferrer");
    setMapConsent(false);
  };

  const active = String(journeyStatus ?? "").toUpperCase() === "ACTIVE";
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

      {journeyId && recentlyJoinedJourneyId === journeyId && (
        <div className="journey-membership-catchup" data-testid="journey-membership-catchup">
          <strong>{zh ? "如何追上同行者？" : "How do I catch up?"}</strong>
          {rendezvous ? (
            <>
              <p>{zh ? `当前共同会合点：${rendezvous.place_name}。` : `Current shared rendezvous: ${rendezvous.place_name}.`}</p>
              <small>{zh ? "当前没有经过验证的个人路线或 ETA（UNKNOWN / ROUTE_UNAVAILABLE）；CityNexus 没有读取或分享你的起点。" : "No verified personal route or ETA is available (UNKNOWN / ROUTE_UNAVAILABLE). CityNexus has not read or shared your origin."}</small>
              <button type="button" onClick={() => setMapConsent(true)}>
                {zh ? "查看公开会合点地图…" : "View public rendezvous map…"}
              </button>
            </>
          ) : (
            <small>{zh ? "暂时没有可确认的共同会合点（UNKNOWN / ROUTE_UNAVAILABLE）；没有读取位置或报告到达。" : "No shared rendezvous is currently available (UNKNOWN / ROUTE_UNAVAILABLE). No location was read and no arrival was reported."}</small>
          )}
        </div>
      )}

      {mapConsent && rendezvous && (
        <section className="journey-membership-map-consent" role="dialog" aria-modal="true" aria-labelledby="journey-membership-map-title" data-testid="journey-membership-map-consent">
          <strong id="journey-membership-map-title">{zh ? "打开公开会合点地图？" : "Open a public map of the rendezvous?"}</strong>
          <p>{zh
            ? `同意后会把公开地点名称“${rendezvous.place_name}”发送给 OpenStreetMap 搜索。不会发送你的起点或位置，也不会生成路线、ETA 或到达记录。`
            : `If you agree, the public place name “${rendezvous.place_name}” is sent to OpenStreetMap search. Your origin and location are not sent; this creates no route, ETA, or arrival record.`}</p>
          <div className="journey-membership-actions">
            <button type="button" data-testid="journey-membership-map-confirm" onClick={openPublicMap}>
              {zh ? "同意并打开地图" : "Agree and open map"}
            </button>
            <button type="button" onClick={() => setMapConsent(false)}>{zh ? "取消" : "Cancel"}</button>
          </div>
        </section>
      )}

      {message && <small role="status" data-testid="journey-membership-message">{message}</small>}
    </section>
  );
}
