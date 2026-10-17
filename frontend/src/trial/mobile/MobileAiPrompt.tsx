import type { FormEvent } from "react";

const NEXT_DAY_REST_PREFERENCE = "偏好：次日中午后出发，留足休息时间。";

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
  const restPreferenceAdded = value.includes(NEXT_DAY_REST_PREFERENCE);
  const restPreferenceFits = restPreferenceAdded ||
    value.length + (value.trim() ? 1 : 0) + NEXT_DAY_REST_PREFERENCE.length <= 360;

  const toggleRestPreference = () => {
    if (restPreferenceAdded) {
      const appendedPreference = `\n${NEXT_DAY_REST_PREFERENCE}`;
      onChange(value.endsWith(appendedPreference)
        ? value.slice(0, -appendedPreference.length)
        : value.replace(NEXT_DAY_REST_PREFERENCE, ""));
      return;
    }
    onChange(`${value}${value.trim() ? "\n" : ""}${NEXT_DAY_REST_PREFERENCE}`);
  };

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
          rows={2}
          onChange={(event) => onChange(event.target.value)}
          placeholder="比如：今晚想吃点当地特色，再轻松散散步。"
        />
        <div className="rev-quick-ai-preferences">
          <button
            type="button"
            className="rev-quick-secondary"
            aria-pressed={restPreferenceAdded}
            disabled={busy || !restPreferenceFits}
            onClick={toggleRestPreference}
            data-testid="rev-quick-ai-rest-preference"
          >
            {restPreferenceAdded
              ? "已加入：中午后出发 · 留足休息（点按移除）"
              : "加上偏好：次日中午后出发 · 留足休息"}
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
