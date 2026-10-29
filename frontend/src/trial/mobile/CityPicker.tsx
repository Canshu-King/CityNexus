import { useEffect, useRef, useState } from "react";
import { PublicCityAreaPicker, type PublicCityCenter } from "../../features/discovery/PublicCityAreaPicker";
import type { BootstrapCitySearchResponse, BootstrapCitySearchResult } from "../../api/citynexus";
import { MobileAiPrompt, type MobileAiAdvice } from "./MobileAiPrompt";

type CityPickerProps = {
  query: string;
  cityResults: BootstrapCitySearchResult[];
  cityFocus: { latitude: number; longitude: number } | null;
  cityFocusLabel: string | null;
  mapFallbackOpen: boolean;
  photonFallbackAvailable: boolean;
  selectedPin: PublicCityCenter | null;
  busy: boolean;
  cityProviderKey?: BootstrapCitySearchResponse["provider_key"] | undefined;
  sampleProviderMode: boolean;
  tilesEnabled: boolean;
  mapLink: string;
  aiGoal: string;
  showAiPrompt?: boolean;
  leadWithAgent: boolean;
  secondary?: boolean;
  agentConfigured: boolean;
  agentChecking?: boolean;
  aiAdvice: MobileAiAdvice | null;
  onQueryChange: (value: string) => void;
  onCityLookup: () => void;
  onPhotonCityLookup: () => void;
  onCityResultSelect: (item: BootstrapCitySearchResult) => void;
  onUseCenter: (
    point: { latitude: number; longitude: number },
    basis: "EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK",
  ) => void;
  onEnableTiles: () => void;
  onMapSelect: (point: PublicCityCenter) => void;
  onMapLinkChange: (value: string) => void;
  onApplyMapLink: () => void;
  onAiGoalChange: (value: string) => void;
  onAskAi: () => void;
};

