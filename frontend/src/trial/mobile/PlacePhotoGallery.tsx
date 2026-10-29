import { useState } from "react";
import { Images, ImageOff, MapPin } from "lucide-react";
import type { GoalPlaceMediaResult } from "../../api/citynexus";
import type { WorkspaceMapPoint } from "./WorkspaceMap";
import "./PlacePhotoGallery.css";

type CuratedPhoto = {
  placeTest: RegExp;
  sourceIds: string[];
  latitude: number;
  longitude: number;
  label: string;
  filename: string;
  author: string;
  licenseLabel: string;
  licenseHref: string;
};

// Identity-checked images for existing Liancheng research places.
// These are historical CC-licensed Wikimedia Commons photos, not live scene,
// provider photography, opening evidence, or a generic keyword-image API.
// Do not add arbitrary remote thumbnails based on a fuzzy POI name.
const LIANCHENG_PHOTOS: CuratedPhoto[] = [
  {
    placeTest: /^(?:连城(?:县)?[ ·]*)?冠豸山(?:风景区|景区|国家地质公园)?$/,
    sourceIds: ["photon:W/846486126"],
    latitude: 25.715886,
    longitude: 116.775720,
    label: "冠豸山",
    filename: "远望冠豸山 - Guanzhai Mountain - 2010.07 - panoramio.jpg",
    author: "rheins",
    licenseLabel: "CC BY 3.0",
    licenseHref: "https://creativecommons.org/licenses/by/3.0/",
  },
  {
    placeTest: /^(?:连城(?:县)?[ ·]*)?石门湖(?:景区|风景区)?$/,
    sourceIds: ["photon:R/6432779"],
    latitude: 25.704378,
    longitude: 116.788294,
    label: "石门湖",
    filename: "石门湖 - Shimeng Lake - 2010.07 - panoramio - rheins.jpg",
    author: "rheins",
    licenseLabel: "CC BY 3.0",
    licenseHref: "https://creativecommons.org/licenses/by/3.0/",
  },
  {
    placeTest: /^(?:连城(?:县)?[ ·]*)?培田(?:古村落|古村|村|古民居)$/,
    sourceIds: ["nominatim:way/670148268"],
    latitude: 25.633770,
    longitude: 116.633329,
    label: "培田古村",
    filename: "2012 福建 龙岩 连城县 培田古村 - panoramio (3).jpg",
    author: "张元柏",
    licenseLabel: "CC BY-SA 3.0",
    licenseHref: "https://creativecommons.org/licenses/by-sa/3.0/",
  },
];

function photoPage(filename: string): string {
  return "https://commons.wikimedia.org/wiki/File:" + encodeURIComponent(filename.replaceAll(" ", "_"));
}

function photoUrl(filename: string): string {
  return "https://commons.wikimedia.org/wiki/Special:FilePath/" + encodeURIComponent(filename) + "?width=600";
}

// A curated source binding identifies the photographed attraction; it does not
// rewrite the provider's UNKNOWN district, opening or fee fields. Coordinates
// and the exact source ID must both agree with the Commons location metadata.
function matchesPhoto(photo: CuratedPhoto, place: WorkspaceMapPoint): boolean {
  if (!photo.placeTest.test(place.name) || place.provider_provenance !== "LIVE_PROVIDER"
    || place.region_status === "CONFLICT" || place.selection_state === "REGION_CONFLICT") return false;
  if (place.region_status === "MATCHED" && place.adcode === "350825") return true;
  return place.coordinate_system === "WGS84" && photo.sourceIds.includes(place.candidate_id)
    && Number.isFinite(place.latitude) && Number.isFinite(place.longitude)
    && Math.abs(place.latitude - photo.latitude) < 0.03
    && Math.abs(place.longitude - photo.longitude) < 0.03;
}

