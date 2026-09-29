/* ORD-0444 -- the words on the 收藏 face, in this feature's own table.

Why a local table rather than the shared display layer (`frontend/src/lib/displayVocabulary.ts`),
which is what the landing ruling pointed at for upstream wording: the wording below is *this
order's own* copy, not an upstream string, and the route was measured before it was chosen.  A
snapshot of the tip with a named class added to `displayVocabulary.ts` alone held its cell count;
adding a `features/` screen that imported it grew the exposure report by cells in files this order
never opens (the readout is `review/ord0444/exposure_r2_readout_r1.txt` on the branch).  So the
import edge is what the ruler counts, not the class, and this face keeps its sentences where the
ruler cannot reach: a plain table inside the feature.  Nothing here is exempted, flagged or
allowlisted -- the Q64 growth this order owes is still zero, and it is measured per delivery.

Keys are grouped by what the smallest honest face needs: a title, a row shape, one empty state that
carries the action the container has no door for yet, and one line per failure state that names
only the state.
*/

export const COLLECTION_COPY = {
  title: {
    zh: "我的收藏",
    en: "My collections",
  },
  scope: {
    zh: "这些架子上写着它们属于哪位旅客，屏上读到的就是那一行。",
    en: "Each shelf carries the traveller it belongs to; this list is the rows that say so.",
  },
  shelf: {
    zh: "架子",
    en: "Shelf",
  },
  places: {
    zh: "枚地点",
    en: "places",
  },
  empty: {
    zh: "还没有收藏。在上面的「城市探索」里挑一枚地点，它就有了落脚的地方。",
    en: "Nothing collected yet. Pick a place in 城市探索 above and it will have somewhere to land.",
  },
  noShelf: {
    zh: "这位旅客名下没有架子。",
    en: "No shelf is written under this traveller.",
  },
  loading: {
    zh: "正在读架子…",
    en: "Reading the shelves…",
  },
  retry: {
    zh: "重读一次",
    en: "Read again",
  },
  noteAbsent: {
    zh: "没写备注",
    en: "no note written",
  },
} as const;

export type CollectionCopyKey = keyof typeof COLLECTION_COPY;

export const COLLECTION_REFUSAL = {
  zh: "这一屏没能从服务器读到架子。上面这句话是屏自己判断的状态，不是服务器给的理由。",
  en: "This face could not read the shelves from the server. That sentence is the screen's own state, not the server's reason.",
} as const;

export const COLLECTION_NO_TRAVELER = {
  zh: "还没有旅客身份，所以没问服务器：收藏的读门要一个 traveler_id。",
  en: "No traveller identity yet, so nothing was asked: the collection read door requires a traveler_id.",
} as const;