export function CityPicker({
  query,
  cityResults,
  cityFocus,
  cityFocusLabel,
  mapFallbackOpen,
  photonFallbackAvailable,
  selectedPin,
  busy,
  cityProviderKey,
  sampleProviderMode,
  tilesEnabled,
  mapLink,
  aiGoal,
  showAiPrompt = true,
  leadWithAgent,
  secondary = false,
  agentConfigured,
  agentChecking = false,
  aiAdvice,
  onQueryChange,
  onCityLookup,
  onPhotonCityLookup,
  onCityResultSelect,
  onUseCenter,
  onEnableTiles,
  onMapSelect,
  onMapLinkChange,
  onApplyMapLink,
  onAiGoalChange,
  onAskAi,
}: CityPickerProps) {
  const [pendingAction, setPendingAction] = useState<"city-lookup" | "ai-request" | null>(null);
  const mapFallbackRef = useRef<HTMLDivElement | null>(null);
  const cityLookupPending = busy && pendingAction === "city-lookup";
  const aiRequestPending = busy && pendingAction === "ai-request";

  useEffect(() => {
    if (!mapFallbackOpen) return;
    const frame = window.requestAnimationFrame(() => {
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      mapFallbackRef.current?.scrollIntoView({
        behavior: reducedMotion ? "instant" : "smooth",
        block: "center",
        inline: "nearest",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [mapFallbackOpen]);

  const agentPrompt = showAiPrompt ? <MobileAiPrompt
    value={aiGoal}
    busy={busy}
    requestPending={aiRequestPending}
    configured={agentConfigured}
    checking={agentChecking}
    advice={aiAdvice}
    onChange={onAiGoalChange}
    onSubmit={() => {
      setPendingAction("ai-request");
      onAskAi();
    }}
  /> : null;

  const pane = (
    <div className="rev-quick-pane" data-testid="rev-quick-area">
      <h3 className="rev-quick-area-title">先选一个地区</h3>
      <p className="rev-quick-area-intro">使用所选区域搜索附近地点。</p>
      <label htmlFor="rev-quick-search">城市或地区</label>
      <div className="rev-quick-inline">
        <input
          id="rev-quick-search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="比如：连城县，福建龙岩"
          maxLength={120}
          disabled={busy}
        />
        <button
          type="button"
          onClick={() => {
            setPendingAction("city-lookup");
            onCityLookup();
          }}
          disabled={busy}
          data-testid="rev-quick-find-city"
        >
          {cityLookupPending ? "查询中…" : "查找位置 →"}
        </button>
      </div>
      {cityProviderKey !== undefined && (
        <p className="rev-quick-disclosure">
          {cityProviderKey === "nominatim"
            ? "刚才的地名来自 Nominatim。"
            : cityProviderKey === "photon"
              ? "刚才的地名来自 Photon。"
              : cityProviderKey === null
                ? "这次没有调用地名服务。"
                : "刚才用的是演示地点数据。"}
        </p>
      )}
      {photonFallbackAvailable && !sampleProviderMode && (
        <div className="rev-quick-photon-fallback" data-testid="rev-quick-photon-fallback">
          <p className="rev-quick-disclosure">
            备用搜索会把“{query}”发送至 Photon（Komoot 公开地名服务）。
          </p>
          <button
            type="button"
            className="rev-quick-secondary"
            onClick={() => {
              setPendingAction("city-lookup");
              onPhotonCityLookup();
            }}
            disabled={busy}
            data-testid="rev-quick-photon-search"
          >
            {cityLookupPending ? "正在用 Photon 查找…" : "改用 Photon 地名查找 →"}
          </button>
        </div>
      )}
      {cityResults.length > 0 && (
        <div className="rev-quick-results" data-testid="rev-quick-city-results">
          <h3>是这些地方吗？</h3>
          {cityResults.map((item) => (
            <button
              type="button"
              className="rev-quick-city-option"
              key={item.result_id}
              onClick={() => onCityResultSelect(item)}
            >
              <strong>{item.display_name || item.name}</strong>
              <small>{item.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "公开地点"} · 搜索中心</small>
              <span>就从这个公开地区中心附近找（约2.5公里） →</span>
            </button>
          ))}
        </div>
      )}
      {cityFocus && (
        <div className="rev-quick-map-step">
          <h3>已找到：{cityFocusLabel || "当前地区"}</h3>
          <p className="rev-quick-disclosure">
            搜索中心取自公开地名结果，范围约 2.5 公里。你可以从附近查找或调整地图。
          </p>
          <button
            type="button"
            className="rev-quick-primary rev-quick-continue"
            data-testid="rev-quick-use-approx-center"
            onClick={() => {
              // This explicit user selection makes a PUBLIC, approximate
              // center the user-directed search area. It does NOT invent a
              // MAP_TAP provenance or silently send provider requests.
              onUseCenter({
                latitude: cityFocus.latitude,
                longitude: cityFocus.longitude,
              }, "EXPLICIT_GEOCODER_APPROX");
            }}
          >直接从这片地区附近找 →</button>
          <details className="rev-quick-optional-map">
            <summary>想换具体位置？可以打开地图（可选）</summary>
            <p className="rev-quick-disclosure">可选：点击下方按钮加载地图。</p>
            {!tilesEnabled ? (
              <button
                type="button"
                className="rev-quick-secondary"
                onClick={onEnableTiles}
                data-testid="rev-quick-load-map"
              >
                加载 OpenStreetMap 地图
              </button>
            ) : (
              <>
                <PublicCityAreaPicker
                  selectedCenter={selectedPin}
                  focusCenter={cityFocus}
                  mobileFirst
                  onSelect={onMapSelect}
                />
              </>
            )}
          </details>
        </div>
      )}
      {mapFallbackOpen && !cityFocus && (
        <div className="rev-quick-map-step" data-testid="rev-quick-map-fallback" ref={mapFallbackRef}>
          <h3>在地图上选区域</h3>
          <p className="rev-quick-disclosure">
            地图底图来自 OpenStreetMap。拖动到你所在区域，再轻触地图确定搜索中心；这不会读取设备定位，也不代表地名搜索结果。
          </p>
          <PublicCityAreaPicker
            selectedCenter={selectedPin}
            fallbackCameraCenter={{ latitude: 35, longitude: 105 }}
            mobileFirst
            onSelect={onMapSelect}
          />
        </div>
      )}
      <details className="rev-quick-internals">
        <summary>想用公开 OpenStreetMap 链接定位？（可选）</summary>
        <label htmlFor="rev-quick-map-link">公开地图链接</label>
        <input
          id="rev-quick-map-link"
          type="url"
          value={mapLink}
          onChange={(e) => onMapLinkChange(e.target.value)}
          placeholder="https://www.openstreetmap.org/#map=13/25.7/116.75"
        />
        <button type="button" onClick={onApplyMapLink} data-testid="rev-quick-apply-map-link">使用这个公开地图位置</button>
      </details>
    </div>
  );

  // Folding the manual area search away must never fold the Agent prompt away with it: the prompt is
  // the main road, so it always stays outside the <details>.
  const promptFirst = leadWithAgent ? agentPrompt : null;
  const promptLast = leadWithAgent ? null : agentPrompt;
  if (!secondary) return <>{promptFirst}{pane}{promptLast}</>;
  return (
    <>
      {promptFirst}
      {/* The screen's own sentence says 这里可以手动查找地点, so the query key must not wait behind a
          closed layer -- measured on the clean tip: after the plan screen's 补上没排地点的那段时间 hand,
          rev-quick-find-city reported isVisible=false even when scrolled to centre. */}
      <details className="rev-quick-secondary" data-testid="rev-quick-area-secondary" open>
        <summary>我想自己先挑地点（可选）</summary>
        {pane}
      </details>
      {promptLast}
    </>
  );
}
