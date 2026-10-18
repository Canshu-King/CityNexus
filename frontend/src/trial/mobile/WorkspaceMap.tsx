import { useEffect, useMemo, useRef, useState } from "react";
import type { BootstrapDiscoveryCandidate } from "../../api/citynexus";
import "maplibre-gl/dist/maplibre-gl.css";

export type WorkspaceMapPoint = Pick<BootstrapDiscoveryCandidate, "candidate_id" | "name" | "latitude" | "longitude" | "coordinate_system" | "provider_provenance" | "selection_state" | "source_url" | "observation_expired">;

function validPoint(place: WorkspaceMapPoint): boolean {
  return place.coordinate_system === "WGS84" && Number.isFinite(place.latitude) && Number.isFinite(place.longitude)
    && Math.abs(place.latitude) <= 85 && Math.abs(place.longitude) <= 180;
}

export function WorkspaceMap({ candidates, allowed, onAllow }: {
  candidates: WorkspaceMapPoint[]; allowed: boolean; onAllow: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const points = useMemo(() => candidates.filter(validPoint), [candidates]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!allowed || !host.current || points.length === 0) return;
    let disposed = false;
    let map: import("maplibre-gl").Map | undefined;
    let observer: ResizeObserver | undefined;
    const markers: import("maplibre-gl").Marker[] = [];
    setFailed(false);
    void import("maplibre-gl").then(({ default: lib }) => {
      if (disposed || !host.current) return;
      map = new lib.Map({ container: host.current, center: [points[0].longitude, points[0].latitude], zoom: 13,
        style: { version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm", type: "raster", source: "osm" }] },
        dragRotate: false, pitchWithRotate: false, attributionControl: { compact: true },
      });
      map.addControl(new lib.NavigationControl({ showCompass: false }), "top-right");
      map.on("error", () => { if (!disposed) setFailed(true); });
      const bounds = new lib.LngLatBounds();
      points.forEach((point, index) => {
        const element = document.createElement("button");
        element.type = "button"; element.className = "rev-workspace-map-pin";
        element.textContent = String(index + 1);
        element.setAttribute("aria-label", point.name);
        const text = `${point.name}\n${point.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "已保存的地点坐标"}`;
        markers.push(new lib.Marker({ element }).setLngLat([point.longitude, point.latitude])
          .setPopup(new lib.Popup({ offset: 18 }).setText(text)).addTo(map!));
        bounds.extend([point.longitude, point.latitude]);
      });
      if (points.length > 1) map.fitBounds(bounds, { padding: 50, maxZoom: 15, duration: 0 });
      observer = new ResizeObserver(() => map?.resize()); observer.observe(host.current);
    }).catch(() => { if (!disposed) setFailed(true); });
    return () => { disposed = true; observer?.disconnect(); markers.forEach((marker) => marker.remove()); map?.remove(); };
  }, [allowed, points]);
  return <section aria-label="当前行程地图">
    <p>已找到 {points.length} 处有坐标的地点。营业和费用未知，也可以先在地图上查看。</p>
    {candidates.length > points.length && <p>{candidates.length - points.length} 处地点暂无可用坐标。</p>}
    {!points.length ? <p>先去探索查找地点，查到后可以从任何页打开此图。</p> : <>
      {!allowed ? <div className="rev-workspace-map-consent"><p>加载 OpenStreetMap 公开底图，地图服务会收到显示区域的瓦片请求。不读取 GPS。</p>
        <button type="button" onClick={onAllow}>加载地图</button></div>
        : <div ref={host} className="rev-workspace-map" data-testid="rev-workspace-map-canvas" />}
      {failed && <p role="status">底图暂时没有加载成功，下面的地点列表仍可查看。</p>}
      <ol className="rev-workspace-place-list">{points.map((point) => <li key={point.candidate_id}><strong>{point.name}</strong>
        <small>{point.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "地点位置"} · {point.observation_expired ? "上次搜索的地点，营业与费用需更新" : point.selection_state === "READY_FOR_NATIVE_PLAN" ? "资料可用于正式排程" : "部分营业或费用资料待核实"}</small>
        {point.source_url && /^https:\/\/(www\.)?openstreetmap\.org\/(node|way|relation)\/[0-9]+$/.test(point.source_url) &&
          <a href={point.source_url} target="_blank" rel="noreferrer">查看地点来源 ↗</a>}</li>)}</ol>
    </>}
  </section>;
}
