/* ORD-0524 — the words the import screen needs for its three destinations, in this feature's own table.

   Why a local table instead of `i18n/LocaleContext.tsx`: that file is the one every lane's front-end
   order edits (ORD-0435's r8 could not merge for exactly that reason), and the house answer to a
   feature's own sentences is a table inside the feature -- `features/collections/collectionCopy.ts`
   and `i18n/mapPanelCopy.ts` are the two this file copies the shape of. Nothing here is exempted from
   the exposure ruler; these are this order's sentences, not upstream prose.

   The shelf words are NOT repeated here: 收藏到… / 收到哪个架子 / 已收在 / 这一枚已经在这个架子上 are
   ORD-0444 and ORD-0510's own lines in `collectionCopy.ts`, and `PoiImportPanel` imports them from
   there. Re-typing them here would be the fourth way of saying the same thing, which is what the order
   forbids.

   Counted nouns go through `{plural:stem}` (`lib/plural.ts`, ORD-0433) rather than a per-key plural of
   this file's own -- the ORD-0467 alignment ruling says the vocabulary is shared or it is not written.
*/

import { expandPluralMarkers } from "../../lib/plural";

export type PoiImportCopyKey =
  | "exitsLead"
  | "selectAll"
  | "selectAllOn"
  | "exitStoreOnly"
  | "storeOnlyRefusal"
  | "storeOnlyChosen"
  | "landingDayChosen"
  | "landingDayFirst"
  | "landingDayNone"
  | "collectAction"
  | "collecting"
  | "collectedCount"
  | "collectAlready"
  | "collectNothingConfirmed"
  /* ORD-0545: the channel badge came over from `t("poiImport.channelLocal")`, which ORD-0533 had to
     fill because this screen's own table did not hold it.  The words are that order's, unchanged. */
  | "channelLocal";

const COPY: Record<PoiImportCopyKey, { zh: string; en: string }> = {
  exitsLead: {
    zh: "三个去处只能选一个：选了哪一个，就只照那一个写。",
    en: "One destination at a time: whichever is chosen is the only one that writes.",
  },
  /* The row that replaces the silent pre-tick. It says what it will do to every selectable row, and
     its own word moves with the state so the control is not a glyph a screen reader alone can read. */
  selectAll: {
    zh: "全选可加的行",
    en: "Select every selectable row",
  },
  selectAllOn: {
    zh: "已全选——点一下取消全部",
    en: "All selected — tap to clear every row",
  },
  exitStoreOnly: {
    zh: "只存不排",
    en: "Keep them without a day",
  },
  /* Measured on this line, not assumed: `POST .../poi-import/add` with an empty day answers 201 with
     `day_source=JOURNEY_FIRST_DAY`, and the only other store this tree has is the shelf, which is the
     exit above. So there is no door to wire this radio to, and the honest form of the third exit is a
     refusal that names why. */
  storeOnlyRefusal: {
    zh: "这台服务器没有“存下来但不给日子”的门：加进计划必须落在某一天，而存进架子就是上面那个出口。这里不另起第四种说法，所以这一项按状态拒绝，什么都不写。",
    en: "This server has no door that keeps a place without giving it a day: 加进计划 must land on a day, and putting it on a shelf is the exit above. No fourth word is invented here, so this one refuses by state and writes nothing.",
  },
  /* The chosen state of the refused exit: the traveller picked it, so the screen owes a sentence about
     what just happened -- which is that nothing happened, and no write control exists any more. */
  storeOnlyChosen: {
    zh: "这一项选上了，但它没有可写的门：上面那句就是它的全部回答，这一屏什么都没写。",
    en: "This destination is chosen and has no door to write through: the line above is its whole answer, and nothing has been written.",
  },
  landingDayChosen: {
    zh: "你选的日子：{day}",
    en: "The day you chose: {day}",
  },
  landingDayFirst: {
    zh: "没有填日子，就落在计划的第一天：{day}",
    en: "No day typed, so this lands on the plan's first day: {day}",
  },
  landingDayNone: {
    zh: "现在还没有日子可落——先选一个日子。",
    en: "There is no day to land on yet — pick one first.",
  },
  collectAction: {
    zh: "存进这个架子",
    en: "Collect these into that shelf",
  },
  collecting: {
    zh: "正在存…",
    en: "Collecting…",
  },
  /* The number here is counted off the re-read, so the sentence cannot outlive the rows the list door
     actually returned. `{shelf}` is the shelf's own name from that read -- never its id. The Chinese
     arms carry no `{plural:}` marker at all, which is ORD-0433's rule: a marker in a zh line would
     paint an English noun on the Chinese glass. */
  collectedCount: {
    zh: "{n} 枚已收在「{shelf}」——这句是从同一扇读门重读回来的。",
    en: "{n} {plural:place} are now on {shelf} — read back from the same list door.",
  },
  collectAlready: {
    zh: "{n} 枚本来就在「{shelf}」上，没有重复写入。",
    en: "{n} {plural:place} were already on {shelf}, so nothing was written twice.",
  },
  collectNothingConfirmed: {
    zh: "写入应答了，但架子上读不回这一枚。在它读回来之前，这里不说“已收在”。",
    en: "The write answered, but the shelf did not give these back. Nothing is called collected until it does.",
  },
  /* The badge next to the screen's title.  It carries no `{...}` value because the screen states it
     the same way whatever it is showing: the parser is local and no link is opened.  Both halves are
     ORD-0533's words, moved rather than reworded -- `git diff` on this order shows the pair as one
     deletion from `LocaleContext.tsx` and one insertion here. */
  channelLocal: {
    zh: "本地解析，不打开链接",
    en: "Local parse, no links opened",
  },
};

export function poiImportCopy(
  locale: string,
  key: PoiImportCopyKey,
  params?: Record<string, string | number>,
): string {
  const table = locale.startsWith("zh") ? COPY[key].zh : COPY[key].en;
  /* Two passes, in this order: `{plural:stem}` is grammar and belongs to the shared counting rule
     (ORD-0433), while `{day}` / `{shelf}` / `{n}` are values the caller measured. A placeholder with
     no value stays visible as the placeholder -- the same rule `fillAccess` keeps, so a field the
     screen never read cannot arrive as a finished sentence.

     This line is not decoration: the first candidate generation painted 「没有填日子，就落在计划的第一天：{day}」
     on the glass, and the arm that reads `innerText` is what caught it. */
  const counted = expandPluralMarkers(table, params);
  return counted.replace(/\{(\w+)\}/g, (_match, name: string) => String(params?.[name] ?? `{${name}}`));
}
