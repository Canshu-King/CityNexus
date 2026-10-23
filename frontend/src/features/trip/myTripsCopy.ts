/**
 * Issue #33 Q1 -- copy for the reopen-my-trips entry.
 *
 * Deliberately not in `i18n/LocaleContext.tsx`: that dictionary is the shared file other lanes edit
 * the same night, and `features/trash/journeyTrashCopy.ts` is the precedent for a screen-local table.
 *
 * Two rules the words have to keep:
 *  - the entry only ever says what the doors can do.  There is no password and no refresh token on
 *    this build, so a lapsed credential gets "start a new trip", never "sign in again" -- a promise
 *    this server cannot keep is worse than the gap it papers over.
 *  - "your trips" means trips the credential speaks for.  The list door filters by the presented
 *    traveller (`backend/app/main.py`, `list_journeys`), so the count on screen is that door's
 *    answer, not a number this file holds.
 */
import { expandPluralMarkers } from "../../lib/plural";

export const myTripsCopy = {
  en: {
    "my.title": "My trips",
    "my.loading": "Asking which trips are yours…",
    "my.count": "{n} {plural:trip} on this account",
    "my.empty": "This account has no trip on this server yet.",
    "my.expired": "Your session ended. Start a new trip to get back in.",
    "my.failed": "The trip list did not answer.",
    "my.when": "From {from}",
    "my.open": "Open this trip",
    "my.opening": "Opening…",
    "my.refresh": "Read it again",
  },
  "zh-CN": {
    "my.title": "我的行程",
    "my.loading": "正在问服务器哪些行程属于你的账号…",
    "my.count": "这个账号下有 {n} 趟行程",
    "my.empty": "这台服务器上还没有你名下的行程。",
    "my.expired": "登录已结束。新开一趟就能回来。",
    "my.failed": "行程列表没答上来。",
    "my.when": "{from} 起",
    "my.open": "打开这趟",
    "my.opening": "正在打开…",
    "my.refresh": "再读一次",
  },
} as const;

export type MyTripsCopyKey = keyof (typeof myTripsCopy)["zh-CN"];

/** A key missing in one language falls back to English, never to the raw key on screen. */
export function myTripsCopyFor(locale: string, key: MyTripsCopyKey): string {
  const table = myTripsCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? myTripsCopy.en[key] ?? key;
}

export function fillMyTrips(template: string, params: Record<string, string | number>): string {
  return expandPluralMarkers(template, params).replace(
    /\{(\w+)\}/g,
    (_, name: string) => String(params[name] ?? `{${name}}`),
  );
}
