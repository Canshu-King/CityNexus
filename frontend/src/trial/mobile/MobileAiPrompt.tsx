import type { FormEvent } from "react";

const NEXT_DAY_REST_PREFERENCE = "时间窗：次日14:00后出发；上午不排活动，留足休息。";
const SHORT_WALK_PREFERENCE = "偏好：低体力同行，少走路，优先短路线。";
const RAIN_CONFLICT_PREFERENCE = "只排已核实开放且可达的两站；未知标待核实。先核实午后雨情，下雨给室内备选；冲突先问我改计划。";

function togglePromptPreference(value: string, preference: string) {
  const lines = value.split("\n");
  if (lines.includes(preference)) {
    return lines.filter((line) => line !== preference).join("\n");
  }
  return `${value}${value.trim() ? "\n" : ""}${preference}`;
}

function preferenceFits(value: string, preference: string) {
  return value.split("\n").includes(preference) ||
    value.length + (value.trim() ? 1 : 0) + preference.length <= 360;
}

export type MobileAiAdvice = {
  category: string | null;
  reason: string;
  verifiedTool: boolean;
  model: string | null;
};

export function MobileAiPrompt({
  value,
  busy,
  configured,
  checking = false,
  advice,
  onChange,
  onSubmit,
}: {
  value: string;
  busy: boolean;
  configured: boolean;
  checking?: boolean;
  advice: MobileAiAdvice | null;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };
  const restPreferenceAdded = value.split("\n").includes(NEXT_DAY_REST_PREFERENCE);
  const shortWalkPreferenceAdded = value.split("\n").includes(SHORT_WALK_PREFERENCE);
  const restPreferenceFits = preferenceFits(value, NEXT_DAY_REST_PREFERENCE);
  const shortWalkPreferenceFits = preferenceFits(value, SHORT_WALK_PREFERENCE);
  const rainPreferenceAdded = value.split("\n").includes(RAIN_CONFLICT_PREFERENCE);
  const rainPreferenceFits = preferenceFits(value, RAIN_CONFLICT_PREFERENCE);
  const promptRows = Math.min(10, Math.max(2, value.split("\n").reduce(
    (rows, line) => rows + Math.max(1, Math.ceil(line.length / 16)),
    0,
  )));

  return (
    <section className="rev-quick-ai" data-testid="rev-quick-ai-guide">
      <div className="rev-quick-ai-title">
        <strong>想让 AI 帮你想玩法？</strong>
        <small>{checking ? "正在连接 AI…" : configured ? "可请求 AI 建议" : "AI 建议暂不可用 · 可手动选地点"}</small>
      </div>
      <form onSubmit={submit}>
        <label htmlFor="rev-quick-ai-prompt">写下你的想法</label>
        <textarea
          id="rev-quick-ai-prompt"
          value={value}
          maxLength={360}
          rows={promptRows}
          style={{ maxHeight: "none" }}
          onChange={(event) => onChange(event.target.value)}
          placeholder="比如：今晚想吃点当地特色，再轻松散散步。"
        />
        <div className="rev-quick-ai-preferences">
          <button
            type="button"
            className="rev-quick-secondary"
            aria-pressed={restPreferenceAdded}
            disabled={busy || !restPreferenceFits}
            onClick={() => onChange(togglePromptPreference(value, NEXT_DAY_REST_PREFERENCE))}
            data-testid="rev-quick-ai-rest-preference"
          >
            {restPreferenceAdded
              ? "已加入：不排上午 · 留足休息（点按移除）"
              : "加上时间窗：13:30 起床 · 14:00 后出发"}
          </button>
          <button
            type="button"
            className="rev-quick-secondary"
            aria-pressed={shortWalkPreferenceAdded}
            disabled={busy || !shortWalkPreferenceFits}
            onClick={() => onChange(togglePromptPreference(value, SHORT_WALK_PREFERENCE))}
            data-testid="rev-quick-ai-short-walk-preference"
          >
            {shortWalkPreferenceAdded
              ? "已加入：低体力 · 短路线（点按移除）"
              : "加上偏好：低体力同行 · 少步行"}
          </button>
          <button
            type="button"
            className="rev-quick-secondary"
            aria-pressed={rainPreferenceAdded}
            disabled={busy || !rainPreferenceFits}
            onClick={() => onChange(togglePromptPreference(value, RAIN_CONFLICT_PREFERENCE))}
            data-testid="rev-quick-ai-rain-conflict-preference"
          >
            {rainPreferenceAdded
              ? "已加入：雨天备选 · 冲突可改计划（点按移除）"
              : "加上偏好：核实两站 · 雨天室内备选"}
          </button>
        </div>
        <div className="rev-quick-ai-actions">
          <button
            type="submit"
            disabled={busy || checking || !configured || value.trim().length < 4}
            data-testid="rev-quick-consult-ai"
          >{busy ? "正在请教 AI…" : checking ? "正在连接 AI…" : "问问 AI →"}</button>
          <span>点击后发送这段文字。</span>
        </div>
      </form>
      {advice && (
        <div className="rev-quick-ai-response" role="status" data-testid="rev-quick-ai-response">
          <strong>{advice.verifiedTool ? "AI 给你的探索建议" : "本次没有生成建议"}</strong>
          <p>{advice.reason}</p>
          {advice.category && <span>建议兴趣：{advice.category}（可以修改）</span>}
          <small>{advice.verifiedTool ? "可修改" : "改写想法后再试"}{advice.model ? ` · ${advice.model}` : ""}</small>
        </div>
      )}
    </section>
  );
}
