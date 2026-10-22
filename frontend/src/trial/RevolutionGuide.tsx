import { useState } from "react";

/**
 * Real first-person wayfinding over the existing R107/R108 product component.
 * Only exposes/focuses existing controls. Never fabricates a POI, route,
 * credential, consent, or AgentRun.
 */
export function RevolutionGuide({ cityName }: { cityName: string }) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [hint, setHint] = useState<string | null>(null);

  const reveal = () => {
    const details = document.querySelector<HTMLDetailsElement>(".rev-discovery-details");
    if (details) details.open = true;
  };

  const goTo = (selector: string) => {
    const target = document.querySelector<HTMLElement>(selector);
    if (!target) return false;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    return true;
  };

  const chooseArea = () => {
    setStep(1);
    setHint("搜索「连城县」或在地图选区，然后确认位置。");
    reveal();
    if (goTo('[data-testid="bootstrap-public-area-picker"]')) return;
    const start = document.querySelector<HTMLButtonElement>('[data-testid="bootstrap-source-manual"]');
    if (start) {
      start.click();
      window.setTimeout(() => goTo('[data-testid="bootstrap-public-area-picker"]'), 80);
    } else {
      setHint("地图选择组件正在加载，请稍等或刷新页面。");
    }
  };

  const findPlaces = () => {
    setStep(2);
    setHint("选一个兴趣类别，核对地图中心，勾选本次公开数据查询授权，再点「搜索附近地点」。");
    reveal();
    window.setTimeout(() => {
      if (!goTo('[data-testid="bootstrap-outing-intents"]')) {
        setHint("请先完成上一步，选择好公开地图区域。");
      }
    }, 40);
  };

  const saveWalk = () => {
    setStep(3);
    setHint("搜索后选择两个地点，保存私人步行计划。");
    reveal();
    window.setTimeout(() => {
      if (!goTo('[data-testid="bootstrap-discovery-pocket-walk"]') &&
          !goTo('[data-testid="bootstrap-shortlist"]')) {
        setHint("还没有地点可以保存。先搜索附近地点。");
      }
    }, 40);
  };

  return (
    <section className="rev-guide" data-testid="revolution-guided-journey">
      <div className="rev-guide-heading">
        <span className="rev-guide-overline">开始探索</span>
        <h2>探索{cityName}，只需三步。</h2>
        <p>搜索并选择两个地点，按下方步骤开始散步。</p>
      </div>
      <div className="rev-guide-steps" aria-label="探索步骤">
        <button type="button" onClick={chooseArea} className={step === 1 ? "is-current" : ""}>
          <span className="rev-guide-index">01</span>
          <strong>选一个地方</strong>
          <small>搜索连城或在地图上选点</small>
          <span>去选地图 →</span>
        </button>
        <button type="button" onClick={findPlaces} className={step === 2 ? "is-current" : ""}>
          <span className="rev-guide-index">02</span>
          <strong>找好玩的</strong>
          <small>选兴趣、授权搜索真实地点</small>
          <span>去搜索 →</span>
        </button>
        <button type="button" onClick={saveWalk} className={step === 3 ? "is-current" : ""}>
          <span className="rev-guide-index">03</span>
          <strong>开始散步</strong>
          <small>挑两站、保存并进入 GO MODE</small>
          <span>去保存路线 →</span>
        </button>
      </div>
      {hint && <p className="rev-guide-hint" role="status">{hint}</p>}
      <p className="rev-guide-disclaimer">
        查询公开地点前需你确认；AI 会生成探索建议。
      </p>
    </section>
  );
}
