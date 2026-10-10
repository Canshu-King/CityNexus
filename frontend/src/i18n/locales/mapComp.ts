// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const mapComp = {
  en: {

  // ── Map components ──
  "mapComp.attribution": "© OpenStreetMap contributors",
  "mapComp.yourLocation": "Your location · {n} m accuracy",
  "mapComp.journeyMap": "Journey map",
  "mapComp.routeContext": "Route context",
  "mapComp.legs": "{n} {plural:leg}",
  "mapComp.providerRoute": "Provider-backed route · WGS84",
  "mapComp.noRouteNoProvider": "No route is drawn: this deployment has no routing provider configured, so this plan holds no legs at all.",
  "mapComp.noRouteNotRouted": "No route is drawn: this plan holds no legs, so nothing on the map came from a routing provider.",
  "mapComp.disruptionScope": "Disruption scope",
  "mapComp.maplibreLabel": "MapLibre Journey map",
  /* ORD-0417: a tap on a pin used to answer with a number and keep the stop's name in
     `aria-label` only, which is nothing to an eye that is not reading a screen reader.  Name
     only, per the ORD-0390 rule that keeps the two surfaces from disagreeing about what a
     selected stop shows. */
  "mapComp.selectedStopOnMap": "Selected on the map · {name}",
  },
  zh: {

  // ── 地图组件 ──
  "mapComp.attribution": "© OpenStreetMap 贡献者",
  "mapComp.yourLocation": "你的位置 · {n} 米精度",
  "mapComp.journeyMap": "行程地图",
  "mapComp.routeContext": "路线上下文",
  "mapComp.legs": "{n} 段路程",
  "mapComp.providerRoute": "供应商支持的路线 · WGS84",
  "mapComp.noRouteNoProvider": "这里没有画路线：这台部署没有配置算路服务，所以这一版计划一条路段都没有。",
  "mapComp.noRouteNotRouted": "这里没有画路线：这一版计划一条路段都没有，图上不存在来自算路服务的路线。",
  "mapComp.disruptionScope": "中断范围",
  "mapComp.maplibreLabel": "MapLibre 行程地图",
  /* ORD-0417：与 en 同一条，站名之外什么都不加（时长、价钱会把两个面重新拉回互相矛盾）。
     摆放的位置在 `.v8-map-caption` 里面，理由写在 `map-selection.css` 的那条规则上。 */
  "mapComp.selectedStopOnMap": "图上选中的这一站 · {name}",
  },
};
