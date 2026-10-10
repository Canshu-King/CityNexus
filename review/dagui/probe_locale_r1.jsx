import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  LocaleProvider,
  useLocale,
} from "../../frontend/src/i18n/LocaleContext";

const CASES = [
  ["simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot", { n: 3 }],
  [
    "simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan",
    { listed: 5, open: 2, id: "abcd1234" },
  ],
  [
    "simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine",
    { listed: 5 },
  ],
  ["simulation.now", { state: "OUTAGE" }],
  ["simulation.thisActionIsUnavailableRightNow", { reason: "REASON_TOKEN" }],
  ["simulation.thePreviousActionHasNotReturnedYet", undefined],
];

// what the same line read on screen before the move, with the same concrete values
const EXPECTED = {
  "simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot": {
    zh: '（另有 3 次没读到，那不是"没有时段"）',
    en: ' (3 reads did not answer, which is not the same as "no slot")',
  },
  "simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan":
    {
      zh: "服务器回了 5 份方案，其中 2 份还开着；下面「接受方案」那一行现在拿的是 abcd1234。接受才会换计划。",
      en: 'The server answered with 5 proposals, 2 still open; "Accept the proposal" below now points at abcd1234. Accepting is what changes the plan.',
    },
  "simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine":
    {
      zh: "服务器回了方案，但它现在列出的 5 份里没有还开着的那一份，所以「接受方案」这一行会说不给按——理由在它自己那行。",
      en: 'The server produced proposals, but none of the 5 it now lists is open, so "Accept the proposal" will refuse and say why on its own line.',
    },
  "simulation.now": { zh: "（现值 OUTAGE）", en: " (now OUTAGE)" },
  "simulation.thisActionIsUnavailableRightNow": {
    zh: "这个动作现在做不了：REASON_TOKEN",
    en: "This action is unavailable right now: REASON_TOKEN",
  },
  "simulation.thePreviousActionHasNotReturnedYet": {
    zh: "上一个动作还没回来，先等它。",
    en: "The previous action has not returned yet.",
  },
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
    if (!same) {
      console.log(
        "     expected=%s",
        JSON.stringify(want),
      );
    }
  }
}
console.log("probe_fail=%d", fail);
process.exit(fail ? 7 : 0);
