import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { LocaleProvider, useLocale } from "./src/i18n/LocaleContext";

function Probe() {
  const { locale, t } = useLocale();
  const keys = ["mobility.note", "stay.kicker", "itinerary.dayByDay", "simulation.now",
                "simulation.closeStage", "detail.receiptLabelAbsent"];
  return createElement("pre", {
    dangerouslySetInnerHTML: {
      __html: JSON.stringify({ locale, got: keys.map((k) => [k, t(k)]) }),
    },
  });
}

globalThis.localStorage = {
  getItem: () => "zh-CN",
  setItem: () => {},
  removeItem: () => {},
};
const html = renderToStaticMarkup(
  createElement(LocaleProvider, null, createElement(Probe)),
);
console.log(
  html
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&"),
);
