import { createElement } from "react";
import { renderToString } from "react-dom/server";

export const KEYS: string[] = JSON.parse(process.env.PROBE_KEYS || "[]");
export const ARM: string = process.env.PROBE_ARM || "?";

function unescapeHtml(value: string): string {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'");
}

export function renderAll(dict: { LocaleProvider: unknown; useT: () => string }, locale: string): string[] {
  const store = new Map<string, string>([["citynexus.locale", locale]]);
  const globalAny = globalThis as unknown as { localStorage: unknown };
  globalAny.localStorage = {
    getItem: (key: string) => (store.has(key) ? store.get(key) : null),
    setItem: (key: string, value: string) => { store.set(key, value); },
  };

  function Probe() {
    const t = dict.useT();
    return createElement("ul", null, KEYS.map((key) => createElement("li", { key }, t(key))));
  }

  const html = renderToString(createElement(dict.LocaleProvider as never, null, createElement(Probe)));
  const texts: string[] = [];
  const matcher = /<li>([\s\S]*?)<\/li>/g;
  let found: RegExpExecArray | null;
  while ((found = matcher.exec(html)) !== null) texts.push(unescapeHtml(found[1]));
  return texts;
}

export function emit(dict: { LocaleProvider: unknown; useT: () => string }): void {
  for (const locale of ["zh-CN", "en"]) {
    const values = renderAll(dict, locale);
    KEYS.forEach((key, index) => {
      console.log(`${ARM} | ${locale} | ${key} | ${values[index]}`);
    });
  }
}
