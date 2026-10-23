import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useT } from "../../i18n/LocaleContext";
import { roleLabel } from "../../i18n/travelerLabels";
import { cityNexusApi, type DestinationCapability } from "../../api/citynexus";
import { classifyReadFailure } from "../../lib/failureAttribution";
import { RawFactsPanel } from "../../components/RawFactsPanel";
import type { RawFacts } from "../../lib/rawFacts";
import { useElapsedSeconds } from "../../lib/waitClock";
import { ENTRY_FIELDS, entryFieldBounds, entryFieldLabel, entryFieldName, entryFieldSuffix } from "../../lib/entryLimits";
import { englishCountNoun } from "../../lib/plural";

/**
 * ORD-0036 (d) -- where the wizard's state lives.
 *
 * The decision is **localStorage, not the URL**: a half-filled trip is not a link worth
 * sharing, and `startAt` / `endAt` are local wall-clock strings whose meaning depends on
 * the browser's zone.  The URL keeps its existing job (which screen you are on); this key
 * keeps what you had typed.
 *
 * The overlay open/close state is deliberately *not* persisted -- see the lane's report --
 * because a reload now genuinely aborts an in-flight request, and restoring an open sheet
 * would imply a run that no longer exists.
 */
const TRIAL_DRAFT_KEY = "citynexus.v8.trial_draft";

type StoredTrial = { step: number; draft: Record<string, unknown> };

