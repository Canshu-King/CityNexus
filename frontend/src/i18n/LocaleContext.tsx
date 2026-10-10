import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { expandPluralMarkers } from "../lib/plural";
import { domainBooks } from "./locales";


export type TripLocale = "en" | "zh-CN";

type Dict = Record<string, string>;

// ORD-0572: both books are assembled from ./locales/*.ts, merged in lexicographic domain-file
// order. Every key and every value below was moved byte for byte; nothing was retyped, renamed
// or reworded, and the exported names, types, useT and dictionaryCopy are unchanged.
const en: Dict = {};
const zhCN: Dict = {};
for (const book of domainBooks) {
  Object.assign(en, book.en);
  Object.assign(zhCN, book.zh);
}

const dictionaries: Record<TripLocale, Dict> = { en, "zh-CN": zhCN };

/* ORD-0557: the lookup for copy that lives in a module function rather than a component.
   `lib/failureAttribution.ts` builds its titles inside `copyFor(attribution, zh)`, whose call sites sit
   on ten other screens (first one `app/V8Experience.tsx:1595`), so that function cannot call the
   `useT()` hook without a signature change reaching into other lanes' files. Same fallback order as
   `t()`: this locale, then English, then the key itself. No `{param}` substitution and no `{plural:}`
   expansion -- a line needing either still goes through `t()`. */
export function dictionaryCopy(locale: TripLocale, key: string): string {
  return dictionaries[locale][key] ?? dictionaries.en[key] ?? key;
}

/**
 * ORD-0557: the same lookup for a caller that also has values to drop into the sentence.
 *
 * `lib/entryLimits.ts`, `lib/errorReceipt.ts` and `lib/pretripChecklist.ts` are plain functions handed
 * their language by the caller, so they cannot call a hook; and `trial.rangeFrom` carries `{min}` and
 * `{unit}` holes, which `dictionaryCopy` deliberately does not fill. The fallback order is not written
 * twice -- this sits on top of `dictionaryCopy` and adds only the plural marker and the substitution
 * that `t()` itself applies.
 *
 * `t()` is left alone on purpose: its body is pinned by a shipped gate
 * (`e2e/qoder-a68b0631-label-anchors-not-line-numbers-r1.spec.ts`, arm A5), which greps the two
 * dictionary arms out of that callback itself, so folding the three together reddens another lane's
 * gate. Whoever can move that gate should move all three bodies in one step.
 */
export function dictionaryText(
  locale: TripLocale,
  key: string,
  params?: Record<string, string | number>,
): string {
  const counted = expandPluralMarkers(dictionaryCopy(locale, key), params);
  if (!params) return counted;
  return counted.replace(/\{(\w+)\}/g, (_, k: string) => String(params[k] ?? `{${k}}`));
}

type LocaleState = {
  locale: TripLocale;
  setLocale: (l: TripLocale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  switchLocale: () => void;
};

const LocaleContext = createContext<LocaleState | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<TripLocale>(() => {
    const stored = localStorage.getItem("citynexus.locale");
    if (stored === "zh-CN" || stored === "en") return stored;
    // No explicit choice yet: follow the traveller's browser language so a
    // Chinese device does not open in English.
    const preferred = typeof navigator !== "undefined" ? navigator.language || "" : "";
    return preferred.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
  });

  const setLocale = useCallback((next: TripLocale) => {
    localStorage.setItem("citynexus.locale", next);
    document.documentElement.lang = next;
    setLocaleState(next);
  }, []);

  const switchLocale = useCallback(() => {
    setLocale(locale === "en" ? "zh-CN" : "en");
  }, [locale, setLocale]);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      let value = dictionaries[locale][key];
      if (!value) {
        value = dictionaries.en[key] ?? key;
      }
      const counted = expandPluralMarkers(value, params);
      if (!params) return counted;
      return counted.replace(/\{(\w+)\}/g, (_, k: string) =>
        String(params[k] ?? `{${k}}`),
      );
    },
    [locale],
  );

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t, switchLocale }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}

export function useT() {
  return useLocale().t;
}
