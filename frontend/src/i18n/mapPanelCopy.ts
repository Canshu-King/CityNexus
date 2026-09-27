/**
 * ORD-A — the map surface's own copy table, kept in its own file on purpose:
 * `LocaleContext.tsx` is being edited by two other lanes at the same time, so this lane's keys land
 * here and the commander lifts them by file. `mapComp.attribution` (already in LocaleContext) holds
 * the bare OSM phrase; the lines below are the sentences that must be *readable on screen*, which
 * additionally name the tile host the component actually calls.
 *
 * `noLocationTitle` / `noLocationBody` / `tileNotice` / `gestureHint` were lifted VERBATIM out of
 * `components/v8/MapPanel.tsx` at 090c048f (the four `locale.startsWith("zh") ? … : …` ternaries at
 * :358, :360-362, :383-385, :394-396). They must stay byte-identical — moving them here is a
 * refactor, not a rewrite. `e2e/qoder-map-gesture-ownership.spec.ts` asserts the gesture hint by
 * substring, and `e2e/qoder-map-interaction.spec.ts` asserts it is visible.
 *
 * `attributionRaster` / `attributionVector` are new: the basemap obligation for
 * tile.openstreetmap.org (MapPanel) and tiles.openfreemap.org (JourneyMap), neither of which was
 * readable on screen before — both set `attributionControl:false`.
 */

export type MapCopyKey =
  | "noLocationTitle"
  | "noLocationBody"
  | "tileNotice"
  | "gestureHint"
  | "attributionRaster"
  | "attributionVector";

const COPY: Record<MapCopyKey, { zh: string; en: string }> = {
  noLocationTitle: { zh: "尚未获取地图位置",
            en: "No map location yet" },
  noLocationBody: { zh: "这个行程还没有可信的坐标。添加活动地点或开启定位后，地图会显示正确的城市。",
            en: "This trip has no trustworthy coordinates yet. Add located activities or enable location, and the map will show the right city." },
  tileNotice: { zh: "底图未加载，显示的是路线示意。",
            en: "Basemap did not load — showing the route diagram only." },
  gestureHint: { zh: "单指拖动地图 · 双指缩放 · 想翻这一页就拖地图以外的地方",
            en: "One finger drags the map · two fingers zoom · to move the page, drag outside the map" },
  attributionRaster: { zh: "底图数据 © OpenStreetMap 贡献者 · 瓦片服务 tile.openstreetmap.org",
            en: "Basemap data © OpenStreetMap contributors · tiles: tile.openstreetmap.org" },
  attributionVector: { zh: "底图数据 © OpenStreetMap 贡献者 · 瓦片服务 tiles.openfreemap.org",
            en: "Basemap data © OpenStreetMap contributors · tiles: tiles.openfreemap.org" },
};

/** Same locale rule the component used inline: anything starting with zh takes the Chinese arm. */
export function mapCopy(locale: string, key: MapCopyKey): string {
  const arms = COPY[key];
  return locale.startsWith("zh") ? arms.zh : arms.en;
}
