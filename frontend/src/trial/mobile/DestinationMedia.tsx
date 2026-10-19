import { useState } from "react";
import { ImageOff, Mountain, Trees } from "lucide-react";
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

export function DestinationMedia({ cityName }: { cityName: string }) {
  const scene = /连城/.test(cityName) ? LIANCHENG_PHOTO : null;
  const [failed, setFailed] = useState(false);
  const src = scene ? "https://commons.wikimedia.org/wiki/Special:FilePath/" + encodeURIComponent(scene.file) + "?width=1000" : null;
  return <div className="cn-mission-media" aria-label={scene ? "目的地实景参考" : "旅行目的地插画"}>
    {scene && !failed && src
      ? <img src={src} loading="lazy" decoding="async" alt="福建连城冠豸山实景，作为目的地参考，不代表当前营业与通行状态"
          onError={() => setFailed(true)} />
      : <div className="cn-mission-media-art" aria-hidden="true">
          <Mountain size={92} strokeWidth={0.65} />
          <Trees size={45} strokeWidth={0.7} />
        </div>}
    {scene && !failed
      ? <div className="cn-mission-media-credit">
          <a href={scene.page} target="_blank" rel="noopener noreferrer">冠豸山实景（封面裁切）</a>
          <span> · {scene.credit} / <a href={scene.license} target="_blank" rel="noopener noreferrer">CC BY 3.0</a></span>
        </div>
      : <div className="cn-mission-media-credit is-illustration"><ImageOff size={12} aria-hidden="true" /> 场景插画 · 非真实地点照片</div>}
  </div>;
}
