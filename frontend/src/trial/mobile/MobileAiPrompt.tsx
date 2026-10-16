import type { FormEvent } from "react";

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
          disabled={busy}
        />
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
