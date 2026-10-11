import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  LocaleProvider,
  useLocale,
} from "../../frontend/src/i18n/LocaleContext";

const CASES = [
  ["simulation.basis", undefined],
  ["simulation.evidence", undefined],
];

const EXPECTED = {
  "simulation.basis": { zh: "依据", en: "Basis" },
  "simulation.evidence": { zh: "证据", en: "Evidence" },
};

function Probe() {
  const { locale, t } = useLocale();
  const rows = CASES.map(([key]) => ({ key, out: t(key) }));
  return createElement("div", {
    dangerouslySetInnerHTML: { __html: JSON.stringify({ locale, rows }) },
  });
}

function unesc(s) {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function read(lang) {
  globalThis.localStorage = {
    getItem: () => lang,
    setItem: () => {},
    removeItem: () => {},
  };
  const html = renderToStaticMarkup(
    createElement(LocaleProvider, null, createElement(Probe)),
  );
  const start = html.indexOf(">") + 1;
  const end = html.lastIndexOf("<");
  return JSON.parse(unesc(html.slice(start, end)));
}

let fail = 0;
for (const lang of ["en", "zh-CN"]) {
  const r = read(lang);
  const side = lang === "zh-CN" ? "zh" : "en";
  for (const row of r.rows) {
    const want = EXPECTED[row.key][side];
    const same = want === row.out;
    if (!same) fail += 1;
    console.log("%s locale=%s key=%s value=%s", same ? "OK  " : "FAIL", r.locale, row.key, JSON.stringify(row.out));
  }
}
console.log("probe_fail=%d cases=%d", fail, CASES.length * 2);
process.exit(fail ? 7 : 0);
