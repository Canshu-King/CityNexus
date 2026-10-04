import { useCallback, useEffect, useState } from "react";
import {
  cityNexusApi,
  CityNexusApiError,
  type AgentRun,
  type PendingJourneyMission,
} from "../../api/citynexus";

function optionLabel(key: string, zh: boolean): string {
  if (key === "TAKE_NOW") return zh ? "优先当前机会" : "Prefer the current opportunity";
  if (key === "TAKE_LATER") return zh ? "保留资源给后续机会" : "Preserve resources for the later opportunity";
  return key;
}

function completionLabel(run: AgentRun, zh: boolean): string {
  const kind = run.completion_contract?.kind;
  if (kind === "MUTATION_EXECUTED") return zh ? "服务器已确认执行变化。" : "The server confirmed an execution change.";
  if (kind === "NO_ACTION") return zh ? "服务器确认本次不改动行程。" : "The server confirmed no change for this decision.";
  if (kind === "APPROVAL_PENDING") return zh ? "方案等待批准，尚未确认执行。" : "Approval is pending; execution is not confirmed.";
  if (run.status === "FAILED_EXTERNAL" || run.status === "UNAVAILABLE") {
    return zh ? "答案已保存，但模型未完成后续任务。" : "Your answer was saved, but the model did not finish the follow-up.";
  }
  return zh ? "答案已保存，服务器尚未确认这次决策已解决。" : "Your answer was saved; the server has not confirmed this decision is resolved.";
}

/** Questions/options come only from persisted server missions, never from model prose. */
export function JourneyClarificationPanel({ journeyId, refreshKey, zh, onJourneyUpdated }: {
  journeyId: string;
  refreshKey: number;
  zh: boolean;
  onJourneyUpdated: () => Promise<void>;
}) {
  const [items, setItems] = useState<PendingJourneyMission[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staleIds, setStaleIds] = useState<string[]>([]);
  const [receipt, setReceipt] = useState<AgentRun | null>(null);
  const refresh = useCallback(async () => {
    const response = await cityNexusApi.getPendingJourneyMissions(journeyId);
    setItems(response.items);
  }, [journeyId]);

  useEffect(() => {
    let active = true;
    cityNexusApi.getPendingJourneyMissions(journeyId).then(
      (response) => { if (active) setItems(response.items); },
      () => { if (active) setError(zh ? "暂时读不到待回答任务，可重试读取。" : "Pending decisions could not be loaded. Retry the read."); },
    );
    return () => { active = false; };
  }, [journeyId, refreshKey, zh]);

  const running = items.some((item) => item.mission.status === "RUNNING");
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => { void refresh().catch(() => undefined); }, 5000);
    return () => window.clearInterval(timer);
  }, [running, refresh]);

  const resume = async (missionId: string) => {
    const response = await cityNexusApi.resumeJourneyMission(journeyId, missionId);
    setReceipt(response.run);
    // A failed model may already have executed a governed tool. Always reread truth.
    await onJourneyUpdated();
    await refresh();
  };

  const act = async (item: PendingJourneyMission, optionKey?: string) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      let childId = item.mission.id;
      if (optionKey !== undefined) {
        const answer = await cityNexusApi.answerJourneyClarification(
          journeyId, item.mission.id, item.mission.clarification!.clarification_id!, optionKey,
        );
        childId = answer.child_mission.id;
        // Replace the answered question before calling the model: retry resumes the child,
        // it does not submit the human answer twice, including after a page reload.
        setItems((current) => current.map((entry) => entry.mission.id === item.mission.id
          ? { mission: answer.child_mission, run: null } : entry));
      }
      await resume(childId);
    } catch (cause) {
      const detail = cause instanceof CityNexusApiError ? (cause.body as { detail?: string })?.detail : null;
      if (detail === "CLARIFICATION_STALE_RECOMPUTE_REQUIRED") {
        setStaleIds((current) => [...current, item.mission.id]);
        setError(zh ? "行程或证据已变化，这道旧问题不能再作答。请按当前行程重新发起决策。" : "The journey or evidence changed. This question is stale; start a decision against the current journey.");
      } else {
        setError(zh ? "暂时未得到继续执行的确认。请刷新任务状态，已保存的答案不会重复提交。" : "Continuation was not confirmed. Refresh the task status; saved answers are not resubmitted.");
      }
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };

  if (!items.length && !error && !receipt) return null;
  return (
    <section className="cn-clarification-panel" aria-label={zh ? "待决策事项" : "Pending decisions"} data-testid="journey-clarification">
      {items.map((item) => {
        const { mission } = item;
        const question = mission.clarification;
        const waiting = mission.status === "WAITING_FOR_USER" && question?.clarification_id;
        return (
          <article key={mission.id} data-mission-id={mission.id}>
            {waiting ? <>
              <h4>{zh ? "这次旅行，你更看重哪一个？" : "What matters more for this trip?"}</h4>
              <p>{question.question}</p>
              <small>{zh ? "只用于本次行程；答案会交给助手继续验证和执行，不会扩大权限。" : "This journey only. The assistant continues through normal verification and authority boundaries."}</small>
              <div className="cn-clarification-options">
                {question.option_keys?.map((key) => <button key={key} type="button" className="v8-secondary"
                  disabled={busy || staleIds.includes(mission.id)} onClick={() => void act(item, key)}>
                  {optionLabel(key, zh)}
                </button>)}
              </div>
            </> : <>
              <p>{mission.status === "RUNNING"
                ? (zh ? "助手正在依据服务器事实继续决策。" : "The assistant is continuing against server facts.")
                : (zh ? "你的答案已保存，后续任务尚未完成。" : "Your answer is saved; the follow-up is unfinished.")}</p>
              {item.run && <small>{completionLabel(item.run, zh)}</small>}
              {mission.parent_mission_id && ["CREATED", "DEGRADED"].includes(mission.status) &&
                <button type="button" disabled={busy} onClick={() => void act(item)}>{zh ? "继续处理已保存的选择" : "Continue the saved choice"}</button>}
            </>}
          </article>
        );
      })}
      {busy && <p role="status">{zh ? "正在提交并继续处理，请勿重复提交。" : "Saving and continuing; please do not submit again."}</p>}
      {receipt && <p role="status" data-completion-kind={receipt.completion_contract?.kind ?? receipt.status}>{completionLabel(receipt, zh)}</p>}
      {error && <p role="alert">{error}</p>}
      <button type="button" disabled={busy} onClick={() => {
        setError(null);
        void refresh().catch(() => setError(zh ? "任务状态读取失败，请稍后重试。" : "Task status could not be read. Retry later."));
      }}>{zh ? "刷新任务状态" : "Refresh task status"}</button>
    </section>
  );
}
