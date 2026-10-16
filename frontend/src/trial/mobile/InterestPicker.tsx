type InterestPickerOption = {
  value: string;
  name: string;
  subtitle: string;
};

type InterestPickerProps<TCategory extends InterestPickerOption> = {
  categories: readonly TCategory[];
  category: TCategory["value"];
  centerBasis: "EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK" | null;
  sampleProviderMode: boolean;
  expectedRecipient: string | null;
  readinessStatus: "checking" | "ready" | "blocked" | "error";
  readinessReady: boolean;
  busy: boolean;
  onCategoryChange: (value: TCategory["value"]) => void;
  onRetryReadiness: () => void;
  onDiscover: () => void;
  onChangeArea: () => void;
};

export function InterestPicker<TCategory extends InterestPickerOption,>({
  categories,
  category,
  centerBasis,
  sampleProviderMode,
  expectedRecipient,
  readinessStatus,
  readinessReady,
  busy,
  onCategoryChange,
  onRetryReadiness,
  onDiscover,
  onChangeArea,
}: InterestPickerProps<TCategory>) {
  return (
    <div className="rev-quick-pane" data-testid="rev-quick-category">
      <h3>这次想看些什么？</h3>
      <div className="rev-quick-categories">
        {categories.map((item) => (
          <button
            type="button"
            className={category === item.value ? "is-chosen" : ""}
            key={item.value}
            onClick={() => onCategoryChange(item.value)}
            disabled={busy}
            aria-pressed={category === item.value}
          >
            <strong>{item.name}</strong><small>{item.subtitle}</small>
          </button>
        ))}
      </div>
      <p className="rev-quick-disclosure">
        {centerBasis === "EXPLICIT_GEOCODER_APPROX"
          ? "使用你选择的区域中心搜索，范围约 2.5 公里。可返回更换区域。"
          : "你已选择公开地图位置。"}
        {sampleProviderMode
          ? "搜索时将所选区域和类别发送至 TEST_PROVIDER。"
          : `搜索时将所选区域和类别发送至 ${expectedRecipient || "公开地图服务"}。`}
        搜索按你选择的区域进行，手机定位需单独授权。
      </p>
      {readinessStatus !== "ready" && (
        <p className="rev-quick-alert neutral" role="status">
          {readinessStatus === "checking"
          ? "正在检查地图服务…"
            : readinessStatus === "blocked"
              ? "公开地点服务暂不可用。"
              : "无法读取地图服务状态，请稍后重试。"}
          {readinessStatus !== "checking" && (
            <button type="button" className="rev-quick-secondary" onClick={onRetryReadiness} disabled={busy}>
              重新检查服务
            </button>
          )}
        </p>
      )}
      <div className="rev-quick-actions">
        <button
          type="button"
          className="rev-quick-primary"
          onClick={onDiscover}
          disabled={busy || !readinessReady}
          data-testid="rev-quick-find-places"
        >
          {busy ? "正在寻找真实地点…" : "搜索附近地点 →"}
        </button>
        <button type="button" className="rev-quick-text-btn" onClick={onChangeArea}>换一个位置</button>
      </div>
    </div>
  );
}