function PhotoCard({ photo, result, place, selected, scheduled, onSelect }: {
  photo?: CuratedPhoto; result?: GoalPlaceMediaResult; place: WorkspaceMapPoint;
  selected: boolean; scheduled: boolean; onSelect?: (id: string) => void;
}) {
  const [broken, setBroken] = useState(false);
  const media = result?.media?.can_show && result.media.place_id === place.candidate_id ? result.media : null;
  const url = media?.thumb_url || media?.image_url || (photo ? photoUrl(photo.filename) : null);
  const sourceUrl = media?.source_url || (photo ? photoPage(photo.filename) : null);
  const author = media?.author || photo?.author;
  const license = media?.license || photo?.licenseLabel;
  const licenseUrl = media?.terms_url || photo?.licenseHref;
  // The tile used to invite 「先看看这个地点」 with no control behind it: a tap on the picture area did
  // nothing (measured 2026-10-22 -- 72 s of waiting after such a tap, no request reached the server).
  // The lookup does exist, hanging off the small meta button, so the invitation is now that control,
  // and once the source has answered the tile says which answer came back instead of staying neutral.
  const answer = url ? null : !result ? null : result.status === "UNAVAILABLE" ? "照片来源暂时没答上"
    : result.reason_code === "MEDIA_IDENTITY_UNBOUND" ? "还没核实到具体是哪个地点" : "没查到可核实的实景照片";
  return <article className={"cn-place-photo" + (selected ? " is-selected" : "") + (!url ? " is-placeholder" : "")}
    data-place-id={place.candidate_id} data-photo-origin={media ? "runtime" : photo ? "curated" : "none"}>
    {broken || !url
      ? <div className="cn-place-photo-fallback">{url ? <ImageOff size={24} /> : <MapPin size={28} />}
        {url || answer ? <span>{url ? "照片暂时无法加载" : answer}</span>
          : <button type="button" onClick={() => onSelect?.(place.candidate_id)}>先看看这个地点</button>}</div>
      : <img src={url} alt={place.name + "实景照片"} loading="lazy" decoding="async" onError={() => setBroken(true)} />}
    <div className="cn-place-photo-meta">
      <strong>{photo?.label || place.name}</strong>
      {url && <span>{media ? "来源实景 · 封面裁切" : "历史照片 · 封面裁切"}</span>}
      {sourceUrl && <small><a href={sourceUrl} target="_blank" rel="noopener noreferrer">{author}</a>
        {license && <> · {licenseUrl ? <a href={licenseUrl} target="_blank" rel="noopener noreferrer">{license}</a> : license}</>}
      </small>}
      <button type="button" onClick={() => onSelect?.(place.candidate_id)} aria-pressed={selected}>
        {selected ? "正在查看" : scheduled ? "查看对应安排" : "在地图中查看"}
      </button>
    </div>
  </article>;
}

export function PlacePhotoGallery({ cityName, places, mediaById = {}, selectedId, scheduledIds, priorityIds, onSelect }: {
  cityName: string; places: WorkspaceMapPoint[]; mediaById?: Record<string, GoalPlaceMediaResult>;
  selectedId?: string | null; scheduledIds?: ReadonlySet<string>; priorityIds?: ReadonlySet<string>; onSelect?: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const curated = /^(?:福建省)?(?:龙岩市)?连城(?:县)?$/.test(cityName.trim()) ? LIANCHENG_PHOTOS : [];
  const eligible = places.filter(place => place.provider_provenance === "LIVE_PROVIDER"
    && place.region_status !== "CONFLICT" && place.selection_state !== "REGION_CONFLICT");
  const cards = eligible.map(place => ({ place, photo: curated.find(photo => matchesPhoto(photo, place)),
    result: mediaById[place.candidate_id] })).sort((a,b) =>
      Number(Boolean(b.result?.media || b.photo)) - Number(Boolean(a.result?.media || a.photo)));
  if (!cards.length) return null;
  const relevant = cards.filter(card => card.photo || card.result?.media || priorityIds?.has(card.place.candidate_id) || card.place.candidate_id === selectedId);
  const visibleCards = expanded ? cards : relevant.length ? relevant : cards.slice(0, 6);
  return <section className="cn-place-gallery" aria-label="与研究地点对应的真实景点照片">
    <div className="cn-place-gallery-heading"><Images size={17} /><strong>先看看这些地方</strong><span>地点相册</span></div>
    <div className="cn-place-photo-track">{visibleCards.slice(0, 24).map(({ photo, place, result }) =>
      <PhotoCard key={place.candidate_id + (result?.media?.image_url || "")} photo={photo} result={result}
        place={place} selected={selectedId === place.candidate_id} scheduled={scheduledIds?.has(place.candidate_id) ?? false} onSelect={onSelect} />)}</div>
    {cards.length > visibleCards.length && !expanded && <button type="button" className="cn-place-gallery-more" onClick={() => setExpanded(true)}>查看更多地点（{Math.min(cards.length,24)}）</button>}
  </section>;
}
