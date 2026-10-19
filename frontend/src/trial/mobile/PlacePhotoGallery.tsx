import { useState } from "react";
import { Images, ImageOff } from "lucide-react";
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

function PhotoCard({ photo, place, selected, scheduled, onSelect }: {
  photo: CuratedPhoto; place: WorkspaceMapPoint; selected: boolean; scheduled: boolean; onSelect?: (id: string) => void;
}) {
  const [broken, setBroken] = useState(false);
  return <article className={"cn-place-photo" + (selected ? " is-selected" : "")} data-place-id={place.candidate_id}>
    {broken
      ? <div className="cn-place-photo-fallback"><ImageOff size={24} /><span>照片暂时无法加载</span></div>
      : <img src={photoUrl(photo.filename)} alt={photo.label + "实景照片"}
          loading="lazy" decoding="async" onError={() => setBroken(true)} />}
    <div className="cn-place-photo-meta">
      <strong>{photo.label}</strong>
      <span>历史照片 · 封面裁切</span>
      <small>
        <a href={photoPage(photo.filename)} target="_blank" rel="noopener noreferrer">{photo.author}</a>
        {photo.licenseHref && <> · <a href={photo.licenseHref} target="_blank" rel="noopener noreferrer">{photo.licenseLabel}</a></>}
      </small>
      <button type="button" onClick={() => onSelect?.(place.candidate_id)} aria-pressed={selected}>
        {selected ? "正在查看" : scheduled ? "查看对应安排" : "在地图中查看"}
      </button>
    </div>
  </article>;
}

export function PlacePhotoGallery({ cityName, places, selectedId, scheduledIds, onSelect }: {
  cityName: string; places: WorkspaceMapPoint[]; selectedId?: string | null; scheduledIds?: ReadonlySet<string>; onSelect?: (id: string) => void;
}) {
  if (!/^(?:福建省)?(?:龙岩市)?连城(?:县)?$/.test(cityName.trim())) return null;
  const photos = LIANCHENG_PHOTOS.flatMap((photo) => {
    const place = places.find((point) => matchesPhoto(photo, point));
    return place ? [{ photo, place }] : [];
  });
  if (photos.length === 0) return null;
  return <section className="cn-place-gallery" aria-label="与研究地点对应的真实景点照片">
    <div className="cn-place-gallery-heading"><Images size={17} /><strong>先看看这些地方</strong><span>实景相册</span></div>
    <div className="cn-place-photo-track">{photos.map(({ photo, place }) => <PhotoCard key={photo.filename}
      photo={photo} place={place} selected={selectedId === place.candidate_id} scheduled={scheduledIds?.has(place.candidate_id) ?? false} onSelect={onSelect} />)}</div>
  </section>;
}
