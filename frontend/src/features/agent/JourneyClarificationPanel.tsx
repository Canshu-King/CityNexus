import { useCallback, useEffect, useState } from "react";
import {
  cityNexusApi,
  CityNexusApiError,
  type AgentRun,
  type CollectiveCandidateOption,
  type PendingJourneyMission,
  type PendingJourneyViewer,
} from "../../api/citynexus";

function optionLabel(key: string, zh: boolean): string {
  if (key === "TAKE_NOW") return zh ? "优先当前机会" : "Prefer the current opportunity";
  if (key === "TAKE_LATER") return zh ? "保留资源给后续机会" : "Preserve resources for the later opportunity";
  return key;
}

function roleLabel(role: string, zh: boolean): string {
  if (role === "OWNER") return zh ? "行程所有者" : "Trip owner";
  if (role === "ADMIN") return zh ? "管理员" : "Admin";
  if (role === "COLLABORATOR") return zh ? "同行者" : "Collaborator";
  return role;
}

function candidateLabel(option: CollectiveCandidateOption, index: number, zh: boolean): string {
  const names = (option.display_places ?? []).map((item) => item.name).filter(Boolean);
  if (names.length) return names.join(" · ");
  const tags = (option.fit_subject_tags ?? []).filter(Boolean).slice(0, 3);
  if (tags.length) return tags.join(" · ");
  return zh ? `方案 ${index + 1}` : `Option ${index + 1}`;
}

function candidateTradeoff(option: CollectiveCandidateOption, zh: boolean): string {
  const unhappy = option.fairness?.unacceptable_member_ids?.length ?? 0;
  if (unhappy > 0) {
    return zh
      ? `服务器判断这项会让 ${unhappy} 位相关同行者作出明显让步。`
      : `The server found a material compromise for ${unhappy} relevant traveler${unhappy === 1 ? "" : "s"}.`;
  }
  return zh
    ? "服务器没有记录到这项存在严重的成员适配冲突。"
    : "The server did not record a severe member-fit conflict for this option.";
}

function completionLabel(run: AgentRun, zh: boolean): string {
  const kind = run.completion_contract?.kind;
  if (kind === "MUTATION_EXECUTED") return zh ? "服务器已确认执行变化。" : "The server confirmed an execution change.";
  if (kind === "NO_ACTION") return zh ? "行程未更改。" : "Journey unchanged.";
  if (kind === "APPROVAL_PENDING" || run.status === "WAITING_FOR_APPROVAL") {
    return zh ? "助手已停在批准边界，等待有权限的人确认。" : "The assistant is paused at the approval boundary.";
  }
  if (run.status === "FAILED_EXTERNAL" || run.status === "UNAVAILABLE") {
    return zh ? "答案已保存 · 后续任务未完成。" : "Answer saved · follow-up incomplete.";
  }
  return zh ? "答案已保存；决策仍待处理。" : "Answer saved; decision pending.";
}

function apiStatus(cause: unknown): number | null {
  return cause instanceof CityNexusApiError ? cause.status : null;
}

