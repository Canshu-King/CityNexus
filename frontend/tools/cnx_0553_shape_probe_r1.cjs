#!/usr/bin/env node
/* ORD-0553 shape probe: for each listed site, compare what the screen shows today against
 * what it would show if the inline formatting were replaced by the shared formatWhen helper.
 * The order forbids changing on-screen text, so a site whose shape differs cannot be
 * "converged" this round without either a new helper option or a ruling. */

// Mirror of frontend/src/lib/formatWhen.ts (INSTANT gate + Intl shape).
const INSTANT = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;
function formatWhen(at, opts) {
  const raw = (at ?? "").trim();
  if (!raw) return opts.pending;
  if (!INSTANT.test(raw)) return raw;
  const when = new Date(raw);
  if (Number.isNaN(when.getTime())) return raw;
  return new Intl.DateTimeFormat(opts.zh ? "zh-CN" : "en-GB", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(when);
}

const SAMPLES = {
  instant: "2026-10-09T18:30:00+08:00",
  instantZ: "2026-10-09T10:30:00Z",
  dateOnly: "2026-10-09",
};

const SITES = [
  { id: "V10LiveExecutionPanel.tsx:64", today: () => new Date(SAMPLES.instant).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), note: "clock cell, now = new Date(server clock)" },
  { id: "V12AuthoritativeJourneyPanel.tsx:118", today: () => new Date(SAMPLES.instant).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), note: "next-step <small>" },
  { id: "RealCityDiscoveryPanel.tsx:537", today: () => SAMPLES.instant.slice(0, 16).replace("T", " "), note: "batch row <span>" },
  { id: "V8Experience.tsx:3515", today: () => (SAMPLES.dateOnly ? ` · ${SAMPLES.dateOnly.slice(5)}` : ""), note: "day detail title, server YYYY-MM-DD" },
  { id: "AgentComposer.tsx:265", today: () => SAMPLES.instant, note: "semantic envelope effective_time, raw" },
  { id: "JourneyInboxWorkbench.tsx:976", today: () => SAMPLES.instant.replace("Z", "").slice(0, 16), note: "<input type=datetime-local> value" },
  { id: "JourneyInboxWorkbench.tsx:980", today: () => SAMPLES.instant.replace("Z", "").slice(0, 16), note: "<input type=datetime-local> value" },
];

let swappable = 0;
for (const site of SITES) {
  const before = { zh: site.today(), en: site.today() };
  const after = {
    zh: formatWhen(site.id.includes("V8Experience") ? SAMPLES.dateOnly : SAMPLES.instant, { zh: true, pending: "—" }),
    en: formatWhen(site.id.includes("V8Experience") ? SAMPLES.dateOnly : SAMPLES.instant, { zh: false, pending: "—" }),
  };
  const same = before.zh === after.zh && before.en === after.en;
  if (same) swappable++;
  console.log(`${same ? "SAME  " : "CHANGES"} ${site.id}`);
  console.log(`        today   zh=${JSON.stringify(before.zh)} en=${JSON.stringify(before.en)}`);
  console.log(`        helper  zh=${JSON.stringify(after.zh)} en=${JSON.stringify(after.en)}   [${site.note}]`);
}
console.log(`\nsites_listed=${SITES.length} swappable_without_changing_screen_text=${swappable}`);
