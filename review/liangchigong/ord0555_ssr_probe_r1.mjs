import { createRequire } from "module";
import { writeFileSync } from "fs";
const require = createRequire("D:/moodle/_liangchigong_0555_wt/frontend/package.json");
const esbuild = require("esbuild");

const ENTRY = "D:/moodle/_liangchigong_0555_wt/frontend/__lc_probe/ssr_entry.tsx";
const OUT = "D:/moodle/_liangchigong_0555_wt/frontend/__lc_probe/ssr_bundle.cjs";

writeFileSync(ENTRY, `
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { LocaleProvider } from "../src/i18n/LocaleContext";
import { AgentComposer } from "../src/features/agent/AgentComposer";

const JOURNEY_ID = "lc-probe-journey";
const arm = (feasibility: string) => ({
  role: "assistant", text: "probe",
  response: {
    mode: "AI", reply: "probe",
    intent: { name: "WHAT_IF", confidence: 1, reasoning_summary: "", entities: {}, constraints: [] },
    action: null, event: null,
    what_if: {
      simulation_only: true, status: "SIMULATED", feasibility,
      before: { cost_minor: 120000, currency: "CNY" },
      after: { cost_minor: 90000, currency: "CNY" },
      deltas: {}, affected_activities: [],
      protected_commitments: { count: 2, preserved: true, ids: [] },
      proposed_changes: [], provenance: {}, explanation: "", next_action: null,
    },
  },
});
const HISTORY = JSON.stringify([arm("PASSED"), arm("FAILED"), arm("UNKNOWN"), arm("SOMETHING_ELSE")]);

(globalThis as any).window = {
  localStorage: { getItem: (k: string) => (k === \`citynexus.copilot.history.\${JOURNEY_ID}\` ? HISTORY : null), setItem: () => {}, removeItem: () => {} },
  navigator: { language: "en" },
};
(globalThis as any).document = { documentElement: { lang: "en" }, getElementById: () => null };

const data: any = { journey: { id: JOURNEY_ID, title: "Probe journey" }, traveler_twin: null };
const localeKey = process.argv[2] === "zh-CN" ? "zh-CN" : "en";
(globalThis as any).localStorage = (globalThis as any).window.localStorage;
(globalThis as any).window.localStorage.getItem = (k: string) =>
  k === "citynexus.locale" ? localeKey : k === \`citynexus.copilot.history.\${JOURNEY_ID}\` ? HISTORY : null;

const html = renderToStaticMarkup(
  createElement(LocaleProvider, null, createElement(AgentComposer, { data, busy: false, onNavigate: () => {} })),
);
const cells = Array.from(html.matchAll(/data-testid="v15-what-if"[\\s\\S]*?<\\/div><\\/div>/g)).map((m) => m[0]);
const labels = cells.map((c) => {
  const bs = Array.from(c.matchAll(/<b>([\\s\\S]*?)<\\/b>/g)).map((x) => x[1]);
  return bs[bs.length - 1] ?? "NONE";
});
console.log(JSON.stringify({ localeKey, cardCount: cells.length, feasibilityLabels: labels }));
`);

await esbuild.build({
  entryPoints: [ENTRY],
  bundle: true,
  platform: "node",
  format: "cjs",
  outfile: OUT,
  jsx: "automatic",
  loader: { ".css": "empty" },
  logLevel: "error",
});
console.log("bundled");
