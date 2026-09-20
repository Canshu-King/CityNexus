import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useT } from "../../i18n/LocaleContext";

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

export function JourneyTrialSetup({
  onCreate,
  onUseTianjinDemo,
  onCancel,
  busy,
  message,
}: {
  onCreate: (draft: JourneyTrialDraft) => Promise<void>;
  onUseTianjinDemo: () => Promise<void>;
  onCancel?: () => void;
  busy: boolean;
  /* The shell's createJourney catch writes the named backend error into its own state,
     but this screen returns before the shell renders it, so the reason never reached the
     user.  Optional on purpose: the call-site change belongs to another owner, and the
     wizard's own failure visibility below must not depend on it landing first. */
  message?: string | null;
}) {
  const t = useT();
  const { locale, switchLocale } = useLocale();
  const zh = locale.startsWith("zh");
  const browserTimezone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai",
    [],
  );
  const defaultDraft = useMemo<JourneyTrialDraft>(
    () => ({
      cityName: "",
      countryCode: "CN",
      timezone: browserTimezone,
      startAt: futureLocalAt(1, 10),
      endAt: futureLocalAt(3, 20),
      arrivalLocation: "",
      departureLocation: "",
      budgetMajor: 3000,
      stayBudgetMajor: 1000,
      currency: "CNY",
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
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [draft, setDraft] = useState<JourneyTrialDraft>(restored.draft as JourneyTrialDraft);
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
    setDraft((current) => ({
      ...current,
      cityName,
      ...(facts
        ? { countryCode: facts.country, timezone: facts.timezone, currency: facts.currency }
        : {}),
    }));
  };

  const facts = inferCityFacts(draft.cityName);
  /* The API requires a non-empty anchor location at both ends
     (`arrival_anchor.location` has minLength 1).  Until now the field looked optional -- a
     placeholder, and a bare "—" on the review page -- so a legal-looking 4-day trip died on
     a 422 the traveller could not see.  Pre-validating here is what ruling ① allows; the
     backend stays the authority. */
  const missingStep1 = [
    draft.cityName.trim() ? null : zh ? "目的地" : "the destination",
    draft.arrivalLocation.trim() ? null : zh ? "抵达地点" : "where you arrive",
    draft.departureLocation.trim() ? null : zh ? "离开地点" : "where you leave",
  ].filter(Boolean) as string[];
  const step1Ready = missingStep1.length === 0;
  const step2Ready = draft.partySize >= 1 && draft.budgetMajor > 0;

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
              placeholder={zh ? "例如：厦门" : "e.g. Xiamen"}
              autoFocus
            />
          </label>

          {facts && (
            <p className="trial-inferred" data-testid="trial-inferred">
              {zh ? "已自动设置：" : "Auto-set: "}
              {zh ? facts.labelZh : facts.labelEn} ·{" "}
              {currencyLabel(draft.currency, locale)} ·{" "}
              {timezoneLabel(draft.timezone, locale)}
            </p>
          )}

          <label className="trial-field">
            <span>{zh ? "抵达厦门" : "Arrive at"}</span>
            <input
              data-testid="trial-arrival"
              value={draft.arrivalLocation}
              onChange={(event) => update("arrivalLocation", event.target.value)}
              placeholder={zh ? "例如：厦门高崎国际机场" : "e.g. Xiamen Gaoqi Intl Airport"}
            />
          </label>
          <label className="trial-field">
            <span>{zh ? "离开厦门" : "Depart from"}</span>
            <input
              data-testid="trial-departure"
              value={draft.departureLocation}
              onChange={(event) => update("departureLocation", event.target.value)}
              placeholder={zh ? "例如：厦门北站" : "e.g. Xiamen North Station"}
            />
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
            </div>
            <div>
              <dt>{zh ? "抵达" : "Arrival"}</dt>
              <dd data-testid="review-arrival">
                {draft.arrivalLocation || "—"} · {draft.startAt.replace("T", " ")}
              </dd>
            </div>
            <div>
              <dt>{zh ? "离开" : "Departure"}</dt>
              <dd data-testid="review-departure">
                {draft.departureLocation || "—"} · {draft.endAt.replace("T", " ")}
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
              <dd data-testid="review-pace">{draft.pace || "—"}</dd>
            </div>
            <div>
              <dt>{zh ? "兴趣" : "Interests"}</dt>
              <dd data-testid="review-interests">
                {(draft.interests ?? []).join(", ") || "—"}
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

      {createAttemptFailed && (
        /* Directly above the confirm button, so the reason is where the tap was.
           Gated on createAttemptFailed rather than on `message` alone: the shell's message
           is shared state and could carry text from an unrelated earlier step. */
        <div className="trial-create-error" data-testid="trial-create-error" role="alert">
          <strong>
            {zh
              ? "这一步没有成功，行程还没有创建。"
              : "This step did not complete — no journey was created."}
          </strong>
          {message ? <span>{message}</span> : null}
        </div>
      )}
      {step === 1 && !step1Ready && (
        /* A greyed-out "Next" with no reason is the same silence as a create that dies
           quietly, so name what is missing. */
        <p className="trial-required-hint" data-testid="trial-required-hint" role="status">
          {zh
            ? `还需要填写：${missingStep1.join("、")}`
            : `Still needed: ${missingStep1.join(", ")}`}
        </p>
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
            disabled={(step === 1 && !step1Ready) || (step === 2 && !step2Ready)}
            onClick={() => setStep((current) => (current === 1 ? 2 : 3))}
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
            onClick={() => void submit()}
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