/** Questions/options come only from persisted server missions, never from model prose. */
export function JourneyClarificationPanel({ journeyId, refreshKey, zh, onJourneyUpdated }: {
  journeyId: string;
  refreshKey: number;
  zh: boolean;
  onJourneyUpdated: () => Promise<void>;
}) {
  const [items, setItems] = useState<PendingJourneyMission[]>([]);
  const [viewer, setViewer] = useState<PendingJourneyViewer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staleIds, setStaleIds] = useState<string[]>([]);
  const [receipt, setReceipt] = useState<AgentRun | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const response = await cityNexusApi.getPendingJourneyMissions(journeyId);
    setItems(response.items);
    setViewer(response.viewer);
  }, [journeyId]);

  useEffect(() => {
    let active = true;
    cityNexusApi.getPendingJourneyMissions(journeyId).then(
      (response) => {
        if (!active) return;
        setItems(response.items);
        setViewer(response.viewer);
      },
      (cause) => {
        if (!active) return;
        const status = apiStatus(cause);
        setError(
          status === 401
            ? (zh ? "同行者会话已失效，请重新登录。" : "Traveler session expired. Sign in again.")
            : (zh ? "待回答任务加载失败，请重试。" : "Could not load pending decisions. Try again."),
        );
      },
    );
    return () => { active = false; };
  }, [journeyId, refreshKey, zh]);

  const liveWait = items.some((item) =>
    ["RUNNING", "WAITING_FOR_MEMBERS", "WAITING_FOR_APPROVAL"].includes(item.mission.status),
  );
  useEffect(() => {
    if (!liveWait) return;
    const timer = window.setInterval(() => { void refresh().catch(() => undefined); }, 4000);
    return () => window.clearInterval(timer);
  }, [liveWait, refresh]);

  const resume = async (missionId: string) => {
    const response = await cityNexusApi.resumeJourneyMission(journeyId, missionId);
    setReceipt(response.run);
    await onJourneyUpdated();
    await refresh();
  };

  const act = async (item: PendingJourneyMission, optionKey?: string) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    setReceipt(null);
    try {
      let childId = item.mission.id;
      if (optionKey !== undefined) {
        const answer = await cityNexusApi.answerJourneyClarification(
          journeyId, item.mission.id, item.mission.clarification!.clarification_id!, optionKey,
        );
        childId = answer.child_mission.id;
        setItems((current) => current.map((entry) => entry.mission.id === item.mission.id
          ? { mission: answer.child_mission, run: null } : entry));
      }
      await resume(childId);
    } catch (cause) {
      const body = cause instanceof CityNexusApiError ? cause.body as { detail?: string; error?: { message?: string } } : null;
      const detail = body?.detail ?? body?.error?.message ?? null;
      if (detail === "CLARIFICATION_STALE_RECOMPUTE_REQUIRED") {
        setStaleIds((current) => [...current, item.mission.id]);
        setError(zh ? "行程信息已更新，请按当前行程重新回答。" : "Journey details changed. Answer again for the current journey.");
      } else {
        setError(zh ? "任务继续状态待确认，请刷新任务。" : "Task status is unconfirmed. Refresh the task.");
      }
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };

  const answerCollective = async (item: PendingJourneyMission, proposalId: string) => {
    const collective = item.collective;
    const clarificationId = item.mission.clarification?.clarification_id;
    if (busy || !collective?.viewer_member_id || !clarificationId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const answer = await cityNexusApi.answerCollectiveClarification(
        journeyId,
        item.mission.id,
        collective.viewer_member_id,
        clarificationId,
        proposalId,
      );
      if (answer.child_mission) {
        const mediating = answer.status === "MEDIATION_REQUIRED";
        setNotice(mediating
          ? (zh ? "成员选择不同，助手正在寻找双方都能接受的方案。" : "The travelers chose differently. The assistant is seeking a solution both can accept.")
          : (zh ? "所有相关成员已经回答。助手正在继续处理共同选择。" : "All required travelers answered. The assistant is continuing the shared choice."));
        await resume(answer.child_mission.id);
      } else {
        setNotice(zh ? "你的选择已保存，正在等待其他相关成员。" : "Your choice is saved. Waiting for the other relevant travelers.");
        await refresh();
      }
    } catch (cause) {
      const status = apiStatus(cause);
      setError(
        status === 401
          ? (zh ? "成员身份已失效，请重新建立同行者会话后再回答。" : "Your traveler identity expired. Re-establish the member session before answering.")
          : status === 403
            ? (zh ? "请切换到该成员账号后作答。" : "Switch to that member's account to answer.")
            : status === 409
              ? (zh ? "这个共同决策已经变化或失效，请刷新后按当前状态作答。" : "This shared decision changed or became stale. Refresh before answering.")
              : (zh ? "共同选择结果待确认，请刷新状态。" : "Shared choice is unconfirmed. Refresh the status."),
      );
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };

  const approve = async (item: PendingJourneyMission) => {
    const continuation = item.continuation;
    if (busy || !continuation?.approval_id) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await cityNexusApi.approveAgentAction(journeyId, continuation.approval_id);
      const resumed = result.continuation?.status === "RESUMED";
      setNotice(
        resumed
          ? (zh ? "批准已生效，助手已从原任务继续并完成这一步。" : "Approval took effect. The assistant resumed the original task and completed this step.")
          : (zh ? "批准已经保存，正在等待服务器继续原任务。" : "Approval is saved; the server is continuing the original task."),
      );
      await onJourneyUpdated();
      await refresh();
    } catch (cause) {
      const status = apiStatus(cause);
      setError(
        status === 401
          ? (zh ? "批准身份已失效，请重新建立成员会话。" : "Your approval identity expired. Re-establish the member session.")
          : status === 403
            ? (zh ? "这个成员没有权限批准这次行程变更。" : "This member is not allowed to approve this Journey change.")
            : (zh ? "批准状态待确认，请刷新任务。" : "Approval status is unconfirmed. Refresh the task."),
      );
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };

  if (!items.length && !error && !receipt && !notice) return null;
  return (
    <section className="cn-clarification-panel" aria-label={zh ? "待决策事项" : "Pending decisions"} data-testid="journey-clarification">
      {viewer && (
        <div className="cn-collective-viewer" data-member-id={viewer.member_id}>
          <span>{zh ? "当前成员" : "Current member"}</span>
          <b>{roleLabel(viewer.role, zh)}</b>
        </div>
      )}

      {items.map((item) => {
        const { mission } = item;
        const question = mission.clarification;
        const waiting = mission.status === "WAITING_FOR_USER" && question?.clarification_id;
        const collectiveWaiting = mission.status === "WAITING_FOR_MEMBERS"
          && question?.kind === "COLLECTIVE_TRADEOFF"
          && item.collective;
        const approvalWaiting = mission.status === "WAITING_FOR_APPROVAL" && item.continuation;
        const mediationIntent = mission.resolved_intent?.collective_mediation;
        const mediationReady = mission.parent_mission_id
          && ["CREATED", "DEGRADED"].includes(mission.status)
          && typeof mediationIntent === "object"
          && mediationIntent !== null;
        const mediationRound = mediationReady
          ? Number((mediationIntent as Record<string, unknown>).round ?? 1)
          : 0;

        return (
          <article key={mission.id} data-mission-id={mission.id} data-mission-status={mission.status}>
            {collectiveWaiting ? <div data-testid="collective-decision">
              <div className="cn-collective-heading">
                <div>
                  <h4>{zh ? "这一步需要同行者共同决定" : "This step needs a group decision"}</h4>
                  <p>{zh
                    ? `已回答 ${item.collective!.response_count}/${item.collective!.required_count}。助手会等相关成员都表态后再继续。`
                    : `${item.collective!.response_count}/${item.collective!.required_count} answered. The assistant waits for every relevant traveler before continuing.`}</p>
                </div>
                <span data-testid="collective-progress">{item.collective!.response_count}/{item.collective!.required_count}</span>
              </div>

              <ul className="cn-collective-members" aria-label={zh ? "成员回答状态" : "Member response status"}>
                {item.collective!.required_members.map((member) => (
                  <li key={member.member_id} data-testid="collective-member" data-responded={member.responded ? "true" : "false"} className={member.responded ? "answered" : "waiting"}>
                    <b>{member.display_name || roleLabel(member.role, zh)}{member.is_viewer ? (zh ? "（你）" : " (you)") : ""}</b>
                    <span>{member.responded ? (zh ? "已回答" : "Answered") : (zh ? "等待回答" : "Waiting")}</span>
                  </li>
                ))}
              </ul>

              <div className="cn-collective-options">
                {item.collective!.candidate_options.map((option, index) => (
                  <div key={option.proposal_id} className="cn-collective-option" data-testid="collective-option" data-proposal-id={option.proposal_id}>
                    <b>{candidateLabel(option, index, zh)}</b>
                    <small>{candidateTradeoff(option, zh)}</small>
                    <button
                      type="button"
                      className="v8-secondary"
                      disabled={busy || !item.collective!.viewer_member_id || item.collective!.viewer_has_responded}
                      onClick={() => void answerCollective(item, option.proposal_id)}
                    >
                      {item.collective!.viewer_has_responded
                        ? (zh ? "你的选择已保存" : "Your choice is saved")
                        : (zh ? "选择这个方案" : "Choose this option")}
                    </button>
                  </div>
                ))}
              </div>

              {!item.collective!.viewer_member_id && (
                <small className="cn-collective-session-note">
                  {zh
                    ? "当前账号为只读；登录同行成员账号后可提交答复。"
                    : "Read-only account · sign in as a Journey member to answer."}
                </small>
              )}
            </div> : approvalWaiting ? <div data-testid="collective-approval">
              <div className="cn-approval-wait">
                <h4>{zh ? "共同选择已形成，助手正在等批准" : "The group choice is ready; the assistant is waiting for approval"}</h4>
                <p>{zh
                  ? "批准后将继续已保存的助手任务。"
                  : "Approval resumes the saved assistant task."}</p>
                <small>{zh
                  ? `批准状态：${item.continuation!.approval_status ?? "UNKNOWN"} · 任务状态：${item.continuation!.pending_status}`
                  : `Approval: ${item.continuation!.approval_status ?? "UNKNOWN"} · continuation: ${item.continuation!.pending_status}`}</small>
                {item.continuation!.viewer_can_approve ? (
                  <button type="button" className="v8-primary" data-testid="collective-approve" disabled={busy} onClick={() => void approve(item)}>
                    {zh ? "批准并让助手继续" : "Approve and let the assistant continue"}
                  </button>
                ) : (
                  <small>{zh ? "请由有权限的成员确认这次变更。" : "An authorized member must approve this change."}</small>
                )}
              </div>
              {item.run && <small>{completionLabel(item.run, zh)}</small>}
            </div> : mediationReady ? <div data-testid="collective-mediation">
              <h4>{zh ? "你们意见不同，助手正在做调解" : "You disagree; the assistant is mediating"}</h4>
              <p>{zh
                 ? `第 ${mediationRound} 轮：助手先寻找有事实依据的折中，未解决的取舍交由相关成员选择。`
                 : `Round ${mediationRound}: the assistant seeks a fact-based compromise, then returns open trade-offs to the relevant travelers.`}</p>
              <button type="button" className="v8-primary" disabled={busy} onClick={() => void act(item)}>
                {zh ? "继续调解" : "Continue mediation"}
              </button>
            </div> : waiting ? <>
              <h4>{zh ? "这次旅行，你更看重哪一个？" : "What matters more for this trip?"}</h4>
              <p>{question.question}</p>
              <small>{zh ? "用于完善本次行程。" : "Used to shape this trip."}</small>
              <div className="cn-clarification-options">
                {question.option_keys?.map((key) => <button key={key} type="button" className="v8-secondary"
                  disabled={busy || staleIds.includes(mission.id)} onClick={() => void act(item, key)}>
                  {optionLabel(key, zh)}
                </button>)}
              </div>
            </> : <>
              <p>{mission.status === "RUNNING"
                ? (zh ? "助手正在依据服务器事实继续决策。" : "The assistant is continuing against server facts.")
                : (zh ? "已保存的任务还在等待继续。" : "The saved task is still waiting to continue.")}</p>
              {item.run && <small>{completionLabel(item.run, zh)}</small>}
              {mission.parent_mission_id && ["CREATED", "DEGRADED"].includes(mission.status) &&
                <button type="button" disabled={busy} onClick={() => void act(item)}>{zh ? "继续处理已保存的选择" : "Continue the saved choice"}</button>}
            </>}
          </article>
        );
      })}

      {busy && <p role="status">{zh ? "正在提交并继续处理，请勿重复提交。" : "Saving and continuing; please do not submit again."}</p>}
      {notice && <p role="status" className="cn-collective-notice">{notice}</p>}
      {receipt && <p role="status" data-completion-kind={receipt.completion_contract?.kind ?? receipt.status}>{completionLabel(receipt, zh)}</p>}
      {error && <p role="alert">{error}</p>}
      <button type="button" disabled={busy} onClick={() => {
        setError(null);
        void refresh().catch(() => setError(zh ? "任务状态读取失败，请稍后重试。" : "Task status could not be read. Retry later."));
      }}>{zh ? "刷新任务状态" : "Refresh task status"}</button>
    </section>
  );
}
