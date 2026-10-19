import { useState } from "react";
import { Images, ImageOff } from "lucide-react";
import type { WorkspaceMapPoint } from "./WorkspaceMap";
import "./PlacePhotoGallery.css";

type CuratedPhoto = {
  placeTest: RegExp;
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
    label: "冠豸山",
    filename: "远望冠豸山 - Guanzhai Mountain - 2010.07 - panoramio.jpg",
    author: "rheins",
    licenseLabel: "CC BY 3.0",
    licenseHref: "https://creativecommons.org/licenses/by/3.0/",
  },
  {
    placeTest: /^(?:连城(?:县)?[ ·]*)?石门湖(?:景区|风景区)?$/,
    label: "石门湖",
    filename: "石门湖 - Shimeng Lake - 2010.07 - panoramio - rheins.jpg",
    author: "Wikimedia Commons · 请查看原始授权",
    licenseLabel: "查看原图",
    licenseHref: "",
  },
  {
    placeTest: /^(?:连城(?:县)?[ ·]*)?培田(?:古村落|古村|村)$/,
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

function PhotoCard({ photo }: { photo: CuratedPhoto }) {
  const [broken, setBroken] = useState(false);
  return <article className="cn-place-photo">
    {broken
      ? <div className="cn-place-photo-fallback"><ImageOff size={24} /><span>照片暂时无法加载</span></div>
      : <img src={photoUrl(photo.filename)} alt={photo.label + "历史实景照片，不代表当前营业或开放状态"}
          loading="lazy" decoding="async" onError={() => setBroken(true)} />}
    <div className="cn-place-photo-meta">
      <strong>{photo.label}</strong>
      <span>历史实景 · 仅供旅行参考</span>
      <small>
        <a href={photoPage(photo.filename)} target="_blank" rel="noopener noreferrer">{photo.author}</a>
        {photo.licenseHref && <> · <a href={photo.licenseHref} target="_blank" rel="noopener noreferrer">{photo.licenseLabel}</a></>}
      </small>
    </div>
  </article>;
}

export function PlacePhotoGallery({ cityName, places }: { cityName: string; places: WorkspaceMapPoint[] }) {
  if (!/连城/.test(cityName)) return null;
  const photos = LIANCHENG_PHOTOS.filter((photo) =>
    places.some((place) => photo.placeTest.test(place.name)
      && place.region_status === "MATCHED"
      && place.provider_provenance === "LIVE_PROVIDER"));
  if (photos.length === 0) return null;
  return <section className="cn-place-gallery" aria-label="与研究地点对应的真实景点照片">
    <div className="cn-place-gallery-heading"><Images size={17} /><strong>先看看这些地方</strong><span>带来源的历史实景</span></div>
    <div className="cn-place-photo-track">{photos.map((photo) => <PhotoCard key={photo.filename} photo={photo} />)}</div>
    <p>照片属于视觉参考，不替代地图坐标、开放时间、票价或最新现场情况。</p>
  </section>;
}