function readStoredTrial(defaults: { step: 1 | 2 | 3; draft: Record<string, unknown> }): {
  step: 1 | 2 | 3;
  draft: Record<string, unknown>;
} {
  try {
    const raw = localStorage.getItem(TRIAL_DRAFT_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<StoredTrial> | null;
    if (!parsed || typeof parsed !== "object") return defaults;
    const step = parsed.step === 2 || parsed.step === 3 ? parsed.step : 1;
    /* Accept a stored value only when it has the same shape as the default it replaces.
       The entry is user-editable and may predate a field rename, and a string where the
       form expects a number breaks the first screen rather than just that field. */
    const draft: Record<string, unknown> = { ...defaults.draft };
    if (parsed.draft && typeof parsed.draft === "object") {
      for (const [key, value] of Object.entries(parsed.draft)) {
        if (key in defaults.draft && typeof value === typeof defaults.draft[key]) {
          draft[key] = value;
        }
      }
    }
    return { step, draft };
  } catch {
    // Blocked storage or a half-written entry: start clean rather than trust it.
    return defaults;
  }
}

function writeStoredTrial(step: number, draft: unknown): void {
  try {
    localStorage.setItem(TRIAL_DRAFT_KEY, JSON.stringify({ step, draft }));
  } catch {
    /* Nothing to do: the wizard still works, it just will not survive a reload. */
  }
}

/**
 * Pull one field's own complaint out of the composed rejection message.
 *
 * `v8Request` renders the frozen `VALIDATION_ERROR` envelope as
 * "headline — body.arrival_anchor.location: msg / …".  The backend stays the authority; this
 * only routes each sentence back to the field it was about, so a rejection reads as
 * "this box" rather than as one long string the traveller has to parse.
 */
function fieldProblem(
  message: string | null | undefined,
  locNeedle: RegExp,
): string | null {
  if (!message) return null;
  const tail = message.split(" — ")[1] ?? "";
  const part = tail.split(" / ").find((chunk) => locNeedle.test(chunk));
  if (!part) return null;
  const colon = part.indexOf(": ");
  return (colon >= 0 ? part.slice(colon + 2) : part).trim() || null;
}

function clearStoredTrial(): void {
  try {
    localStorage.removeItem(TRIAL_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

export type JourneyTrialDraft = {
  cityName: string;
  countryCode: string;
  timezone: string;
  startAt: string;
  endAt: string;
  arrivalLocation: string;
  departureLocation: string;
  budgetMajor: number;
  stayBudgetMajor: number;
  currency: string;
  partySize: number;
  rooms: number;
  /** Optional planning brief captured in step 2. */
  pace?: string;
  interests?: string[];
  specialRequirements?: string;
};

/** City -> (country, timezone, currency) so a normal user never has to type them. */
const CITY_FACTS: Record<string, { country: string; timezone: string; currency: string; labelZh: string; labelEn: string }> = {
  "厦门": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  xiamen: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "北京": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  beijing: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "上海": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  shanghai: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "天津": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  tianjin: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "福州": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  fuzhou: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "广州": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  guangzhou: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "深圳": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  shenzhen: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "成都": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  chengdu: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  "杭州": { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  hangzhou: { country: "CN", timezone: "Asia/Shanghai", currency: "CNY", labelZh: "中国", labelEn: "China" },
  tokyo: { country: "JP", timezone: "Asia/Tokyo", currency: "JPY", labelZh: "日本", labelEn: "Japan" },
  "东京": { country: "JP", timezone: "Asia/Tokyo", currency: "JPY", labelZh: "日本", labelEn: "Japan" },
  singapore: { country: "SG", timezone: "Asia/Singapore", currency: "SGD", labelZh: "新加坡", labelEn: "Singapore" },
  "新加坡": { country: "SG", timezone: "Asia/Singapore", currency: "SGD", labelZh: "新加坡", labelEn: "Singapore" },
};

export function inferCityFacts(cityName: string) {
  const key = cityName.trim().toLowerCase();
  if (!key) return null;
  return CITY_FACTS[key] ?? CITY_FACTS[cityName.trim()] ?? null;
}

/**
 * ORD-0072: an unrecognised destination has no country / currency / timezone of its own, so
 * it must not keep the ones belonging to whichever city the traveller typed before it.
 * Applied both when a draft is restored and on every city keystroke.
 */
export function withNeutralBasis(
  draft: JourneyTrialDraft,
  basis: { countryCode: string; currency: string; timezone: string },
): JourneyTrialDraft {
  if (!draft.cityName?.trim() || inferCityFacts(draft.cityName)) return draft;
  return {
    ...draft,
    countryCode: basis.countryCode,
    currency: basis.currency,
    timezone: basis.timezone,
  };
}

/**
 * The cities this table recognises. Names only, deliberately no total: the authoritative
 * count of supported destinations is not this table's to publish, and a headcount computed
 * here would be a claim (ORD-0060 #3).
 *
 * Grouping these by their facts looked natural and was wrong: nine Chinese cities share
 * CN / Asia/Shanghai / CNY, so one entry swallowed eight of them. The table already holds
 * one key per spelling, which is the pairing that actually exists.
 */
const SUPPORTED_CITIES = {
  zh: Object.keys(CITY_FACTS).filter((name) => /[^\x00-\x7F]/.test(name)),
  en: Object.keys(CITY_FACTS)
    .filter((name) => /^[\x00-\x7F]+$/.test(name))
    .map((name) => name.charAt(0).toUpperCase() + name.slice(1)),
};

/**
 * ORD-0346: what the server actually said about each spelling this screen offers.
 *
 * `CITY_FACTS` is a spelling table -- it records which names `applyCity` can fill a basis from -- and
 * the wizard was handing it out as a list of supported destinations.  Asked directly at
 * `c740f45d` (`GET /destinations/capability`, resolver seam `off`), three of the eleven Chinese
 * spellings get no identity at all and none of the eleven comes back `READY`.  So the panel asks the
 * server per name and groups by the answer, printing only fields that route publishes.
 *
 * The identity column is `canonical_destination_id` and nothing else.  The same answer for 东京
 * carries a non-empty `pending_destination_label` and `resolver_query_normalized` beside a *null*
 * identity, which is exactly why "the column was not blank" could never be evidence of an identity.
 */
type DestinationReading = {
  spelling: string;
  /** False until this device holds an answer, so a read that never landed cannot join a server group. */
  answered: boolean;
  capability: string | null;
  reason_code: string | null;
  recommended_action: string | null;
  canonical_destination_id: string | null;
  place_count: number | null;
  missing_categories: string[];
  /** This device's own cause when nothing was read: the shared classifier's enum, never a message. */
  failure: string | null;
};

function noAnswerYet(spelling: string, failure: string | null): DestinationReading {
  return {
    spelling,
    answered: false,
    capability: null,
    reason_code: null,
    recommended_action: null,
    canonical_destination_id: null,
    place_count: null,
    missing_categories: [],
    failure,
  };
}

function readFromCapability(spelling: string, answer: DestinationCapability): DestinationReading {
  return {
    spelling,
    answered: true,
    capability: answer.capability ?? null,
    reason_code: answer.reason_code ?? null,
    recommended_action: answer.recommended_action ?? null,
    canonical_destination_id: answer.canonical_destination_id ?? null,
    place_count: Number.isFinite(Number(answer.place_count)) ? Number(answer.place_count) : null,
    missing_categories: Array.isArray(answer.missing_categories) ? answer.missing_categories : [],
    failure: null,
  };
}

/** The three groups the panel shows, in the order the traveller meets them. */
export type DestinationGroup = "supported" | "needs_lookup" | "unknown";
export const DESTINATION_GROUPS: DestinationGroup[] = ["supported", "needs_lookup", "unknown"];

export function groupOfDestination(row: DestinationReading): DestinationGroup {
  if (!row.answered) return "unknown";
  if (row.reason_code === "NO_CANONICAL_IDENTITY") return "needs_lookup";
  if (row.capability === "READY") return "supported";
  /* A `HYDRATABLE` that carries an identity and rows says the server named the place *and* holds
     material for it.  The row prints the verdict beside it, so the heading glosses this and the
     traveller is never left to trust the gloss. */
  if (row.canonical_destination_id && (row.place_count ?? 0) > 0) return "supported";
  return "unknown";
}

/**
 * The identity column, spoken.  A destination the server could not name reads 还没有身份 -- the
 * traveller's own words, the folded form of them and any operation token are *not* identities, so
 * none of them may stand in this slot (see `DestinationResolution` in `anywhere_capability.py`).
 */
export function identityWords(row: DestinationReading, zh: boolean, t: (key: string) => string): string {
  if (!row.answered) return t("setup.identityNotReadYet");
  if (row.canonical_destination_id) return t("setup.theServerNamedIt");
  return t("setup.noIdentityYet");
}

/** The three causes "this place is not here" can have, each said as itself.
 *
 *  Written as a separate function rather than folded into `verdictWords`, because that one speaks about a
 *  DESTINATION and this one speaks about the CATALOG under it.  The three are the building's whole point:
 *  "never registered", "no canonical identity", and "registered but with no coordinate" all used to reach
 *  the traveller as the same empty list, and a traveller who cannot tell them apart cannot act on any of
 *  them.  Each branch says which one it is, carries what the server actually said, and names a next step;
 *  a cause with no step returns null so the screen says the fact and stops, rather than inventing advice.
 */
export function notFoundCauseWords(
  row: DestinationReading | null,
  zh: boolean,
  t: (key: string) => string,
): { title: string; body: string } | null {
  if (!row || !row.answered) return null;
  const spell = row.spelling || t("setup.thisName");

  if (row.reason_code === "NO_CANONICAL_IDENTITY") {
    return {
      title: t("setup.theServerCannotNameThisPlace"),
      body: zh
        ? `服务器说「${spell}」没有任何可追溯来源能把它定成一个目的地。这不是网络问题——服务器刚才答得出来。换个写法，或在"看支持的目的地"里挑一个。`
        : `The server says nothing traceable names "${spell}" as a destination. This is not a network problem: the server just answered. Try another spelling, or pick one from the supported list.`,
    };
  }

  if (row.reason_code === "PLACES_NO_COORDINATE") {
    const n = row.place_count ?? 0;
    return {
      title: t("setup.thePlacesAreHereButNoneHasACoordinate"),
      body: zh
        ? `服务器认得「${spell}」，目录里有 ${n} 条地点，但这些地点没有可用坐标，所以排不出路线、也放不到图上——不是没登记，是登记了而缺坐标。可以先补这些地点的坐标，再规划。`
        : `The server names "${spell}" and the catalog holds ${n} ${englishCountNoun(n, "place")}, but none of them has a usable coordinate, so nothing can be routed or plotted — they are registered, not missing. Their coordinates can be filled in first, and then planning can use them.`,
    };
  }

  if (row.reason_code === "COVERAGE_INCOMPLETE" || (row.missing_categories?.length ?? 0) > 0) {
    const missing = (row.missing_categories ?? []).join(zh ? "、" : ", ");
    const count = row.missing_categories?.length ?? 0;
    return {
      title: t("setup.thisDestinationHasNotBeenPrepared"),
      body: zh
        ? `服务器认得「${spell}」，但还缺 ${count} 类事实（${missing}），所以现在直接规划会缺依据。可以先准备。`
        : `The server names "${spell}" but is short ${count} ${englishCountNoun(count, "category")} (${missing}), so planning now would lack evidence. You can prepare it first.`,
    };
  }

  if ((row.place_count ?? 0) === 0 && row.canonical_destination_id) {
    return {
      title: t("setup.noPlacesAreRegisteredForThisDestination"),
      body: zh
        ? `服务器认得「${spell}」，但目录里一条地点都没有——是还没登记，不是查不到这个名字。`
        : `The server names "${spell}" but the catalog holds no places: they are not registered yet, which is different from the name being unknown.`,
    };
  }

  return null;
}

/** What the server answered, said once in plain words and once in the route's own field values. */
function verdictWords(row: DestinationReading, zh: boolean, t: (key: string) => string): string {
  if (!row.answered) {
    return row.failure
      ? t("trial.verdict.unreadThisRound")
      : t("trial.verdict.notAskedYet");
  }
  if (row.capability === "READY") {
    return t("setup.theServerSaysThisDestinationCanBePlannedNow");
  }
  if (row.reason_code === "NO_CANONICAL_IDENTITY") {
    return t("trial.verdict.unresolvedSpelling");
  }
  if (row.capability === "UNKNOWN_RETRYABLE") {
    return t("setup.itWasAskedAndNothingAnsweredThisRound");
  }
  if (row.canonical_destination_id) {
    return zh
      ? `服务器认得它，目录里有 ${row.place_count ?? 0} 条，还缺 ${row.missing_categories.length} 类事实`
      : `the server names it, holds ${row.place_count ?? 0} ${englishCountNoun(row.place_count ?? 0, "row")} and is short ${row.missing_categories.length} ${englishCountNoun(row.missing_categories.length, "category")}`;
  }
  return t("setup.theServerGaveSomeOtherVerdict");
}

const GROUP_HEAD: Record<DestinationGroup, [string, string, string, string]> = {
  /* [中文标题, English title, 决定这一组的服务器字段名, 给旅客看的依据句在字典里的键].  ORD-0573 加附:
     slot 3 is published as a data-* attribute only, because a machine code must not sit in the text node a
     traveller reads.  It names fields, never verdict values: the values a row actually carries are published
     per row as data-capability / data-reason-code, which is where a reader checks the rule against the row. */
  supported: [
    "已支持：服务器认得它，而且目录里有东西",
    "Supported: the server names it and holds material",
    "capability / canonical_destination_id / place_count",
    "setup.groupRuleSupported",
  ],
  needs_lookup: [
    "需联网才能解析：服务器现在认不出这个名字",
    "Needs a network lookup: nothing the server consults names it",
    "reason_code",
    "setup.groupRuleNeedsLookup",
  ],
  unknown: [
    "未知或无数据：这一轮拿不出可规划的判定",
    "Unknown or empty: no plannable verdict came back this round",
    "capability / answered",
    "setup.groupRuleUnknown",
  ],
};

export function currencyLabel(currency: string, locale: string) {
  const zh = locale.startsWith("zh");
  const table: Record<string, [string, string]> = {
    CNY: ["人民币", "Chinese yuan"],
    JPY: ["日元", "Japanese yen"],
    SGD: ["新加坡元", "Singapore dollar"],
    USD: ["美元", "US dollar"],
    EUR: ["欧元", "Euro"],
  };
  const hit = table[currency];
  return hit ? (zh ? hit[0] : hit[1]) : currency;
}

export function timezoneLabel(timezone: string, locale: string) {
  const zh = locale.startsWith("zh");
  const table: Record<string, [string, string]> = {
    "Asia/Shanghai": ["中国标准时间", "China Standard Time"],
    "Asia/Tokyo": ["日本标准时间", "Japan Standard Time"],
    "Asia/Singapore": ["新加坡时间", "Singapore Time"],
  };
  const hit = table[timezone];
  return hit ? (zh ? hit[0] : hit[1]) : timezone;
}

export function suggestedRoomCount(partySize: number): number {
  if (partySize <= 2) return 1;
  if (partySize <= 4) return 2;
  if (partySize <= 6) return 3;
  return Math.max(3, Math.ceil(partySize / 3));
}

function futureLocalAt(dayOffset: number, hour: number) {
  const value = new Date();
  value.setDate(value.getDate() + dayOffset);
  value.setHours(hour, 0, 0, 0);
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function localDateTimeInZoneToIso(value: string, timeZone: string) {
  const [datePart, timePart] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);
  const localMs = Date.UTC(year, month - 1, day, hour, minute);
  let instantMs = localMs;
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    calendar: "iso8601",
    numberingSystem: "latn",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = Object.fromEntries(
      formatter.formatToParts(new Date(instantMs)).map(({ type, value: part }) => [type, part]),
    );
    const displayedMs = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    );
    instantMs += localMs - displayedMs;
  }
  return new Date(instantMs).toISOString();
}

const PACE_OPTIONS = [
  { key: "relaxed", zh: "轻松", en: "Relaxed" },
  { key: "balanced", zh: "适中", en: "Balanced" },
  { key: "packed", zh: "紧凑", en: "Packed" },
] as const;

const INTEREST_OPTIONS = [
  { key: "food", zh: "美食", en: "Food" },
  { key: "nature", zh: "自然", en: "Nature" },
  { key: "culture", zh: "人文", en: "Culture" },
  { key: "seaside", zh: "海边", en: "Seaside" },
  { key: "shopping", zh: "购物", en: "Shopping" },
  { key: "family", zh: "亲子", en: "Family" },
] as const;

/**
 * ORD-0135 ②: the confirmation step prints what the traveller chose, in the words she chose it
 * from.  A stored key (`relaxed`, `food`) is the product's own vocabulary; showing it asks the
 * traveller to decode the form she just filled in.  An unrecognised key is answered "待确认" rather
 * than echoed -- printing it would look like a label while being a leak.
 */
function optionLabels(
  keys: readonly string[],
  table: readonly { key: string; zh: string; en: string }[],
  zh: boolean,
  t: (key: string) => string,
): string {
  return keys
    .map((key) => {
      const entry = table.find((item) => item.key === key);
      return entry ? (zh ? entry.zh : entry.en) : t("trial.toConfirm");
    })
    .join("、");
}

/**
 * ORD-0135 ③: which step mounts each jump target.  A jump can be taken from the review step, where
 * the input it names is not in the DOM yet, so the route is "go to the owning step, then focus".
 */
const STEP_OF_TARGET: Record<string, 1 | 2 | 3> = {
  "trial-city": 1,
  "trial-arrival": 1,
  "trial-departure": 1,
  "trial-start": 1,
  "trial-end": 1,
  "trial-show-advanced": 1,
  "trial-party": 2,
  "trial-rooms": 2,
  "trial-budget": 2,
  "trial-stay-budget": 2,
  "trial-pace-fieldset": 2,
  "trial-interests-fieldset": 2,
  "trial-special": 2,
};

/** One review row's exit.  The accessible name says which item it changes, because a row of bare
 *  「改这一项」 buttons reads as nothing at all to a screen reader. */
function ReviewEdit({
  row,
  zh,
  onEdit,
}: {
  row: ReviewTarget;
  zh: boolean;
  onEdit: (target: string) => void;
}) {
  const t = useT();
  return (
    <button
      type="button"
      className="trial-review-edit"
      data-testid={`review-edit-${row.name}`}
      data-target={row.target}
      aria-label={(t("trial.changeThisAria")) + (zh ? row.zh : row.en)}
      onClick={() => onEdit(row.target)}
    >
      {t("setup.change2")}
    </button>
  );
}

/**
 * ORD-0350 (HJ-P3): the confirmation step says 我们替你填的 next to values nobody typed, but the way
 * back to one of them was to leave the review step and hunt for the control.  Every row therefore
 * carries its own named exit, and it lands on the control that edits that value -- the same route
 * ORD-0135 ③ already used for a missing field, because a jump from step 3 has to mount the owning
 * step before focusing anything.
 */
type ReviewTarget = { name: string; zh: string; en: string; target: string };

const REVIEW_ROWS: ReviewTarget[] = [
  { name: "city", zh: "目的地", en: "Destination", target: "trial-city" },
  { name: "arrival", zh: "抵达", en: "Arrival", target: "trial-arrival" },
  { name: "departure", zh: "离开", en: "Departure", target: "trial-departure" },
  { name: "party", zh: "人数 / 房间", en: "Travellers / rooms", target: "trial-party" },
  { name: "budget", zh: "总预算 / 住宿", en: "Total / stay budget", target: "trial-budget" },
  { name: "pace", zh: "节奏", en: "Pace", target: "trial-pace-fieldset" },
  { name: "interests", zh: "兴趣", en: "Interests", target: "trial-interests-fieldset" },
  { name: "special", zh: "特殊要求", en: "Special requirements", target: "trial-special" },
  /* The auto-set row edits three values at once, and their controls sit behind a disclosure on step
     one -- so its exit is that disclosure, named as such rather than pointed at a hidden input. */
  { name: "auto-set", zh: "自动设置", en: "Auto-set", target: "trial-show-advanced" },
];

/**
 * ORD-0208 3: the marker that keeps inferred values in their own grammar.  HJ-P1 measured the
 * confirmation step printing 人数 2 / CNY 3000 / 轻松 -- all defaults nobody typed -- in exactly the
 * same style as answers that were typed, beside an honest 「—」 for interests.  One screen, two
 * vocabularies.  This marker is the third state: chosen, unanswered (「—」), and filled in for you.
 */
function DefaultMark({ zh }: { zh: boolean }) {
  const t = useT();
  return (
    <span className="trial-default-mark" data-testid="review-default-mark">
      {" "}
      · {t("setup.weFilledThisInForYou")}
    </span>
  );
}

/**
 * The stages `createJourney` actually awaits (ORD-0047).  A waiting line may name nothing
 * outside this list: a fabricated step is worse than no step, because it teaches the
 * traveller to believe a progress bar that means nothing.
 */
export type TrialPhase = "traveler" | "journey" | "stay-options" | "experience";

/** [中文, English] for each awaited stage. */
const PHASE_LABEL: Record<TrialPhase, [string, string]> = {
  traveler: ["正在登记出行人", "Registering the traveller"],
  journey: ["正在创建行程", "Writing the trip"],
  "stay-options": ["正在搜索住宿", "Looking for stays"],
  experience: ["正在载入行程数据", "Loading your trip"],
};

export function JourneyTrialSetup({
  onCreate,
  onUseSealedDemo,
  sealedDemoUnavailable,
  onCancel,
  busy,
  message,
  createFacts = null,
  phase = null,
  startedAt = null,
  journeyCreated = false,
  stoppedWaiting = false,
  onStopWaiting,
}: {
  onCreate: (draft: JourneyTrialDraft) => Promise<void>;
  onUseSealedDemo: () => Promise<void>;
  /* ORD-0209: named fail-closed reason when the sealed demo cannot be addressed. */
  sealedDemoUnavailable?: string | null;
  /** ORD-0273 wrote this as "technical facts for data-* only".  ORD-0339 (Q71) withdrew that: an
   *  exception's name and sentence may not enter the DOM in any position, so this screen no longer
   *  reads it.  The type stays optional so the call site compiles unchanged. */
  sealedDemoDetail?: { message: string; name: string } | null;
  onCancel?: () => void;
  busy: boolean;
  /* The shell's createJourney catch writes the named backend error into its own state, and
     since ORD-0044 the onboarding call site passes it here -- this screen returns before the
     shell renders state, so without that prop the reason never reaches the user.
     Optional on purpose: the wizard's own "this step did not complete" visibility must not
     depend on the reason being available. */
  message?: string | null;
  /** ORD-0353: this device's readings on the answer that refused the create, so the fold under the
   *  failure can show a measurement instead of a claim about one.  Null means nothing was answered
   *  or measured, and the fold says that by name rather than printing an empty block. */
  createFacts?: RawFacts | null;
  /** Which request the shell is awaiting right now, or null when it is not waiting. */
  phase?: TrialPhase | null;
  /** Epoch millis of the first request in this attempt; the clock must read the wall. */
  startedAt?: number | null;
  /** True once the journey row exists, so the failure copy cannot deny the trip. */
  journeyCreated?: boolean;
  /** The traveller gave up waiting: an outcome line, not a red failure block. */
  stoppedWaiting?: boolean;
  onStopWaiting?: () => void;
}) {
  const t = useT();
  const { locale, switchLocale } = useLocale();
  const zh = locale.startsWith("zh");
  const browserTimezone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai",
    [],
  );
  /* ORD-0072: the neutral basis a trip starts on when this screen has not recognised a
     destination.  Named once because three places have to agree on it -- the fresh draft,
     the reset below when a city stops being recognised, and the sentence the traveller
     reads.  "按中立口径规划" is only honest while the default is a single stated value. */
  const defaultBasis = useMemo(
    () => ({ countryCode: "CN", currency: "CNY", timezone: browserTimezone }),
    [browserTimezone],
  );
  const defaultDraft = useMemo<JourneyTrialDraft>(
    () => ({
      cityName: "",
      countryCode: defaultBasis.countryCode,
      timezone: defaultBasis.timezone,
      startAt: futureLocalAt(1, 10),
      endAt: futureLocalAt(3, 20),
      arrivalLocation: "",
      departureLocation: "",
      budgetMajor: 3000,
      stayBudgetMajor: 1000,
      currency: defaultBasis.currency,
      partySize: 2,
      rooms: 1,
      pace: "relaxed",
      interests: [],
      specialRequirements: "",
    }),
    [browserTimezone],
  );
  /* Read once, before either state exists: a reload must land on the step the traveller
     was on with what they had typed, which is the half of "没有保存记录" that was real. */
  const restored = useRef(readStoredTrial({ step: 1, draft: defaultDraft })).current;
  /* ORD-0208 3: the confirmation step used to print inferred defaults (2 people, CNY 3000 / 1000,
     轻松) in the same visual grammar as typed answers, while an unset interest showed the honest
     「—」.  One screen, two vocabularies.  This set records which fields a person actually chose, so
     the review step can mark the rest as 我们替你填的 instead of passing them off as typed.  A
     restored draft counts as chosen: it is a value somebody accepted earlier, not a fresh default. */
  const [touched, setTouched] = useState<Set<string>>(
    () => new Set(Object.keys(restored.draft).filter((key) => restored.draft[key] !== defaultDraft[key as keyof JourneyTrialDraft])),
  );
  /** Each confirmation row's own way back, addressed by name so a row cannot lose it silently. */
  const reviewEdit = (name: string) => {
    const row = REVIEW_ROWS.find((item) => item.name === name);
    if (!row) return null;
    return <ReviewEdit row={row} zh={zh} onEdit={jumpToField} />;
  };
  const [step, setStep] = useState<1 | 2 | 3>(restored.step);

  /* ORD-0135 ③'s route, now shared with the review rows (ORD-0350): from step 3 the target is on an
     earlier step and not in the DOM yet, so the jump moves first and focuses once it exists. */
  const jumpToField = (target: string) => {
    const owningStep = STEP_OF_TARGET[target] ?? step;
    if (owningStep !== step) setStep(owningStep);
    const focusTarget = () => {
      const node =
        document.getElementById(target) ??
        document.querySelector<HTMLElement>(`[data-testid="${target}"]`);
      node?.focus();
    };
    if (owningStep === step) focusTarget();
    else window.setTimeout(focusTarget, 80);
  };

  const [advanced, setAdvanced] = useState(false);
  /* createJourney catches its own failure and does not rethrow, so a resolved
     `await onCreate()` here does not mean a journey exists.  Its success path closes this
     wizard (V8Experience.tsx setSetupOpen(false)), so still being mounted once the
     await settles is the deterministic signal that the step did not complete. */
  const [createAttemptFailed, setCreateAttemptFailed] = useState(false);
  /* ORD-0066 (甲): a tap on a button that cannot advance has to answer out loud.  A live
     region only announces a *change*, so the region is cleared before the same sentence is
     written back -- otherwise the second blocked tap, the one where the traveller is sure they
     pressed it, would be silent. */
  const [spokenReason, setSpokenReason] = useState("");
  /* ORD-0220 ②: the sentence belongs to a particular set of missing fields.  When that set changes
     the announcement is no longer a report of anything, so it stops being spoken. */
  const [spokenKey, setSpokenKey] = useState<string | null>(null);
  const speakTimer = useRef<number | null>(null);
  useEffect(
    () => () => {
      if (speakTimer.current !== null) window.clearTimeout(speakTimer.current);
    },
    [],
  );
  const speak = (text: string, key: string) => {
    if (speakTimer.current !== null) window.clearTimeout(speakTimer.current);
    setSpokenKey(key);
    setSpokenReason("");
    /* Clear then set: an aria-live region only speaks when its text *changes*, so a second refused
       tap has to re-announce the same sentence (ORD-0086). */
    speakTimer.current = window.setTimeout(() => setSpokenReason(text), 60);
  };
  /**
   * ORD-0220 ③: a refused press has to answer where the traveller is looking.  HJ-P1 measured the
   * same shape three times -- the hint at y=1221..1234 inside an 844px viewport with the sticky
   * 下一步 at y=652 -- and this lane reproduced it independently (`review/evidence/ui-overnight/
   * ord0221-step2-visible-before-after.json`: top 1224, height 85, inViewport false).  Nothing
   * moved, so the press read as a dead button.
   *
   * The order allowed focus **or** scroll.  Only scroll is delivered here, on purpose: focusing the
   * paragraph means giving it `tabIndex={-1}`, and ORD-0066's gate `a11y-blocked-next-takes-focus`
   * carries a deliberate negative control on that exact element ("a non-interactive paragraph took
   * focus, so 'landed' is not measuring focusability") -- it went red the moment the paragraph
   * became focusable (measured: `review/run-run076475.log`, 2 failed / 40 passed).  I do not edit
   * another order's instrument to make my own change pass, so the reason is scrolled into view and
   * the announcement (ORD-0220 ②) carries the rest; the focus half waits for a ruling.
   */
  const revealReason = () => {
    const hint = document.getElementById("trial-required-hint");
    if (!hint) return;
    /* Instant, not smooth.  HJ-P1's discriminating experiment (commander's 19:48 rule): the same
       element moved 0 -> 650 with `scrollIntoView({block:"center"})` five times out of five, while
       `behavior:"smooth"` sampled scrollY=0 six times over 1.2s -- the animation never advances in
       this machine's mobile emulation.  A reason that arrives only if the compositor feels like
       animating is not a testable product behaviour, and the traveller should not have to wait for
       an animation to learn why her press did nothing. */
    hint.scrollIntoView({ block: "center" });
  };
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  /* ORD-0346: what the server answered for each spelling this screen offers, keyed by spelling.
     `null` means this panel has never asked -- the names stay on screen either way, so a read in
     flight cannot empty the list the traveller is looking at. */
  const [destinationReadings, setDestinationReadings] =
    useState<Record<string, DestinationReading> | null>(null);
  const destinationReadSeq = useRef(0);
  const readDestinations = useCallback(async () => {
    const names = zh ? SUPPORTED_CITIES.zh : SUPPORTED_CITIES.en;
    const seq = ++destinationReadSeq.current;
    setDestinationReadings((current) => {
      const next: Record<string, DestinationReading> = { ...(current ?? {}) };
      for (const name of names) next[name] = next[name]?.answered ? next[name] : noAnswerYet(name, null);
      return next;
    });
    const settled = await Promise.allSettled(
      names.map((name) => cityNexusApi.getDestinationCapability(name)),
    );
    if (!mounted.current || seq !== destinationReadSeq.current) return;
    setDestinationReadings((current) => {
      const next: Record<string, DestinationReading> = { ...(current ?? {}) };
      settled.forEach((entry, index) => {
        const name = names[index];
        next[name] =
          entry.status === "fulfilled"
            ? readFromCapability(name, entry.value)
            : /* Q64/Q71: the classifier's enum is this device's conclusion; `entry.reason.message`
                 can carry the proxy's or the origin's own sentence, and none of that crosses here. */
              noAnswerYet(name, classifyReadFailure(entry.reason).reason);
      });
      return next;
    });
  }, [zh]);
  const [draft, setDraft] = useState<JourneyTrialDraft>(() =>
    /* A draft stored by the previous build can name a city the table does not know while
       still carrying the triple of the last city it did know.  Coerce on the way in, so the
       step-1 sentence is true on the first render rather than only after the next keystroke. */
    withNeutralBasis(restored.draft as JourneyTrialDraft, defaultBasis),
  );
  const [roomsTouched, setRoomsTouched] = useState(false);

  /* The destination field asked the LOCAL vocabulary and nothing else, so every sentence under it was a
     statement about this device's table -- which is why a server that answered "six categories are still
     missing" could not be seen here, and the traveller saw a confident "Auto-set" instead.  This reads
     the one name currently typed, once per settled spelling, and keeps the server's own reason beside
     the local facts so the sentence can name WHICH of the three causes it is rather than "nothing here".
     It never blocks the field: a read in flight leaves the previous sentence standing, and a read that
     fails leaves no sentence at all (the local "Auto-set" line is still true about the basis). */
  const [typedReading, setTypedReading] = useState<DestinationReading | null>(null);
  const typedReadSeq = useRef(0);
  const typedName = draft.cityName.trim();
  useEffect(() => {
    if (!typedName) {
      setTypedReading(null);
      return;
    }
    const seq = ++typedReadSeq.current;
    let live = true;
    void cityNexusApi
      .getDestinationCapability(typedName)
      .then((answer) => {
        if (!live || seq !== typedReadSeq.current) return;
        setTypedReading(readFromCapability(typedName, answer));
      })
      .catch((reason: unknown) => {
        if (!live || seq !== typedReadSeq.current) return;
        setTypedReading(noAnswerYet(typedName, classifyReadFailure(reason).reason));
      });
    return () => {
      live = false;
    };
  }, [typedName]);

  useEffect(() => {
    writeStoredTrial(step, draft);
  }, [step, draft]);

  const update = <K extends keyof JourneyTrialDraft>(key: K, value: JourneyTrialDraft[K]) => {
    setCreateAttemptFailed(false);
    setTouched((current) => new Set(current).add(key as string));
    setDraft((current) => ({ ...current, [key]: value }));
  };

  // Corrections §5: infer country / timezone / currency from the city and keep
  // the technical fields behind "Advanced settings".
  const applyCity = (cityName: string) => {
    const facts = inferCityFacts(cityName);
    setDraft((current) =>
      /* The failure branch used to be `{}` -- "leave the hidden fields alone" -- so after a
         Tokyo attempt the trip still planned in JPY and Asia/Tokyo while the screen called
         that the fallback.  An unrecognised city falls back to the neutral basis, never to
         the previous city's. */
      withNeutralBasis(
        {
          ...current,
          cityName,
          ...(facts
            ? { countryCode: facts.country, timezone: facts.timezone, currency: facts.currency }
            : {}),
        },
        defaultBasis,
      ),
    );
  };

  const facts = inferCityFacts(draft.cityName);
  /* ORD-0060 #1: the anchor labels said 厦门 whatever the traveller typed, so a person going
     to Tokyo was asked to "抵达厦门". The name only belongs in a label once the table has
     recognised it; until then the label says what it knows. */
  const identifiedCity = facts ? draft.cityName.trim() : "";
  const unrecognizedCity = draft.cityName.trim().length > 0 && !facts;
  /* ORD-0072 #2: one pass, one basis.  Every screen that names the planning basis reads this
     object -- the step-1 caution, the step-3 confirmation, the auto-set line -- and it is the
     same triple `submit()` hands the shell, so three places cannot tell three stories. */
  const basisWords = {
    country: draft.countryCode,
    currencyCode: draft.currency,
    currency: currencyLabel(draft.currency, locale),
    timezone: draft.timezone,
    zone: timezoneLabel(draft.timezone, locale),
  };
  /* The API requires a non-empty anchor location at both ends
     (`arrival_anchor.location` has minLength 1).  Until now the field looked optional -- a
     placeholder, and a bare "—" on the review page -- so a legal-looking 4-day trip died on
     a 422 the traveller could not see.  Pre-validating here is what ruling ① allows; the
     backend stays the authority. */
  /* Each item carries the control it points at: ORD-0135 ③ asked that "还需要填写" be an exit, not
     only a diagnosis, so every named field is also a thing the traveller can be moved to. */
  type MissingField = { label: string; target: string };
  const missingStep1 = [
    draft.cityName.trim()
      ? null
      : { label: t("trial.navDestination"), target: "trial-city" },
    draft.arrivalLocation.trim()
      ? null
      : { label: t("trial.navArrival"), target: "trial-arrival" },
    draft.departureLocation.trim()
      ? null
      : { label: t("trial.navDeparture"), target: "trial-departure" },
  ].filter(Boolean) as MissingField[];
  /* ORD-0066: step 2 can block too, and a blocked primary button that names the anchors on
     step 1 then falls silent one step later is the same defect moved down the wizard. */
  const missingStep2 = [
    draft.partySize >= ENTRY_FIELDS.party.min
      ? null
      : { label: entryFieldName("party", zh), target: ENTRY_FIELDS.party.testId },
    draft.budgetMajor >= ENTRY_FIELDS.budget.min
      ? null
      : { label: entryFieldName("budget", zh), target: ENTRY_FIELDS.budget.testId },
  ].filter(Boolean) as MissingField[];
  /* ORD-0135 ③ (step 3): the review step already prints 「抵达 未填写 · 必填」 but computed no missing
     list at all, so 确认创建 stayed fully pressable, the `trial-next-reason` slot was empty and no
     jump existed -- the same known fact failing to reach the button.  The anchors are the fields the
     API rejects (the 422 above is about `arrival_anchor.location`), so step 3 reuses the step-1 items
     and their jump targets rather than inventing a second list that could disagree with the display. */
  /* ORD-0216 ③ (HJ-P1 2/2): the review step used to inherit step 2's list verbatim, so a budget
     blocked on step 2 and then filled still printed 「还需要填写：总预算」 on step 3 -- after 201s
     had already gone through.  A hint must be recomputed from the *current* values on every step:
     step 3 carries the anchors (the API's 422 fields) plus the same step-2 predicates evaluated
     against the draft as it stands now, so a field the traveller has since filled drops out of the
     sentence wherever the traveller is. */
  const missingStep3 = [
    ...missingStep1,
    ...missingStep2,
  ];
  const missingNow =
    step === 1 ? missingStep1 : step === 2 ? missingStep2 : missingStep3;
  const blockedNow = missingNow.length > 0;
  /* The identity of "what is missing right now", used to retire an announcement that no longer
     matches the screen (ORD-0220 ②). */
  const missingKey = missingNow.map((field) => field.target).join("|");
  /* One sentence, read by the visible hint and by the announcement a blocked tap makes, so
     what a sighted traveller sees and what a screen reader says cannot diverge. */
  const missingLine = missingNow.length
    ? step === 3
      ? zh
        ? `还需要填写：${missingNow.map((field) => `${field.label} 未填写 · 必填`).join("、")}`
        : `Still needed: ${missingNow.map((field) => `${field.label} not filled in · required`).join(", ")}`
      : zh
        ? `还需要填写：${missingNow.map((field) => field.label).join("、")}`
        : `Still needed: ${missingNow.map((field) => field.label).join(", ")}`
    : "";
  /* The backend's own words, routed to the field it named. */
  const arrivalProblem = fieldProblem(message, /arrival_anchor/);
  const departureProblem = fieldProblem(message, /departure_anchor/);
  /* ORD-0047: the wait has to be countable while it runs.  Only a stage the shell really
     awaited may be named, and only the wall clock may say how long. */
  const waited = useElapsedSeconds(busy ? startedAt : null);
  const phaseLabel = phase ? PHASE_LABEL[phase] : null;

  const stepTitle = zh
    ? ["目的地与时间", "人数与偏好", "确认创建"]
    : ["Destination & dates", "Travellers & preferences", "Review & create"];

  const submit = async () => {
    setCreateAttemptFailed(false);
    await onCreate(draft);
    /* Still mounted means the step did not complete.  Unmounted means the shell took its
       success path, so the draft has been consumed and must not be offered again. */
    if (mounted.current) setCreateAttemptFailed(true);
    else clearStoredTrial();
  };

  return (
    <section className="v8-page cn-onboarding" data-testid="trial-setup">
      <div className="cn-onboarding__scroll" data-testid="trial-scroll">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("trial.kicker")}</p>
          <h1>{t("setup.createATrip")}</h1>
          <p className="v8-lede">
            {t("trial.lede.threeSteps")}
          </p>
        </div>
        <button
          type="button"
          className="v8-outline-button"
          aria-label="Switch language"
          onClick={switchLocale}
        >
          {t("nav.language")}
        </button>
      </div>

      <ol className="trial-steps" data-testid="trial-steps">
        {stepTitle.map((label, index) => {
          const n = (index + 1) as 1 | 2 | 3;
          return (
            <li
              key={label}
              className={n === step ? "active" : n < step ? "done" : ""}
              data-testid={`trial-step-${n}`}
            >
              <span className="trial-step-dot">{n < step ? "✓" : n}</span>
              <span>{label}</span>
            </li>
          );
        })}
      </ol>

      {step === 1 && (
        <div className="v8-card trial-card" data-testid="trial-step1-body">
          <label className="trial-field">
            <span>{t("trial.destination")}</span>
            <input
              data-testid="trial-city"
              value={draft.cityName}
              onChange={(event) => applyCity(event.target.value)}
              placeholder={t("setup.eGTianjinTokyoSingapore")}
              aria-describedby={unrecognizedCity ? "trial-city-warning" : undefined}
              autoFocus
            />
          </label>

          {!unrecognizedCity && notFoundCauseWords(typedReading, zh, t) ? (
            /* Which of the three causes it is, said before the basis line rather than instead of it.
               Gated on `!unrecognizedCity` because the paragraph below already speaks for the
               "no local facts" case, and the first draft of this branch said the same thing a second
               time in different words -- two sentences for one fact reads as two facts.  This branch
               exists for the causes that paragraph cannot see: the server answered, the destination
               resolved, and the reason is about the CATALOG rather than about the name. */
            <p
              className="trial-city-warning"
              data-testid="trial-not-found-cause"
              id="trial-not-found-cause"
              role="status"
            >
              {zh
                ? `${notFoundCauseWords(typedReading, zh, t)?.title}：${notFoundCauseWords(typedReading, zh, t)?.body}`
                : `${notFoundCauseWords(typedReading, zh, t)?.title}: ${notFoundCauseWords(typedReading, zh, t)?.body}`}
            </p>
          ) : null}
          {facts ? (
            <p className="trial-inferred" data-testid="trial-inferred">
              {t("trial.autoSetPrefix")}
              {zh ? facts.labelZh : facts.labelEn} · {basisWords.currency} · {basisWords.zone}
            </p>
          ) : null}
          {unrecognizedCity && (
            /* ORD-0060 #2 + ORD-0072: `inferCityFacts` returns nothing here, and the old
               `applyCity` left the hidden triple holding the *previous* city's values -- so this
               sentence read "still planning with JP / JPY / Asia/Tokyo" about a city it had just
               admitted it did not know.  The basis quoted below is the one `submit()` carries. */
            <p
              className="trial-city-warning"
              data-testid="trial-city-warning"
              id="trial-city-warning"
              role="status"
            >
              {zh
                ? `没认出「${draft.cityName.trim()}」：已退回中立口径 ${basisWords.country} / ${basisWords.currency}（${basisWords.currencyCode}）/ ${basisWords.timezone} 规划，不沿用上一次识别到的城市。换个写法，或在"看支持的目的地"里挑一个。`
                : `"${draft.cityName.trim()}" is not recognised: planning falls back to the neutral basis ${basisWords.country} / ${basisWords.currency} (${basisWords.currencyCode}) / ${basisWords.timezone}, and does not keep the city you last recognised. Try another spelling, or pick one from "See supported destinations".`}
            </p>
          )}
          <details
            className="trial-supported"
            data-testid="trial-supported-cities"
            onToggle={(event) => {
              /* One round of reads per opening, and only because the traveller asked to see this.
                 The panel cannot say anything about a destination it has not asked about, so the
                 names are listed first and the server's answer is attached as it lands. */
              if (event.currentTarget.open) void readDestinations();
            }}
          >
            {/* ORD-0060 #3 still holds for the entry itself: the summary carries no headcount, because
                the number of supported destinations is not this table's to publish.  ORD-0346 changed
                what the *body* is: it used to print this client-side spelling table under the words
                "supported destinations", which is what a traveller read as a promise.  The body now
                groups the same names by what `GET /destinations/capability` answered for each one. */}
            <summary data-testid="trial-supported-toggle">
              {t("setup.seeSupportedDestinations")}
            </summary>
            {DESTINATION_GROUPS.map((group) => {
              const rows = (zh ? SUPPORTED_CITIES.zh : SUPPORTED_CITIES.en)
                .map((name) => (destinationReadings && destinationReadings[name]) || noAnswerYet(name, null))
                .filter((row) => groupOfDestination(row) === group);
              return (
                <section
                  className="trial-supported-group"
                  key={group}
                  data-testid={`trial-supported-group-${group}`}
                >
                  <h4 className="trial-supported-group-title">{zh ? GROUP_HEAD[group][0] : GROUP_HEAD[group][1]}</h4>
                  <p
                    className="trial-supported-group-rule"
                    data-testid={`trial-supported-group-rule-${group}`}
                    data-server-fields={GROUP_HEAD[group][2]}
                  >
                    {t(GROUP_HEAD[group][3])}
                  </p>
                  {rows.length === 0 ? (
                    <p className="trial-supported-none" data-testid={`trial-supported-none-${group}`}>
                      {t("setup.noNameLandedInThisGroupThisRound")}
                    </p>
                  ) : (
                    <ul className="trial-supported-list">
                      {rows.map((row) => (
                        <li
                          key={row.spelling}
                          className="trial-supported-row"
                          data-testid={`trial-supported-row-${row.spelling}`}
                          data-answered={row.answered ? "yes" : "no"}
                          data-capability={row.capability ?? undefined}
                          data-reason-code={row.reason_code ?? undefined}
                          data-recommended-action={row.recommended_action ?? undefined}
                          /* The identity column.  Absent, not filled in, when there is no identity:
                             a placeholder here is what let `unresolved:<hash>` pass for a name. */
                          data-canonical-destination-id={row.canonical_destination_id ?? undefined}
                        >
                          <span className="trial-supported-name">{row.spelling}</span>
                          <span
                            className="trial-supported-identity"
                            data-testid={`trial-supported-identity-${row.spelling}`}
                          >
                            {identityWords(row, zh, t)}
                          </span>
                          <span className="trial-supported-verdict">{verdictWords(row, zh, t)}</span>
                          <span
                            className="trial-supported-fields"
                            data-testid={`trial-supported-fields-${row.spelling}`}
                          >
                            {row.answered
                              ? `${row.capability} · ${row.reason_code} · ${row.recommended_action}`
                              : (row.failure ?? "not-asked")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              );
            })}
          </details>

          <label className="trial-field">
            <span>{zh ? (identifiedCity ? `抵达${identifiedCity}` : "抵达地点") : "Arrive at"}</span>
            <input
              data-testid="trial-arrival"
              value={draft.arrivalLocation}
              onChange={(event) => update("arrivalLocation", event.target.value)}
              placeholder={
                zh
                  ? `例如：${identifiedCity || "某地"}站 / 机场`
                  : "e.g. station or airport"
              }
              aria-required="true"
              aria-invalid={
                draft.arrivalLocation.trim() && !arrivalProblem ? undefined : true
              }
              aria-describedby={
                arrivalProblem
                  ? "trial-required-hint trial-arrival-problem"
                  : draft.arrivalLocation.trim()
                    ? undefined
                    : "trial-required-hint"
              }
            />
            {arrivalProblem && (
              <span className="trial-field-problem" data-testid="trial-arrival-problem" role="alert">
                {arrivalProblem}
              </span>
            )}
          </label>
          <label className="trial-field">
            <span>{zh ? (identifiedCity ? `离开${identifiedCity}` : "离开地点") : "Depart from"}</span>
            <input
              data-testid="trial-departure"
              value={draft.departureLocation}
              onChange={(event) => update("departureLocation", event.target.value)}
              placeholder={
                zh
                  ? `例如：${identifiedCity || "某地"}站 / 机场`
                  : "e.g. station or airport"
              }
              aria-required="true"
              aria-invalid={
                draft.departureLocation.trim() && !departureProblem ? undefined : true
              }
              aria-describedby={
                departureProblem
                  ? "trial-required-hint trial-departure-problem"
                  : draft.departureLocation.trim()
                    ? undefined
                    : "trial-required-hint"
              }
            />
            {departureProblem && (
              <span className="trial-field-problem" data-testid="trial-departure-problem" role="alert">
                {departureProblem}
              </span>
            )}
          </label>
          <div className="trial-row">
            <label className="trial-field">
              <span>{t("setup.arrivalTime")}</span>
              <input
                data-testid="trial-start"
                type="datetime-local"
                value={draft.startAt}
                onChange={(event) => update("startAt", event.target.value)}
              />
            </label>
            <label className="trial-field">
              <span>{t("setup.departureTime")}</span>
              <input
                data-testid="trial-end"
                type="datetime-local"
                value={draft.endAt}
                onChange={(event) => update("endAt", event.target.value)}
              />
            </label>
          </div>

          <details
            className="trial-advanced"
            open={advanced}
            onToggle={(event) => setAdvanced((event.target as HTMLDetailsElement).open)}
          >
            <summary>{t("setup.advancedSettings")}</summary>
            <div className="trial-row">
              <label className="trial-field">
                <span>{t("trial.country")}</span>
                <input
                  data-testid="trial-country"
                  value={draft.countryCode}
                  onChange={(event) => update("countryCode", event.target.value.toUpperCase().slice(0, 3))}
                />
              </label>
              <label className="trial-field">
                <span>{t("trial.timezone")}</span>
                <input
                  data-testid="trial-timezone"
                  value={draft.timezone}
                  onChange={(event) => update("timezone", event.target.value)}
                />
              </label>
              <label className="trial-field">
                <span>{t("trial.currency")}</span>
                <input
                  data-testid="trial-currency"
                  value={draft.currency}
                  onChange={(event) => update("currency", event.target.value.toUpperCase().slice(0, 3))}
                />
              </label>
            </div>
          </details>
          {/* ORD-0264: this opener used to render in the page-bottom secondary row, where its centre
              measured y=1208 in an 844px viewport -- on a phone it was permanently below the fold and
              untappable. It now sits directly under the details it opens. The width (350×44) and the
              min-height the class-level floor gives it are unchanged; only its position moved. */}
          {step === 1 && (
            <button
              type="button"
              className="trial-back-link"
              data-testid="trial-show-advanced"
              onClick={() => {
                setAdvanced(true);
                const node = document.querySelector(".trial-advanced") as HTMLDetailsElement | null;
                if (node) node.open = true;
              }}
            >
              {t("setup.advancedSettings")}
            </button>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="v8-card trial-card" data-testid="trial-step2-body">
          <div className="trial-row">
            <label className="trial-field">
              <span data-testid="trial-party-label">{entryFieldLabel("party", zh)}</span>
              <input
                data-testid="trial-party"
                type="number"
                {...entryFieldBounds("party")}
                value={draft.partySize}
                onChange={(event) => {
                  const partySize = Number(event.target.value);
                  setDraft((current) => ({
                    ...current,
                    partySize,
                    ...(roomsTouched ? {} : { rooms: suggestedRoomCount(partySize) }),
                  }));
                }}
              />
            </label>
            <label className="trial-field">
              <span data-testid="trial-rooms-label">{`${t("trial.rooms")}${entryFieldSuffix("rooms", zh)}`}</span>
              <input
                data-testid="trial-rooms"
                type="number"
                {...entryFieldBounds("rooms")}
                value={draft.rooms}
                onChange={(event) => {
                  setRoomsTouched(true);
                  update("rooms", Number(event.target.value));
                }}
              />
            </label>
          </div>

          <div className="trial-row">
            <label className="trial-field">
              <span data-testid="trial-budget-label">{entryFieldLabel("budget", zh)}</span>
              <input
                data-testid="trial-budget"
                type="number"
                {...entryFieldBounds("budget")}
                value={draft.budgetMajor}
                onChange={(event) => update("budgetMajor", Number(event.target.value))}
              />
            </label>
            <label className="trial-field">
              <span data-testid="trial-stay-budget-label">{`${t("trial.stayBudget")}${entryFieldSuffix("stayBudget", zh)}`}</span>
              <input
                data-testid="trial-stay-budget"
                type="number"
                {...entryFieldBounds("stayBudget")}
                value={draft.stayBudgetMajor}
                onChange={(event) => update("stayBudgetMajor", Number(event.target.value))}
              />
            </label>
          </div>

          <fieldset className="trial-fieldset" data-testid="trial-pace-fieldset" tabIndex={-1}>
            <legend>{t("setup.pace")}</legend>
            <div className="trial-chips">
              {PACE_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={draft.pace === option.key ? "active" : ""}
                  /* ORD-0208 2: the selected state was colour alone -- a screen reader or a
                     colour-blind traveller could not tell which chip was on.  A toggle control
                     carries its state in `aria-pressed`; it stays a plain click, and it is never
                     `aria-disabled`, which this browser treats as unclickable. */
                  aria-pressed={draft.pace === option.key}
                  data-testid={`trial-pace-${option.key}`}
                  onClick={() => update("pace", option.key)}
                >
                  {zh ? option.zh : option.en}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="trial-fieldset" data-testid="trial-interests-fieldset" tabIndex={-1}>
            <legend>{t("setup.interests")}</legend>
            <div className="trial-chips">
              {INTEREST_OPTIONS.map((option) => {
                const selected = (draft.interests ?? []).includes(option.key);
                return (
                  <button
                    key={option.key}
                    type="button"
                    className={selected ? "active" : ""}
                    aria-pressed={selected}
                    data-testid={`trial-interest-${option.key}`}
                    onClick={() =>
                      update(
                        "interests",
                        selected
                          ? (draft.interests ?? []).filter((item) => item !== option.key)
                          : [...(draft.interests ?? []), option.key],
                      )
                    }
                  >
                    {zh ? option.zh : option.en}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="trial-field">
            <span>{t("setup.specialRequirements")}</span>
            <textarea
              data-testid="trial-special"
              rows={3}
              value={draft.specialRequirements ?? ""}
              onChange={(event) => update("specialRequirements", event.target.value)}
              placeholder={t("trial.special.placeholder")}
            />
          </label>
        </div>
      )}

      {step === 3 && (
        <div className="v8-card trial-card" data-testid="trial-step3-body">
          <dl className="trial-review">
            <div>
              <dt>{t("trial.destination")}{reviewEdit("city")}</dt>
              <dd data-testid="review-city">{draft.cityName || "—"}</dd>
              {/* The step-1 caution has to be here too: this is the screen the traveller
                  confirms from, and an assumption shown only two steps back is gone.
                  What is *not* repeated here is the enumeration of the neutral basis: step 1 already
                  says 「按中立口径 CN / 人民币（CNY）/ Asia/Shanghai 规划」 in full, and printing that
                  forty-character list a second time on the confirmation screen is what pushed this
                  row to wrap over three lines on a 390px phone. The caution itself stays. */}
              {unrecognizedCity && (
                <dd className="trial-city-warning" data-testid="review-city-warning">
                  {t("trial.review.unrecognizedCity")}
                </dd>
              )}
            </div>
            <div>
              <dt>{roleLabel("ARRIVAL", zh)}{reviewEdit("arrival")}</dt>
              {/* A bare "—" read as an acceptable blank, and the API rejects it. Say so here. */}
              <dd
                data-testid="review-arrival"
                data-missing={draft.arrivalLocation.trim() ? undefined : "true"}
              >
                {draft.arrivalLocation.trim() || t("setup.notFilledInRequired")}
                {" · "}
                {draft.startAt.replace("T", " ")}
              </dd>
            </div>
            <div>
              <dt>{t("trial.departureField")}{reviewEdit("departure")}</dt>
              <dd
                data-testid="review-departure"
                data-missing={draft.departureLocation.trim() ? undefined : "true"}
              >
                {draft.departureLocation.trim() || (t("setup.notFilledInRequired"))}
                {" · "}
                {draft.endAt.replace("T", " ")}
              </dd>
            </div>
            <div>
              <dt>{t("setup.travellersRooms")}{reviewEdit("party")}</dt>
              <dd data-testid="review-party">
                {draft.partySize} · {draft.rooms}
                {!touched.has("partySize") && <DefaultMark zh={zh} />}
              </dd>
            </div>
            <div>
              <dt>{t("setup.totalStayBudget")}{reviewEdit("budget")}</dt>
              <dd data-testid="review-budget">
                {draft.currency} {draft.budgetMajor} / {draft.stayBudgetMajor}
                {(!touched.has("budgetMajor") || !touched.has("stayBudgetMajor")) && <DefaultMark zh={zh} />}
              </dd>
            </div>
            <div>
              <dt>{t("setup.pace2")}{reviewEdit("pace")}</dt>
              <dd data-testid="review-pace">
                {optionLabels(draft.pace ? [draft.pace] : [], PACE_OPTIONS, zh, t) || "—"}
                {!touched.has("pace") && <DefaultMark zh={zh} />}
              </dd>
            </div>
            <div>
              <dt>{t("setup.interests")}{reviewEdit("interests")}</dt>
              <dd data-testid="review-interests">
                {optionLabels(draft.interests ?? [], INTEREST_OPTIONS, zh, t) || "—"}
              </dd>
            </div>
            <div>
              <dt>{t("setup.specialRequirements")}{reviewEdit("special")}</dt>
              <dd data-testid="review-special">{draft.specialRequirements || "—"}</dd>
            </div>
            <div>
              <dt>{t("setup.autoSet2")}{reviewEdit("auto-set")}</dt>
              <dd>
                {draft.countryCode} · {draft.currency} · {draft.timezone}
              </dd>
            </div>
          </dl>
          {onCancel && (
            <button type="button" className="trial-back-link" onClick={onCancel}>
              {t("trial.cancel")}
            </button>
          )}
        </div>
      )}

      {createAttemptFailed && !stoppedWaiting && (
        /* Directly above the confirm button, so the reason is where the tap was.
           Gated on createAttemptFailed rather than on `message` alone: the shell's message
           is shared state and could carry text from an unrelated earlier step. */
        <div className="trial-create-error" data-testid="trial-create-error" role="alert">
          <strong>
            {journeyCreated
              ? t("setup.stepFailedStaySearchOnly")
              : t("trial.create.stepFailedNoJourney")}
          </strong>
          {message ? <span>{message}</span> : null}
          {/* ORD-0353: the phone gate counted zero <details> blocks on this failure, which left the
              recitable number the server sends with nowhere to be read aloud.  The fold stays closed
              -- the traveller gets this screen's sentence first -- and inside it there is only what
              this device measured plus the server's own number. */}
          <details className="trial-technical" data-testid="create-technical-details">
            <summary data-testid="create-technical-toggle">
              {t("hub.continuationTechnicalDetail")}
            </summary>
            {createFacts ? (
              <RawFactsPanel
                facts={createFacts}
                zh={zh}
                testId="create-raw-facts"
                nameMissingReceipt
              />
            ) : (
              /* No `data-cnx-field` here on purpose: "this device has nothing measured" is not the
                 same reading as "no answer arrived", and naming a contract field with a value this
                 screen did not measure is the invention Q68 forbids. */
              <span className="trial-technical-none" data-testid="create-technical-none">
                {t("trial.create.nothingMeasured")}
              </span>
            )}
          </details>
        </div>
      )}
      {stoppedWaiting && !busy && message && (
        /* Giving up on the wait is not a failure and not a cancel: the request this screen
           stopped is described by what actually happened to it. */
        <div className="trial-wait-outcome" data-testid="trial-wait-outcome" role="status">
          <strong>{t("setup.stoppedWaiting")}</strong>
          <span>{message}</span>
        </div>
      )}
      {blockedNow && (
        /* A greyed-out "Next" with no reason is the same silence as a create that dies
           quietly, so name what is missing.  Stable id: the blocked button describes itself
           with this element, so the relation cannot dangle between keystrokes. */
        <p
          className="trial-required-hint"
          id="trial-required-hint"
          data-testid="trial-required-hint"
          role="status"
        >
          {/* ORD-0135 ③: naming a missing field is a diagnosis; the traveller also needs the route.
              Each item is a real control that puts the cursor in the field it names -- rendered inline
              rather than as its own row, because a row of buttons pushed this wizard's sticky CTA
              under the fixed simulation ball (measured by the mobile gate at 360x800: 33px). */}
          {missingNow.length
            ? t("setup.stillNeeded")
            : ""}
          {missingNow.map((field, index) => (
            <span key={field.target}>
              {index > 0 ? (zh ? "、" : ", ") : ""}
              <button
                type="button"
                className="trial-missing-jump"
                data-testid="trial-missing-jump"
                data-target={field.target}
                onClick={() => jumpToField(field.target)}
              >
                {field.label}
              </button>
              {/* ORD-0135 ③: the review step's rows already say 未填写 · 必填 for this field, and the
                  reason the blocked 确认创建 points at should be that same sentence rather than a
                  second phrasing of it. */}
              {step === 3 ? (t("trial.notFilledRequired")) : ""}
            </span>
          ))}
        </p>
      )}
      {/* Polite, and empty until a tap is refused: the visible hint above already carries the
          words for sighted travellers, so this region exists for the announcement alone.
          ORD-0220 ②: it also has to stop.  A snapshot of an old missing-list keeps being re-read by
          a screen reader after the traveller has fixed the field, which is the same stale-hint
          defect on the only surface she cannot see -- so the sentence is shown only while the set it
          was spoken for is still the set on screen. */}
      <p
        className="v8-sr-only"
        id="trial-next-reason"
        data-testid="trial-next-reason"
        role="status"
        aria-live="polite"
      >
        {spokenKey === missingKey ? spokenReason : ""}
      </p>
      {busy && phaseLabel && (
        /* ORD-0047: this wait measured 114.98s on a cold city through the production
           preview with nothing on screen, so a traveller tapping 确认创建 once could not tell
           "working" from "broken" and tapped again. */
        <div
          className="trial-wait"
          data-testid="trial-wait"
          data-phase={phase ?? ""}
          data-elapsed-seconds={waited}
          role="status"
        >
          <p className="trial-wait-line">
            <span className="trial-wait-pulse" aria-hidden="true" />
            <span>{zh ? phaseLabel[0] : phaseLabel[1]}</span>
            <b data-testid="trial-wait-elapsed">
              {zh ? `已等待 ${waited} 秒` : `waiting ${waited}s`}
            </b>
          </p>
          <p className="trial-wait-note">
            {t("trial.wait.whySeconds")}
          </p>
          {onStopWaiting && (
            <button
              type="button"
              className="v8-outline-button trial-wait-stop"
              data-testid="trial-stop-waiting"
              onClick={onStopWaiting}
            >
              {t("agent.aiRunStop")}
            </button>
          )}
          <p className="trial-wait-hint">
            {t("trial.wait.stopOnlyClosesView")}
          </p>
        </div>
      )}

      {/* Secondary, de-emphasised: the sealed demo is not the golden path. */}
      {sealedDemoUnavailable && (
        /* ORD-0209 5: fail-closed with the reason, never a silent creation fallback.
           ORD-0273-TEXT: the sentence is an i18n key, never the error's own words.
           ORD-0339 (Q71): those words may not ride in `data-*` either.  An attribute is not on
           screen, but it is in the DOM, and from there a screen reader, an export or any later
           render can speak it.  What may land here is a Q64 field this device measured, with its
           contract-name anchor (Q70) - and nothing that comes out of an exception.
           ORD-0273-ACTION: an executable next step travels with the failure -- retry the same
           read here; creating one's own trip stays available below regardless. */
        <div
          className="trial-city-warning"
          data-testid="trial-sealed-unavailable"
          role="alert"
        >
          <p>{sealedDemoUnavailable}</p>
          <button
            type="button"
            className="trial-back-link"
            data-testid="trial-sealed-retry"
            disabled={busy}
            onClick={() => void onUseSealedDemo()}
          >
            {t("trial.retry")}
          </button>
        </div>
      )}
      <div className="trial-secondary">
        {/* ORD-0216 ④: the label comes from `trial.tianjinDemo` and must stay **city-neutral** --
            `GET /api/v1/demo/scene` decides which sealed journey this hands over, so naming a city
            here is the `HUMAN_MISLEADING` defect HJ-P1 read with her own eyes.  The test id keeps
            its original spelling deliberately: it is a gate hook other specs select on, not text a
            traveller can see, and renaming it would break their reach for no product gain. */}
        <button
          type="button"
          className="trial-back-link"
          data-testid="trial-tianjin-demo"
          disabled={busy}
          onClick={() => void onUseSealedDemo()}
        >
          {t("trial.tianjinDemo")}
        </button>
      </div>
      </div>{/* /cn-onboarding__scroll */}

      {/* ORD-0338 (甲): the CTA is the pane's own bottom row, so nothing it used to cover
          is left under chrome.  It is deliberately the last child of the section. */}
      <div className="trial-sticky-cta" data-testid="trial-sticky-cta">
        {step > 1 && (
          <button
            type="button"
            className="v8-outline-button"
            data-testid="trial-back"
            disabled={busy}
            onClick={() => setStep((current) => (current === 3 ? 2 : 1))}
          >
            {t("setup.back")}
          </button>
        )}
        {step < 3 && (
          <button
            type="button"
            className="v8-primary-button"
            data-testid="trial-next"
            /* ORD-0066 (甲): `disabled` kept this control out of the tab sequence, so a screen
               reader user never reached the button -- and never heard the reason parked beside
               it.  Measured on the rebuilt production bundle: focus could not land even with
               `aria-describedby` injected.  aria-disabled carries the same "not yet" semantics
               while staying focusable; the click below still refuses to advance and says why. */
            aria-disabled={blockedNow ? "true" : undefined}
            aria-describedby={blockedNow ? "trial-required-hint" : undefined}
            onClick={() => {
              if (blockedNow) {
                speak(missingLine, missingKey);
                revealReason();
                return;
              }
              setStep((current) => (current === 1 ? 2 : 3));
            }}
          >
            {t("trial.next")}
          </button>
        )}
        {step === 3 && (
          <button
            type="button"
            className="v8-primary-button"
            data-testid="trial-create"
            disabled={busy}
            /* ORD-0135 ③: the review step knows which fields are missing (it prints 未填写 · 必填 for
               each) and that knowledge has to reach this control.  Same accessible form as 下一步:
               `aria-disabled` rather than `disabled`, because a hard-disabled button leaves the tab
               sequence and the reason beside it is then unreachable (ORD-0066 甲, measured). */
            aria-disabled={blockedNow ? "true" : undefined}
            aria-describedby={blockedNow ? "trial-required-hint" : undefined}
            onClick={() => {
              if (blockedNow) {
                speak(missingLine, missingKey);
                revealReason();
                return;
              }
              void submit();
            }}
          >
            {busy ? t("trial.creating") : t("setup.createTrip")}
          </button>
        )}
      </div>
    </section>
  );
}
