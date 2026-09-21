import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useT } from "../../i18n/LocaleContext";
import { useElapsedSeconds } from "../../lib/waitClock";

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
): string {
  return keys
    .map((key) => {
      const entry = table.find((item) => item.key === key);
      return entry ? (zh ? entry.zh : entry.en) : zh ? "待确认" : "to confirm";
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
  "trial-party": 2,
  "trial-budget": 2,
};

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
  onUseTianjinDemo,
  onCancel,
  busy,
  message,
  phase = null,
  startedAt = null,
  journeyCreated = false,
  stoppedWaiting = false,
  onStopWaiting,
}: {
  onCreate: (draft: JourneyTrialDraft) => Promise<void>;
  onUseTianjinDemo: () => Promise<void>;
  onCancel?: () => void;
  busy: boolean;
  /* The shell's createJourney catch writes the named backend error into its own state, and
     since ORD-0044 the onboarding call site passes it here -- this screen returns before the
     shell renders state, so without that prop the reason never reaches the user.
     Optional on purpose: the wizard's own "this step did not complete" visibility must not
     depend on the reason being available. */
  message?: string | null;
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
  const [step, setStep] = useState<1 | 2 | 3>(restored.step);
  const [advanced, setAdvanced] = useState(false);
  /* createJourney catches its own failure and does not rethrow, so a resolved
     `await onCreate()` here does not mean a journey exists.  Its success path closes this
     wizard (V8Experience.tsx:577 setSetupOpen(false)), so still being mounted once the
     await settles is the deterministic signal that the step did not complete. */
  const [createAttemptFailed, setCreateAttemptFailed] = useState(false);
  /* ORD-0066 (甲): a tap on a button that cannot advance has to answer out loud.  A live
     region only announces a *change*, so the region is cleared before the same sentence is
     written back -- otherwise the second blocked tap, the one where the traveller is sure they
     pressed it, would be silent. */
  const [spokenReason, setSpokenReason] = useState("");
  const speakTimer = useRef<number | null>(null);
  useEffect(
    () => () => {
      if (speakTimer.current !== null) window.clearTimeout(speakTimer.current);
    },
    [],
  );
  const speak = (text: string) => {
    if (speakTimer.current !== null) window.clearTimeout(speakTimer.current);
    setSpokenReason("");
    speakTimer.current = window.setTimeout(() => setSpokenReason(text), 60);
  };
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [draft, setDraft] = useState<JourneyTrialDraft>(() =>
    /* A draft stored by the previous build can name a city the table does not know while
       still carrying the triple of the last city it did know.  Coerce on the way in, so the
       step-1 sentence is true on the first render rather than only after the next keystroke. */
    withNeutralBasis(restored.draft as JourneyTrialDraft, defaultBasis),
  );
  const [roomsTouched, setRoomsTouched] = useState(false);

  useEffect(() => {
    writeStoredTrial(step, draft);
  }, [step, draft]);

  const update = <K extends keyof JourneyTrialDraft>(key: K, value: JourneyTrialDraft[K]) => {
    setCreateAttemptFailed(false);
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
      : { label: zh ? "目的地" : "the destination", target: "trial-city" },
    draft.arrivalLocation.trim()
      ? null
      : { label: zh ? "抵达地点" : "where you arrive", target: "trial-arrival" },
    draft.departureLocation.trim()
      ? null
      : { label: zh ? "离开地点" : "where you leave", target: "trial-departure" },
  ].filter(Boolean) as MissingField[];
  /* ORD-0066: step 2 can block too, and a blocked primary button that names the anchors on
     step 1 then falls silent one step later is the same defect moved down the wizard. */
  const missingStep2 = [
    draft.partySize >= 1
      ? null
      : { label: zh ? "旅行人数" : "the number of travellers", target: "trial-party" },
    draft.budgetMajor > 0
      ? null
      : { label: zh ? "总预算" : "the total budget", target: "trial-budget" },
  ].filter(Boolean) as MissingField[];
  /* ORD-0135 ③ (step 3): the review step already prints 「抵达 未填写 · 必填」 but computed no missing
     list at all, so 确认创建 stayed fully pressable, the `trial-next-reason` slot was empty and no
     jump existed -- the same known fact failing to reach the button.  The anchors are the fields the
     API rejects (the 422 above is about `arrival_anchor.location`), so step 3 reuses the step-1 items
     and their jump targets rather than inventing a second list that could disagree with the display. */
  const missingStep3 = missingStep1;
  const missingNow =
    step === 1 ? missingStep1 : step === 2 ? missingStep2 : missingStep3;
  const blockedNow = missingNow.length > 0;
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
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("trial.kicker")}</p>
          <h1>{zh ? "新建行程" : "Create a trip"}</h1>
          <p className="v8-lede">
            {zh
              ? "三步完成。选择目的地、告诉我们怎么玩，剩下的交给 CityNexus。"
              : "Three steps. Pick a destination, tell us how you like to travel, and let CityNexus handle the rest."}
          </p>
        </div>
        <button
          type="button"
          className="v8-outline-button"
          aria-label="Switch language"
          onClick={switchLocale}
        >
          {zh ? "EN" : "中文"}
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
            <span>{zh ? "目的地" : "Destination"}</span>
            <input
              data-testid="trial-city"
              value={draft.cityName}
              onChange={(event) => applyCity(event.target.value)}
              placeholder={zh ? "例如：天津、东京、新加坡" : "e.g. Tianjin, Tokyo, Singapore"}
              aria-describedby={unrecognizedCity ? "trial-city-warning" : undefined}
              autoFocus
            />
          </label>

          {facts ? (
            <p className="trial-inferred" data-testid="trial-inferred">
              {zh ? "已自动设置：" : "Auto-set: "}
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
          <details className="trial-supported" data-testid="trial-supported-cities">
            {/* No count is printed: the authoritative number of supported cities is not this
                lane's to derive, and a headcount read off the local table would be its own
                claim. The names the table does know are shown, which is what a traveller
                can act on. */}
            <summary data-testid="trial-supported-toggle">
              {zh ? "看支持的目的地" : "See supported destinations"}
            </summary>
            <ul className="trial-supported-list">
              {(zh ? SUPPORTED_CITIES.zh : SUPPORTED_CITIES.en).map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
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
              <span>{zh ? "抵达时间" : "Arrival time"}</span>
              <input
                data-testid="trial-start"
                type="datetime-local"
                value={draft.startAt}
                onChange={(event) => update("startAt", event.target.value)}
              />
            </label>
            <label className="trial-field">
              <span>{zh ? "离开时间" : "Departure time"}</span>
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
            <summary>{zh ? "高级设置" : "Advanced settings"}</summary>
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
        </div>
      )}

      {step === 2 && (
        <div className="v8-card trial-card" data-testid="trial-step2-body">
          <div className="trial-row">
            <label className="trial-field">
              <span>{zh ? "旅行人数" : "Travellers"}</span>
              <input
                data-testid="trial-party"
                type="number"
                min="1"
                max="20"
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
              <span>{t("trial.rooms")}</span>
              <input
                data-testid="trial-rooms"
                type="number"
                min="1"
                max="20"
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
              <span>{zh ? "总预算" : "Total budget"}</span>
              <input
                data-testid="trial-budget"
                type="number"
                min="0"
                value={draft.budgetMajor}
                onChange={(event) => update("budgetMajor", Number(event.target.value))}
              />
            </label>
            <label className="trial-field">
              <span>{t("trial.stayBudget")}</span>
              <input
                data-testid="trial-stay-budget"
                type="number"
                min="0"
                value={draft.stayBudgetMajor}
                onChange={(event) => update("stayBudgetMajor", Number(event.target.value))}
              />
            </label>
          </div>

          <fieldset className="trial-fieldset">
            <legend>{zh ? "旅行节奏" : "Pace"}</legend>
            <div className="trial-chips">
              {PACE_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={draft.pace === option.key ? "active" : ""}
                  data-testid={`trial-pace-${option.key}`}
                  onClick={() => update("pace", option.key)}
                >
                  {zh ? option.zh : option.en}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="trial-fieldset">
            <legend>{zh ? "兴趣" : "Interests"}</legend>
            <div className="trial-chips">
              {INTEREST_OPTIONS.map((option) => {
                const selected = (draft.interests ?? []).includes(option.key);
                return (
                  <button
                    key={option.key}
                    type="button"
                    className={selected ? "active" : ""}
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
            <span>{zh ? "特殊要求" : "Special requirements"}</span>
            <textarea
              data-testid="trial-special"
              rows={3}
              value={draft.specialRequirements ?? ""}
              onChange={(event) => update("specialRequirements", event.target.value)}
              placeholder={
                zh
                  ? "例如：我妈妈坐轮椅；每天走路不超过 3000 米"
                  : "e.g. my mother uses a wheelchair; no more than 3 km walking a day"
              }
            />
          </label>
        </div>
      )}

      {step === 3 && (
        <div className="v8-card trial-card" data-testid="trial-step3-body">
          <dl className="trial-review">
            <div>
              <dt>{zh ? "目的地" : "Destination"}</dt>
              <dd data-testid="review-city">{draft.cityName || "—"}</dd>
              {/* The step-1 caution has to be here too: this is the screen the traveller
                  confirms from, and an assumption shown only two steps back is gone. */}
              {unrecognizedCity && (
                <dd className="trial-city-warning" data-testid="review-city-warning">
                  {zh
                    ? `未识别 · 按中立口径 ${basisWords.country} / ${basisWords.currency}（${basisWords.currencyCode}）/ ${basisWords.timezone} 规划，不沿用上一次识别到的城市`
                    : `not recognised · planned on the neutral basis ${basisWords.country} / ${basisWords.currency} (${basisWords.currencyCode}) / ${basisWords.timezone}, not the last recognised city`}
                </dd>
              )}
            </div>
            <div>
              <dt>{zh ? "抵达" : "Arrival"}</dt>
              {/* A bare "—" read as an acceptable blank, and the API rejects it. Say so here. */}
              <dd
                data-testid="review-arrival"
                data-missing={draft.arrivalLocation.trim() ? undefined : "true"}
              >
                {draft.arrivalLocation.trim() || (zh ? "未填写 · 必填" : "not filled in · required")}
                {" · "}
                {draft.startAt.replace("T", " ")}
              </dd>
            </div>
            <div>
              <dt>{zh ? "离开" : "Departure"}</dt>
              <dd
                data-testid="review-departure"
                data-missing={draft.departureLocation.trim() ? undefined : "true"}
              >
                {draft.departureLocation.trim() || (zh ? "未填写 · 必填" : "not filled in · required")}
                {" · "}
                {draft.endAt.replace("T", " ")}
              </dd>
            </div>
            <div>
              <dt>{zh ? "人数 / 房间" : "Travellers / rooms"}</dt>
              <dd data-testid="review-party">
                {draft.partySize} · {draft.rooms}
              </dd>
            </div>
            <div>
              <dt>{zh ? "总预算 / 住宿" : "Total / stay budget"}</dt>
              <dd data-testid="review-budget">
                {draft.currency} {draft.budgetMajor} / {draft.stayBudgetMajor}
              </dd>
            </div>
            <div>
              <dt>{zh ? "节奏" : "Pace"}</dt>
              <dd data-testid="review-pace">
                {optionLabels(draft.pace ? [draft.pace] : [], PACE_OPTIONS, zh) || "—"}
              </dd>
            </div>
            <div>
              <dt>{zh ? "兴趣" : "Interests"}</dt>
              <dd data-testid="review-interests">
                {optionLabels(draft.interests ?? [], INTEREST_OPTIONS, zh) || "—"}
              </dd>
            </div>
            <div>
              <dt>{zh ? "特殊要求" : "Special requirements"}</dt>
              <dd data-testid="review-special">{draft.specialRequirements || "—"}</dd>
            </div>
            <div>
              <dt>{zh ? "自动设置" : "Auto-set"}</dt>
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
              ? zh
                ? "这一步没有成功——行程已创建，但住宿搜索没有完成。"
                : "This step did not complete — the trip was created, but the stay search did not."
              : zh
                ? "这一步没有成功，行程还没有创建。"
                : "This step did not complete — no journey was created."}
          </strong>
          {message ? <span>{message}</span> : null}
        </div>
      )}
      {stoppedWaiting && !busy && message && (
        /* Giving up on the wait is not a failure and not a cancel: the request this screen
           stopped is described by what actually happened to it. */
        <div className="trial-wait-outcome" data-testid="trial-wait-outcome" role="status">
          <strong>{zh ? "已停止等待" : "Stopped waiting"}</strong>
          <span>{message}</span>
        </div>
      )}
      {blockedNow && (
        /* A greyed-out "Next" with no reason is the same silence as a create that dies
           quietly, so name what is missing.  Stable id: the blocked button describes itself
           with this element, so the relation cannot dangle between keystrokes. */
        <p className="trial-required-hint" id="trial-required-hint" data-testid="trial-required-hint" role="status">
          {/* ORD-0135 ③: naming a missing field is a diagnosis; the traveller also needs the route.
              Each item is a real control that puts the cursor in the field it names -- rendered inline
              rather than as its own row, because a row of buttons pushed this wizard's sticky CTA
              under the fixed simulation ball (measured by the mobile gate at 360x800: 33px). */}
          {missingNow.length
            ? zh
              ? "还需要填写："
              : "Still needed: "
            : ""}
          {missingNow.map((field, index) => (
            <span key={field.target}>
              {index > 0 ? (zh ? "、" : ", ") : ""}
              <button
                type="button"
                className="trial-missing-jump"
                data-testid="trial-missing-jump"
                data-target={field.target}
                onClick={() => {
                  /* From step 3 the target lives on an earlier step, where focusing it would do
                     nothing because the input is not mounted.  Move to the step that owns the field
                     first, then focus it once it exists. */
                  const owningStep = STEP_OF_TARGET[field.target] ?? step;
                  if (owningStep !== step) setStep(owningStep);
                  const focusTarget = () => {
                    const target =
                      document.getElementById(field.target) ??
                      document.querySelector<HTMLElement>(
                        `[data-testid="${field.target}"]`,
                      );
                    target?.focus();
                  };
                  if (owningStep === step) focusTarget();
                  else window.setTimeout(focusTarget, 80);
                }}
              >
                {field.label}
              </button>
              {/* ORD-0135 ③: the review step's rows already say 未填写 · 必填 for this field, and the
                  reason the blocked 确认创建 points at should be that same sentence rather than a
                  second phrasing of it. */}
              {step === 3 ? (zh ? " 未填写 · 必填" : " not filled in · required") : ""}
            </span>
          ))}
        </p>
      )}
      {/* Polite, and empty until a tap is refused: the visible hint above already carries the
          words for sighted travellers, so this region exists for the announcement alone. */}
      <p
        className="v8-sr-only"
        id="trial-next-reason"
        data-testid="trial-next-reason"
        role="status"
        aria-live="polite"
      >
        {spokenReason}
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
            {zh
              ? "第一次搜索一座城市实测要两分钟左右。服务器不会中途汇报进度，所以这里只有真实秒数，没有编出来的数字。"
              : "A cold city's first search measured about two minutes. The server reports nothing until it finishes, so this is measured seconds — not an invented number."}
          </p>
          {onStopWaiting && (
            <button
              type="button"
              className="v8-outline-button trial-wait-stop"
              data-testid="trial-stop-waiting"
              onClick={onStopWaiting}
            >
              {zh ? "停止等待" : "Stop waiting"}
            </button>
          )}
          <p className="trial-wait-hint">
            {zh
              ? "停止等待只是离开这块屏幕：服务器不会因此停下，行程数据也不会丢失。"
              : "Stopping the wait only closes this view: the server keeps going, and nothing you typed is lost."}
          </p>
        </div>
      )}
      {/* Sticky CTA: always reachable, never below a wall of scrolling. */}
      <div className="trial-sticky-cta" data-testid="trial-sticky-cta">
        {step > 1 && (
          <button
            type="button"
            className="v8-outline-button"
            data-testid="trial-back"
            disabled={busy}
            onClick={() => setStep((current) => (current === 3 ? 2 : 1))}
          >
            {zh ? "返回" : "Back"}
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
                speak(missingLine);
                return;
              }
              setStep((current) => (current === 1 ? 2 : 3));
            }}
          >
            {zh ? "下一步" : "Next"}
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
                speak(missingLine);
                return;
              }
              void submit();
            }}
          >
            {busy ? t("trial.creating") : zh ? "确认创建" : "Create trip"}
          </button>
        )}
      </div>

      {/* Secondary, de-emphasised: the sealed demo is not the golden path. */}
      <div className="trial-secondary">
        <button
          type="button"
          className="trial-back-link"
          data-testid="trial-tianjin-demo"
          disabled={busy}
          onClick={() => void onUseTianjinDemo()}
        >
          {t("trial.tianjinDemo")}
        </button>
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
            {zh ? "高级设置" : "Advanced settings"}
          </button>
        )}
      </div>
    </section>
  );
}
