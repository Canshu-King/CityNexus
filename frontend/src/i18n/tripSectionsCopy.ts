/**
 * ORD-0573 — the trips surface's own copy table, kept in its own file for the same reason
 * `mapPanelCopy.ts` is: `LocaleContext.tsx` is shared and other lanes are editing it, so this
 * surface's words live here.
 *
 * The four section labels were inline bilingual literals inside the shell
 * (`{zh ? item.zh : item.en}` over a local array). They are lifted here verbatim: this is a move,
 * not a rewrite. The words the traveller reads must not change, and the gate compares all four in
 * both arms against the readings taken before this hand.
 *
 * Why these four needed their own keys rather than reusing `nav.*`: the nearest existing keys say
 * different words -- `nav.stay` reads "Stay Explorer" / 「住宿选择」 while this tab reads "Stay" /
 * 「住宿」, and `nav.trips` is the shell's own name for the whole screen, not for a section of it.
 * Reusing them would have changed what is on the glass, which is exactly what this lift forbids.
 */

export type TripsSectionKey = "itinerary" | "stay" | "bookings" | "spend";

const COPY: Record<TripsSectionKey, { zh: string; en: string }> = {
  itinerary: { zh: "行程", en: "Itinerary" },
  stay: { zh: "住宿", en: "Stay" },
  bookings: { zh: "预订", en: "Bookings" },
  spend: { zh: "花费", en: "Spend" },
};

/** The section label as the traveller reads it on this build. */
export function tripsSectionLabel(key: TripsSectionKey, zh: boolean): string {
  return zh ? COPY[key].zh : COPY[key].en;
}

export const tripsSectionKeys: TripsSectionKey[] = ["itinerary", "stay", "bookings", "spend"];