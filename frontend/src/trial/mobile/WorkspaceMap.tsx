import { useEffect, useMemo, useRef, useState } from "react";
import type { BootstrapDiscoveryCandidate } from "../../api/citynexus";
import "maplibre-gl/dist/maplibre-gl.css";
import "./WorkspaceMapPreview.css";

export type WorkspaceMapPoint = Omit<Pick<BootstrapDiscoveryCandidate, "candidate_id" | "name" | "latitude" | "longitude" | "provider_provenance" | "selection_state" | "source_url" | "observation_expired" | "region_status">, "coordinate_system"> & {
  coordinate_system: "WGS84" | "GCJ02";
  provider?: string;
  provider_object_id?: string;
  adcode?: string;
  public_address?: Record<string, string>;
  kind?: "place" | "area";
};

const OSM_SOURCE_URL = /^https:\/\/(www\.)?openstreetmap\.org\/(node|way|relation)\/[0-9]+$/;
const AMAP_MARKER_URL = /^https:\/\/uri\.amap\.com\/marker(?:\?.*)?$/;
const ADMIN_ADDRESS_KEYS = ["province", "city", "district", "county", "township", "town"] as const;

function isAmapPoint(place: WorkspaceMapPoint): boolean {
  return typeof place.provider === "string" && place.provider.toLowerCase() === "amap" && place.coordinate_system === "GCJ02";
}

function validPoint(place: WorkspaceMapPoint): boolean {
  return place.region_status !== "CONFLICT" && place.selection_state !== "REGION_CONFLICT"
    && !(typeof place.provider === "string" && place.provider.toLowerCase() === "amap") && place.coordinate_system === "WGS84"
    && Number.isFinite(place.latitude) && Number.isFinite(place.longitude)
    && Math.abs(place.latitude) <= 85 && Math.abs(place.longitude) <= 180;
}

function shortAdministrativeAddress(address?: Record<string, string>): string {
  if (!address) return "";
  return [...new Set(ADMIN_ADDRESS_KEYS.map((key) => typeof address[key] === "string" ? address[key].trim() : "").filter(Boolean))]
    .slice(0, 3).join(" · ");
}

