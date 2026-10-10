import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  LocaleProvider,
  useLocale,
} from "../../frontend/src/i18n/LocaleContext";

const CASES = [
  ["simulation.closeStage", undefined],
  ["simulation.onStage", undefined],
  ["simulation.sceneWindow", undefined],
];

// what those three lines read on the screen before the move
const EXPECTED = {
  "simulation.closeStage": { zh: "收起舞台", en: "Close the stage" },
  "simulation.onStage": { zh: "台上行程", en: "On stage" },
  "simulation.sceneWindow": { zh: "场景窗口", en: "Scene window" },
};

function Probe() {
  const { locale, t } = useLocale();
  const rows = CASES.map(([key, params]) => ({ key, out: t(key, params) }));
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
    console.log(
      "%s locale=%s key=%s value=%s",
      same ? "OK  " : "FAIL",
      r.locale,
      row.key,
      JSON.stringify(row.out),
    );
    if (!same) console.log("     expected=%s", JSON.stringify(want));
  }
}
console.log("probe_fail=%d", fail);
process.exit(fail ? 7 : 0);
