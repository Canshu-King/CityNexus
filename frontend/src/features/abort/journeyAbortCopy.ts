/* ORD-0505: the words of 中止, kept in one table so both language arms are read together.
 *
 * The order asks for a screen that says what happens after the trip is stopped and whether it can be
 * taken back.  Those are two facts, not one mood, so each has its own key:
 *
 *   `after`  - the trip leaves the live screen and stays in the list.  It does not say "deleted":
 *              丢弃 is the recycle bin's verb and this door does not touch `deleted_at`.
 *   `back`   - there is no un-abort door in this build, and the sentence says so instead of
 *              implying a undo that no route serves.  Measured at the base: the only status writes
 *              are PLANNED / ACTIVE / COMPLETED and this order adds CANCELLED, so nothing returns a
 *              trip from it.
 *
 * The refusal keys are the three names the backend answers with, so a traveller reads which rule
 * stopped the tap rather than "it failed".
 */

export type AbortCopyKey =
  | "title"
  | "reasonLabel"
  | "reasonHint"
  | "submit"
  | "after"
  | "back"
  | "storedReason"
  | "noReasonYet"
  | "done"
  | "refusedAuthorised"
  | "refusedNotFound"
  | "refusedAlready"
  | "refusedOther";

export const ABORT_COPY: Record<"zh" | "en", Record<AbortCopyKey, string>> = {
  zh: {
    title: "中止这趟行程",
    reasonLabel: "中止的原因",
    reasonHint: "会写进行程本身，不是只留在屏上",
    submit: "中止",
    after: "中止后，这趟行程不再出现在实时屏，但仍留在行程列表里。",
    back: "现在还没有把中止撤回的门，所以这一步按不可逆来确认。",
    storedReason: "记录里的原因：{reason}（{moment}）",
    noReasonYet: "还没有中止记录：这趟行程没有被中止过。",
    done: "已中止。原因已写入这条行程，重开也会读到同一句。",
    refusedAuthorised: "没有中止：只有这条行程的旅行者能中止它。",
    refusedNotFound: "没有中止：服务器说没有这条行程。",
    refusedAlready: "没有再中止：这趟已经中止了，保留的是第一次写下的原因。",
    refusedOther: "没有中止：服务器答的是 {code}。",
  },
  en: {
    title: "Abort this trip",
    reasonLabel: "Reason for aborting",
    reasonHint: "written into the trip itself, not left on this screen",
    submit: "Abort",
    after: "After an abort the trip leaves the live screen and stays in the trip list.",
    back: "There is no un-abort door in this build, so this step is confirmed as irreversible.",
    storedReason: "Reason on the record: {reason} ({moment})",
    noReasonYet: "No abort on this trip: it has never been stopped.",
    done: "Aborted. The reason is stored on the trip and reads back the same after a reload.",
    refusedAuthorised: "Not aborted: only this trip's traveller can stop it.",
    refusedNotFound: "Not aborted: the server says there is no such trip.",
    refusedAlready: "Not aborted again: it is already stopped, and the first reason stands.",
    refusedOther: "Not aborted: the server answered {code}.",
  },
};

/** The refusal the backend names, mapped to the sentence that explains it. */
export const ABORT_REFUSAL_KEYS: Record<string, AbortCopyKey> = {
  JOURNEY_ABORT_NOT_AUTHORISED: "refusedAuthorised",
  JOURNEY_NOT_FOUND: "refusedNotFound",
  JOURNEY_ABORT_ALREADY_CANCELLED: "refusedAlready",
};

export function abortCopy(locale: "zh" | "en", key: AbortCopyKey): string {
  return ABORT_COPY[locale][key];
}

export function fillAbortCopy(
  locale: "zh" | "en",
  key: AbortCopyKey,
  facts: Record<string, string>,
): string {
  return Object.entries(facts).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, value),
    ABORT_COPY[locale][key],
  );
}
