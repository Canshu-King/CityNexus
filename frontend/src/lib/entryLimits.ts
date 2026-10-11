/**
 * ORD-0456: what the trip-setup entry asks for, declared once.
 *
 * Before this file the same two facts existed twice - 「旅行人数」 was spelled one way in the
 * missing-field sentence (`JourneyTrialSetup.tsx`) and another way in the field's own label
 * (`:1145`), and the accepted range was typed into the input as literal `min`/`max` attributes while
 * the server carried its own bound (`backend/app/schemas.py`). Two copies of one fact is how a
 * label ends up promising 1-20 while the control silently allows something else.
 *
 * So both the label and the control are produced from these entries. `required` here means the
 * review step blocks on it (`missingStep1/2/3`), which is the same predicate the API rejects with a
 * 422 - not a new claim invented at display time.
 *
 * ORD-0557 moved the two words this file used to invent for itself - the required/optional tag and
 * the way a lower bound with no upper bound is phrased - into the traveller dictionaries, under
 * `trial.fieldRequired`, `trial.fieldOptional` and `trial.rangeFrom`. The facts stay here; only the
 * wording is looked up, and it is looked up per language rather than chosen by a ternary in this
 * module.
 */

import { dictionaryText } from "../i18n/LocaleContext";

export const PARTY_SIZE_MIN = 1;
/** `party_size: int = Field(default=1, ge=1, le=20)` in `backend/app/schemas.py`. */
export const PARTY_SIZE_MAX = 20;
export const ROOMS_MIN = 1;
/** The same ceiling as party size: one room per traveller is the upper bound the form offers. */
export const ROOMS_MAX = 20;
/** The review step blocks on a budget of zero, so a 0 here would be a label promising what the form refuses. */
export const BUDGET_MINOR_MIN = 1;
/** An optional money field still accepts 0, because 0 there is the traveller saying "no lodging budget". */
export const OPTIONAL_MONEY_MIN = 0;

type EntryField = {
  zh: string;
  en: string;
  /** The unit words a traveller reads after the range, in their own language. */
  unitZh: string;
  unitEn: string;
  testId: string;
  min: number;
  max: number | null;
  required: boolean;
};

export const ENTRY_FIELDS = {
  party: {
    zh: "旅行人数",
    en: "Travellers",
    unitZh: "人",
    unitEn: "people",
    testId: "trial-party",
    min: PARTY_SIZE_MIN,
    max: PARTY_SIZE_MAX,
    required: true,
  },
  rooms: {
    zh: "房间数",
    en: "Rooms",
    unitZh: "间",
    unitEn: "rooms",
    testId: "trial-rooms",
    min: ROOMS_MIN,
    max: ROOMS_MAX,
    required: false,
  },
  budget: {
    zh: "总预算",
    en: "Total budget",
    unitZh: "元",
    unitEn: "CNY",
    testId: "trial-budget",
    min: BUDGET_MINOR_MIN,
    max: null,
    required: true,
  },
  stayBudget: {
    zh: "住宿预算",
    en: "Lodging budget",
    unitZh: "元",
    unitEn: "CNY",
    testId: "trial-stay-budget",
    min: OPTIONAL_MONEY_MIN,
    max: null,
    required: false,
  },
} as const satisfies Record<string, EntryField>;

export type EntryFieldKey = keyof typeof ENTRY_FIELDS;

function wantsChinese(zh?: boolean | string | null): boolean {
  if (typeof zh === "boolean") return zh;
  if (typeof zh === "string") return zh.trim().toLowerCase().startsWith("zh");
  return false;
}

/** The short name the blocked-tap sentence uses. Same entry, so it cannot disagree with the label. */
export function entryFieldName(key: EntryFieldKey, zh?: boolean | string | null): string {
  const field = ENTRY_FIELDS[key];
  return wantsChinese(zh) ? field.zh : field.en;
}

/** The range a control will take, spelled the way each language spells a unit after a number. */
export function entryFieldRange(key: EntryFieldKey, zh?: boolean | string | null): string {
  const field = ENTRY_FIELDS[key];
  /* Only the open-ended arm reads a key: it is the phrase this file made up for itself (ORD-0557).
     The bounded arm still spells `min-max` here, because it was not on that order's table and a key
     invented unsolicited would be a second copy of a wording nobody has decided yet. */
  if (wantsChinese(zh)) {
    return field.max === null
      ? dictionaryText("zh-CN", "trial.rangeFrom", { min: field.min, unit: field.unitZh })
      : `${field.min}-${field.max} ${field.unitZh}`;
  }
  return field.max === null
    ? dictionaryText("en", "trial.rangeFrom", { min: field.min, unit: field.unitEn })
    : `${field.min}-${field.max} ${field.unitEn}`;
}

/** The label the traveller reads above the input: name, whether it is required, and the bound. */
export function entryFieldLabel(key: EntryFieldKey, zh?: boolean | string | null): string {
  return `${entryFieldName(key, zh)}${entryFieldSuffix(key, zh)}`;
}

/**
 * The parenthesised tail on its own, for a field whose name already has one source elsewhere -
 * `trial.rooms` and `trial.stayBudget` are dictionary keys, so the words come from the dictionary and
 * only the fact this file owns (required? which bound?) is appended here.
 */
export function entryFieldSuffix(key: EntryFieldKey, zh?: boolean | string | null): string {
  const field = ENTRY_FIELDS[key];
  /* Which word, in which language, is the dictionaries' business (ORD-0557); which fact it names --
     that the review step blocks on this field -- stays the boolean above. */
  const required = dictionaryText(
    wantsChinese(zh) ? "zh-CN" : "en",
    field.required ? "trial.fieldRequired" : "trial.fieldOptional",
  );
  return `（${required} · ${entryFieldRange(key, zh)}）`;
}

/** The attributes the control actually enforces, from the same entry as the words above it. */
export function entryFieldBounds(key: EntryFieldKey): { min: number; max?: number } {
  const field = ENTRY_FIELDS[key];
  return field.max === null ? { min: field.min } : { min: field.min, max: field.max };
}
