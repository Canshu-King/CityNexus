import { useState } from "react";
import { ImageOff, Mountain, Trees } from "lucide-react";
import type { GoalPlaceMedia } from "../../api/citynexus";
import "./DestinationMedia.css";

/**
 * Consumer-facing scenery is an attributed media surface, not POI evidence.
 * Never attach a generic search image to a specific museum, restaurant or route.
 * Curated starter: a CC BY 3.0 Commons photograph of 冠豸山 in 连城县.
 */
const LIANCHENG_PHOTO = {
  file: "远望冠豸山 - Guanzhai Mountain - 2010.07 - panoramio.jpg",
  page: "https://commons.wikimedia.org/wiki/File:%E8%BF%9C%E6%9C%9B%E5%86%A0%E8%B1%B8%E5%B1%B1_-_Guanzhai_Mountain_-_2010.07_-_panoramio.jpg",
  credit: "rheins",
  license: "https://creativecommons.org/licenses/by/3.0/",
};

export function DestinationMedia({ cityName, media, placeName }: { cityName: string; media?: GoalPlaceMedia | null; placeName?: string }) {
  const scene = /^(?:福建省)?(?:龙岩市)?连城(?:县)?$/.test(cityName.trim()) ? LIANCHENG_PHOTO : null;
  const [failed, setFailed] = useState(false);
  const src = media?.thumb_url || media?.image_url || (scene ? "https://commons.wikimedia.org/wiki/Special:FilePath/" + encodeURIComponent(scene.file) + "?width=1000" : null);
  const page = media?.source_url || scene?.page;
  const author = media?.author || scene?.credit;
  const license = media?.license || (scene ? "CC BY 3.0" : null);
  const terms = media?.terms_url || scene?.license;
  const name = media ? placeName : "冠豸山";
  return <div className="cn-mission-media" aria-label={src ? "目的地实景参考" : "旅行目的地插画"}>
    {!failed && src
      ? <img src={src} loading="lazy" decoding="async" alt={name + "实景"}
          onError={() => setFailed(true)} />
      : <div className="cn-mission-media-art" aria-hidden="true">
          <Mountain size={92} strokeWidth={0.65} />
          <Trees size={45} strokeWidth={0.7} />
        </div>}
    {src && !failed
      ? <div className="cn-mission-media-credit">
          <a href={page} target="_blank" rel="noopener noreferrer">{name}实景（封面裁切）</a>
          <span> · {author} / {terms ? <a href={terms} target="_blank" rel="noopener noreferrer">{license}</a> : license}</span>
        </div>
      : <div className="cn-mission-media-credit is-illustration"><ImageOff size={12} aria-hidden="true" /> 旅行插画</div>}
  </div>;
}
