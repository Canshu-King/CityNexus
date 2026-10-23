/**
 * ORD-0504 · the one door this screen is allowed to speak a place count from.
 *
 * Before this file the "this city has no places" sentence was produced by the device: the run
 * fetched `/api/v1/places`, counted the ids it liked, and wrote a status string out of that
 * arithmetic (`aiGenerationRun.ts` still carries the judgement, and the wording it drives never
 * looked back at the store).  A traveller who then imported places read the same sentence as
 * before, because nothing re-asked the server - the screen was remembering, not reporting.
 *
 * The rule here is the smallest honest one:
 *  - the number only ever comes from rows this server returned, in this read, on this open;
 *  - a door that did not answer produces `unreadable`, which the sentence says out loud instead
 *    of falling back to a remembered count or a zero;
 *  - no identifier, no city code, no key name goes into the traveller's sentence - that is the
 *    evidence panel's job under 技术详情, not the copy's.
 */

/**
 * The three sentences, owned here.  They used to be fetched with `dictionaryCopy("…", "catalog.count.zero")`
 * -- and no dictionary on this line ever defined `catalog.count.*`, so the fallback in
 * `LocaleContext.tsx:3112` handed back the key itself and the trip page printed
 * `catalog.count.zero` to a traveller.  That is exactly what the header of this file forbids, so the
 * copy now lives beside the rule it serves (same shape as `abort/journeyAbortCopy.ts`), and a missing
 * string can no longer degrade into an identifier.
 */
const CATALOGUE_COPY = {
  en: {
    zero: "This city has no places on this server yet.",
    unreadable: "This server has not answered how many places this city holds.",
    some: "This city has {count} places to plan with on this server.",
  },
  "zh-CN": {
    zero: "这座城在这台服务器上还没有可排的地点。",
    unreadable: "这台服务器还没答上来：这座城有多少个地点。",
    some: "这座城在这台服务器上有 {count} 个可排的地点。",
  },
} as const;

export const UNREADABLE_SENTENCE_ZH = CATALOGUE_COPY["zh-CN"].unreadable;
export const UNREADABLE_SENTENCE_EN = CATALOGUE_COPY.en.unreadable;
export type CatalogueReadback = {
  /** `server` only when the door answered with a readable list; `unreadable` is a real state. */
  source: "server" | "unreadable";
  /** Rows the server returned.  `null` means we do not know, and is never displayed as 0. */
  placeCount: number | null;
  /** The status we actually saw, so an unreadable reading can name itself. */
  httpStatus: number | null;
};

export async function readCityCatalogue(
  cityCode: string | undefined,
  signal?: AbortSignal,
): Promise<CatalogueReadback> {
  if (!cityCode) {
    // No city named on this mount is not an empty catalogue; saying 0 here would be inventing a
    // fact the caller never had.
    return { source: "unreadable", placeCount: null, httpStatus: null };
  }
  try {
    const response = await fetch(
      `/api/v1/places?city_code=${encodeURIComponent(cityCode)}`,
      { headers: { Accept: "application/json" }, signal },
    );
    if (!response.ok) {
      return { source: "unreadable", placeCount: null, httpStatus: response.status };
    }
    const rows: unknown = await response.json();
    if (!Array.isArray(rows)) {
      return { source: "unreadable", placeCount: null, httpStatus: response.status };
    }
    return { source: "server", placeCount: rows.length, httpStatus: response.status };
  } catch {
    // A cancelled or broken read is reported as unreadable; it never becomes "no places".
    return { source: "unreadable", placeCount: null, httpStatus: null };
  }
}

/**
 * The traveller-facing sentence, built only from `readback`.  `null` and `0` are different facts
 * and get different sentences; that distinction is the whole reason this function exists.
 */
export function catalogueCountSentence(
  readback: CatalogueReadback | null,
  zh: boolean,
): string {
  if (!readback || readback.source !== "server" || readback.placeCount === null) {
    return zh ? UNREADABLE_SENTENCE_ZH : UNREADABLE_SENTENCE_EN;
  }
  const count = readback.placeCount;
  const table = zh ? CATALOGUE_COPY["zh-CN"] : CATALOGUE_COPY.en;
  if (count === 0) {
    return table.zero;
  }
  return table.some.replace("{count}", String(count));
}