export function WorkspaceMap({ candidates, allowed, onAllow, onSelect, selectedId, traveller }: {
  candidates: WorkspaceMapPoint[]; allowed: boolean; onAllow: () => void; onSelect?: (id: string) => void; selectedId?: string | null;
  traveller?: { latitude: number; longitude: number; label: string; coordinate_system?: string } | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const travellerMarker = useRef<import("maplibre-gl").Marker | null>(null);
  // MapLibre is imported lazily, so the simulated position can arrive before the map object
  // exists.  Without this flag the marker effect ran once against a null map and never again.
  const [mapReady, setMapReady] = useState(false);
  const points = useMemo(() => candidates.filter(validPoint), [candidates]);
  const amapPoints = useMemo(() => candidates.filter((point) => isAmapPoint(point)
    && point.region_status !== "CONFLICT" && point.selection_state !== "REGION_CONFLICT"
    && Number.isFinite(point.latitude) && Number.isFinite(point.longitude)), [candidates]);
  const otherCoordinatePoints = candidates.filter((point) => !validPoint(point) && !isAmapPoint(point)
    && point.region_status !== "CONFLICT" && point.selection_state !== "REGION_CONFLICT");
  // Owner-signed coordinates only. Relative distribution is intentionally NOT a
  // street map, route, travel distance or GCJ02/WGS84 conversion.
  const previewPins = useMemo(() => {
    const sample = points.slice(0, 8);
    if (sample.length === 0) return [];
    const lons = sample.map((p) => p.longitude), lats = sample.map((p) => p.latitude);
    const minLon = Math.min(...lons), maxLon = Math.max(...lons);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const lonSpan = maxLon - minLon, latSpan = maxLat - minLat;
    return sample.map((point, index) => ({
      ...point,
      positionX: lonSpan < 0.00001 ? 50 : 18 + ((point.longitude - minLon) / lonSpan) * 64,
      positionY: latSpan < 0.00001 ? 50 : 18 + ((maxLat - point.latitude) / latSpan) * 64,
      index,
    }));
  }, [points]);
  const previewGroups = useMemo(() => {
    const groups: (typeof previewPins)[] = [];
    for (const pin of previewPins) {
      const group = groups.find(items => Math.hypot(items[0].positionX - pin.positionX, items[0].positionY - pin.positionY) < 20);
      if (group) group.push(pin); else groups.push([pin]);
    }
    return groups;
  }, [previewPins]);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  // A journey can be executing before any research pin exists; the simulated
  // traveller alone is enough to give the classroom map something to show.
  const travellerOnMap = Boolean(
    traveller && (!traveller.coordinate_system || traveller.coordinate_system === "WGS84")
    && Number.isFinite(traveller.latitude) && Number.isFinite(traveller.longitude),
  );
  useEffect(() => {
    if (!allowed || !host.current || (points.length === 0 && !travellerOnMap)) return;
    let disposed = false;
    let map: import("maplibre-gl").Map | undefined;
    let observer: ResizeObserver | undefined;
    const markers: import("maplibre-gl").Marker[] = [];
    setFailed(false);
    void import("maplibre-gl").then(({ default: lib }) => {
      if (disposed || !host.current) return;
      const center: [number, number] = points.length
        ? [points[0].longitude, points[0].latitude]
        : [traveller!.longitude, traveller!.latitude];
      map = new lib.Map({ container: host.current, center, zoom: points.length ? 13 : 14,
        style: { version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm", type: "raster", source: "osm" }] },
        dragRotate: false, pitchWithRotate: false, attributionControl: { compact: true },
      });
      map.addControl(new lib.NavigationControl({ showCompass: false }), "top-right");
      map.on("error", () => { if (!disposed) setFailed(true); });
      mapRef.current = map; setMapReady(true);
      const bounds = new lib.LngLatBounds();
      points.forEach((point, index) => {
        const element = document.createElement("button");
        element.type = "button"; element.className = "rev-workspace-map-pin" + (point.kind === "area" ? " is-area" : "");
        element.textContent = String(index + 1);
        element.setAttribute("aria-label", point.name);
        const content = document.createElement("div");
        const title = document.createElement("strong"); title.textContent = point.name; content.append(title);
        if (point.kind === "area") { const type = document.createElement("p"); type.textContent = "地区／村落线索"; content.append(type); }
        if (point.source_url && OSM_SOURCE_URL.test(point.source_url)) {
          const source = document.createElement("a"); source.textContent = "查看地点来源 ↗";
          source.href = point.source_url; source.target = "_blank"; source.rel = "noreferrer";
          content.append(document.createElement("br"), source);
        }
        element.addEventListener("click", () => onSelect?.(point.candidate_id));
        markers.push(new lib.Marker({ element }).setLngLat([point.longitude, point.latitude])
          .setPopup(new lib.Popup({ offset: 18 }).setDOMContent(content)).addTo(map!));
        bounds.extend([point.longitude, point.latitude]);
      });
      if (points.length > 1) map.fitBounds(bounds, { padding: 50, maxZoom: 15, duration: 0 });
      observer = new ResizeObserver(() => map?.resize()); observer.observe(host.current);
    }).catch(() => { if (!disposed) setFailed(true); });
    return () => { disposed = true; observer?.disconnect(); markers.forEach((marker) => marker.remove()); travellerMarker.current?.remove(); travellerMarker.current = null; mapRef.current = null; setMapReady(false); map?.remove(); };
  }, [allowed, points, onSelect, travellerOnMap]);
  // The simulated traveller is a second marker, kept apart from the numbered pins: it is the
  // only thing on this map that moves, and its coordinates come from the sandbox clock, not
  // from any device location.  GCJ02 is not converted here; it is only drawn as WGS84.
  useEffect(() => {
    const draw = traveller && (!traveller.coordinate_system || traveller.coordinate_system === "WGS84")
      && Number.isFinite(traveller.latitude) && Number.isFinite(traveller.longitude);
    if (!allowed || !mapReady || !draw) { travellerMarker.current?.remove(); travellerMarker.current = null; return; }
    void import("maplibre-gl").then(({ default: lib }) => {
      if (!mapRef.current || !traveller) return;
      if (!travellerMarker.current) {
        const element = document.createElement("div");
        element.className = "rev-workspace-map-traveller";
        element.dataset.testid = "rev-map-traveller";
        element.title = `模拟旅客：${traveller.label}（模拟位置）`;
        element.setAttribute("aria-label", `模拟旅客位置：${traveller.label}`);
        travellerMarker.current = new lib.Marker({ element })
          .setLngLat([traveller.longitude, traveller.latitude]).addTo(mapRef.current);
      } else {
        travellerMarker.current.setLngLat([traveller.longitude, traveller.latitude]);
      }
      // A moving simulated traveller that sits outside the framed pins is invisible on a phone;
      // following it is what makes the demo's blue dot findable without panning by hand.
      mapRef.current.easeTo({ center: [traveller.longitude, traveller.latitude], duration: 300 });
    });
  }, [allowed, mapReady, traveller?.latitude, traveller?.longitude, traveller?.label, traveller?.coordinate_system]);
  return <section aria-label="当前行程地图">
    <p>{travellerOnMap && !points.length && !amapPoints.length
      ? "模拟旅客 1 位 · 暂无研究地点"
      : `OpenStreetMap 地图地点 ${points.length} 处 · 高德地点 ${amapPoints.length} 处`}</p>
    {traveller && <p data-testid="rev-map-traveller-state">模拟旅客：{traveller.label} · {traveller.latitude.toFixed(4)}, {traveller.longitude.toFixed(4)}（{traveller.coordinate_system ?? "WGS84"}，模拟位置，不是物理 GPS）</p>}
    {!points.length && !amapPoints.length && !travellerOnMap && <p>先去探索查找地点，查到后可以从任何页打开此图。</p>}
    {(points.length > 0 || travellerOnMap) && <>
      {!allowed ? <div className="rev-workspace-map-consent">
        <div className="rev-workspace-map-preview" aria-label="已发现地点的坐标分布预览" data-testid="rev-workspace-coordinate-preview">
          <span className="rev-workspace-preview-label">地点分布预览 · 未加载外部底图</span>
          {previewGroups.map((group) => {
            const point = group[0];
            const grouped = group.length > 1;
            return <button type="button" key={point.candidate_id} className={"rev-workspace-preview-pin" + (group.some(p => p.candidate_id === selectedId) ? " is-selected" : "")}
              style={{ left: point.positionX + "%", top: point.positionY + "%", zIndex: 10 + point.index }}
              onClick={() => grouped ? setExpandedGroup(expandedGroup === point.candidate_id ? null : point.candidate_id) : onSelect?.(point.candidate_id)}
              aria-expanded={grouped ? expandedGroup === point.candidate_id : undefined}
              title={group.map(p => p.name).join("、")} aria-label={grouped ? `展开相邻 ${group.length} 处地点` : "查看 " + point.name + " 对应日程"}>
              {point.index + 1}
              {grouped && <span className="rev-workspace-pin-count">{group.length}</span>}
            </button>;
          })}
          <div className="rev-workspace-preview-footer">根据实际坐标显示相对方位，不代表道路或路线</div>
        </div>
        {expandedGroup && <div className="rev-workspace-pin-choices" role="group" aria-label="相邻地点">
          {previewGroups.find(group => group[0].candidate_id === expandedGroup)?.map(point =>
            <button type="button" key={point.candidate_id} onClick={() => onSelect?.(point.candidate_id)} aria-pressed={point.candidate_id === selectedId}>
              {point.index + 1} · {point.name}
            </button>)}
        </div>}
        <p>点击图钉可定位已保存安排；加载 OpenStreetMap 底图后查看街道与详细位置。不会读取 GPS。</p>
        <button type="button" onClick={onAllow}>加载地图</button>
      </div>
        : <div ref={host} className="rev-workspace-map" data-testid="rev-workspace-map-canvas" />}
      {failed && <p role="status">底图暂时没有加载成功，下面的地点列表仍可查看。</p>}
      <ol className="rev-workspace-place-list" aria-label="OpenStreetMap 地点">{points.map((point) => <li key={point.candidate_id} data-selected={point.candidate_id === selectedId}><strong>{point.name}</strong>
        <small>{point.kind === "area" ? "地区／村落线索" : point.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "地点位置"} · {point.observation_expired ? "上次搜索的地点，营业与费用需更新" : point.selection_state === "READY_FOR_NATIVE_PLAN" ? "资料可用于正式排程" : "部分营业或费用资料待核实"}</small>
        {point.source_url && OSM_SOURCE_URL.test(point.source_url) &&
          <a href={point.source_url} target="_blank" rel="noreferrer">查看地点来源 ↗</a>}</li>)}</ol>
    </>}
    {amapPoints.length > 0 && <section aria-label="高德地点" data-testid="rev-amap-research-leads">
      <h3>高德地点</h3>
      <ol className="rev-workspace-place-list">{amapPoints.map((point) => <li key={point.candidate_id} data-selected={point.candidate_id === selectedId}>
        <strong><span aria-hidden="true">📍 </span>{point.name}</strong>
        {shortAdministrativeAddress(point.public_address) && <small>{shortAdministrativeAddress(point.public_address)}</small>}
        {point.source_url && AMAP_MARKER_URL.test(point.source_url) &&
          <a href={point.source_url} target="_blank" rel="noopener noreferrer">在高德地图打开 ↗</a>}
      </li>)}</ol>
    </section>}
    {otherCoordinatePoints.length > 0 && <p>{otherCoordinatePoints.length} 处其他研究地点坐标尚未用于地图。</p>}
  </section>;
}
