/* ORD-0500 -- the words this screen says when the footprint door refuses.
 *
 * Deliberately NOT in `i18n/LocaleContext.tsx`: that dictionary is the shared serialisation point
 * every lane appends to, and the two orders landed tonight both had to re-cut because of it (see
 * `features/access/accessCopy.ts`, which made the same choice for the same reason).  What lives here
 * is the refusal vocabulary of one door, keyed by the `reason_code` the server answers with, so a
 * new refusal name is one row in this table and one arm in this feature's spec.
 *
 * The button's own words (打卡 / 已打卡 and their aria forms) stay in `i18n/LocaleContext.tsx`,
 * which already owns them: one owner per word, so this table holds only the refusal sentences.
 *
 * Two rules every row obeys:
 *  - a sentence never carries an id. The server's `details` carry `existing_checkin_id` and
 *    `activity_id` as uuids; what a traveller can act on is the MOMENT the winning stamp was made,
 *    so `duplicateAt` interpolates `existing_stamped_at` and nothing else;
 *  - an answer this screen has not learned to speak is said as a gap, with the status this device
 *    measured, rather than being folded into a generic "something went wrong" -- that is how a
 *    refusal stops being actionable.
 */

/** The refusal vocabulary, in the same {zh, en} shape `accessCopy` uses. */
export type CheckinCopyKey =
  | "duplicateAt"
  | "duplicateNoMoment"
  | "activityUnknown"
  | "activityNotInJourney"
  | "placeUnknown"
  | "targetRequired"
  | "targetAmbiguous"
  | "journeyInBin"
  | "journeyUnknown"
  | "unreachable"
  | "unexpected";

export const CHECKIN_COPY: Record<CheckinCopyKey, { zh: string; en: string }> = {
  /* The duplicate answer has to point at the stamp that won, in the only two terms a traveller can
     check: this stop, and the instant the server wrote.  No uuid. */
  duplicateAt: {
    zh: "这一站已经打过卡了（服务器记的是 {moment}），这次没有再盖一枚，行程里还是原来那一枚。",
    en: "This stop is already stamped ({moment}); nothing new was written — the trip keeps the stamp it had.",
  },
  duplicateNoMoment: {
    zh: "这一站已经打过卡了，这次没有再盖一枚；那一枚的时间这次没有随答案回来。",
    en: "This stop is already stamped and nothing new was written; the winning stamp's moment did not come back with this answer.",
  },
  activityUnknown: {
    zh: "这一站已经不在服务器上了，所以这枚打卡没有落下。请回行程列表重新打开这趟。",
    en: "That stop is no longer on the server, so this stamp was not written. Open the trip again from your trips list.",
  },
  activityNotInJourney: {
    zh: "这一站不属于这趟行程，所以这枚打卡没有落下。请在这一趟自己的行程里打卡。",
    en: "That stop belongs to another trip, so this stamp was not written. Stamp a stop from this trip's own itinerary.",
  },
  placeUnknown: {
    zh: "那个地点我们这边没有档案，所以这枚打卡没有落下。",
    en: "We have no record of that place here, so this stamp was not written.",
  },
  targetRequired: {
    zh: "这枚打卡没有说要记在哪一站，所以没有落下。请在某一站上按「打卡」。",
    en: "This stamp did not name a stop, so nothing was written. Tap 打卡 on one of the stops.",
  },
  targetAmbiguous: {
    zh: "这枚打卡同时指向一站和一个地点，只能记一个，所以没有落下。",
    en: "This stamp named both a stop and a place, and only one can be recorded, so nothing was written.",
  },
  journeyInBin: {
    zh: "这趟行程在回收站里，先把它找回来才谈得上打卡或读足迹。",
    en: "This trip is in the recycle bin; bring it back before stamping or reading its footprints.",
  },
  journeyUnknown: {
    zh: "这台服务器上没有这趟行程，所以这一屏的打卡没有落下。",
    en: "This server has no such trip, so this stamp was not written.",
  },
  unreachable: {
    zh: "这一问没有到达服务器，所以这里不能说打卡有没有落下。",
    en: "This request never reached the server, so nothing here can say whether the stamp was written.",
  },
  unexpected: {
    zh: "服务器收了这枚打卡但给了一个这里说不上名的答复（{status}），所以这一屏按没有打卡处理。",
    en: "The server answered this stamp with a name this screen does not recognise ({status}), so this screen treats it as not written.",
  },
};

/** `error.reason_code` -> the row that speaks it.  Anything absent falls to `unexpected`. */
export const CHECKIN_REFUSAL_COPY: Record<string, CheckinCopyKey> = {
  CHECKIN_DUPLICATE_STAMP: "duplicateAt",
  CHECKIN_ACTIVITY_UNKNOWN: "activityUnknown",
  CHECKIN_ACTIVITY_NOT_IN_JOURNEY: "activityNotInJourney",
  CHECKIN_PLACE_UNKNOWN: "placeUnknown",
  CHECKIN_TARGET_REQUIRED: "targetRequired",
  CHECKIN_TARGET_AMBIGUOUS: "targetAmbiguous",
  CHECKIN_JOURNEY_IN_RECYCLE_BIN: "journeyInBin",
  CHECKIN_JOURNEY_UNKNOWN: "journeyUnknown",
};

export function wordsFor(entry: { zh: string; en: string }, zh: boolean,
                         params?: Record<string, string>): string {
  const raw = zh ? entry.zh : entry.en;
  if (!params) return raw;
  return raw.replace(/\{(\w+)\}/g, (_all, name) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : "{" + name + "}");
}
