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
  advice,
  onChange,
  onSubmit,
}: {
  value: string;
  busy: boolean;
  configured: boolean;
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
        <small>{configured ? "可主动请求真实模型建议" : "AI 还未接通，可先手动找地点"}</small>
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
            disabled={busy || !configured || value.trim().length < 4}
            data-testid="rev-quick-consult-ai"
          >{busy ? "正在请教 AI…" : "问问 AI →"}</button>
          <span>只在你点击后发送这段文字；不会自动查地图、保存行程或预订。</span>
        </div>
      </form>
      {advice && (
        <div className="rev-quick-ai-response" role="status" data-testid="rev-quick-ai-response">
          <strong>{advice.verifiedTool ? "AI 给你的探索建议" : "模型这次未完成工具建议"}</strong>
          <p>{advice.reason}</p>
          {advice.category && <span>建议兴趣：{advice.category}（可以修改）</span>}
          <small>{advice.verifiedTool
            ? "来自真实模型的只读工具建议，不是已规划路线，也没有发生 AgentRun。"
            : "没有得到可校验的工具调用，不能当作 AI 规划已完成。"}{advice.model ? ` · ${advice.model}` : ""}</small>
        </div>
      )}
    </section>
  );
}
