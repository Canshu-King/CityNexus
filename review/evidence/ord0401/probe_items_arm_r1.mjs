/**
 * ORD-0401 -- the counter-arm: with a check actually open, does the panel still explain itself?
 *
 * Road ① drops the three-sentence note *only* when the derivation returns nothing. The risk in that
 * is a silent second change -- the scope sentence disappearing from the product -- so this arm answers
 * it with the note's own box: rendered, measured, and read off the screen, in both locales.
 *
 * Labeled honestly: the real sealed demo answers zero outstanding checks, so this arm feeds the panel
 * a locally injected `experience_flags.feasibility_failures` entry on top of the *real* payload this
 * device read from the preview chain. It is a shape check on a fixture, not a claim about the server.
 * The empty-state arms (probe_0401_r1) are the ones that read the untouched screen.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4301";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });

const READ = () => {
  const q = (s) => document.querySelector(s);
  const box = (el) =>
    el
      ? {
          y: Math.round(el.getBoundingClientRect().top + window.scrollY),
          h: Math.round(el.getBoundingClientRect().height),
          text: (el.innerText || "").replace(/\s+/g, " ").trim(),
          text_chars: (el.innerText || "").replace(/\s+/g, " ").trim().length,
          display: getComputedStyle(el).display,
        }
      : null;
  const panel = q('[data-testid="pretrip-checklist"]');
  const band = q('[data-testid="today-attention-band"]');
  const items = [...document.querySelectorAll('[data-testid="pretrip-item"]')];
  return {
    panel: box(panel),
    panel_data_count: panel?.getAttribute("data-count"),
    note: box(q(".cn-pretrip-note")),
    head_h2: box(q(".cn-pretrip h2")),
    empty_row: box(q('[data-testid="pretrip-empty"]')),
    items: items.map((li) => ({
      key: li.getAttribute("data-cnx-key"),
      title: box(li.querySelector(".cn-pretrip-title"))?.text,
      basis: box(li.querySelector(".cn-pretrip-basis"))?.text,
      anchor: box(li.querySelector(".cn-pretrip-anchor"))?.text,
      goto: box(li.querySelector("button"))?.text,
    })),
    dom_order: {
      band: band ? [...band.parentElement.children].indexOf(band) : null,
      panel: panel ? [...panel.parentElement.children].indexOf(panel) : null,
    },
    band_state: band?.getAttribute("data-attention"),
    doc_height: document.scrollingElement.scrollHeight,
  };
};

const browser = await chromium.launch();
const report = { base: BASE, fixture: "experience payload + one injected feasibility_failure string", arms: [] };

for (const locale of ["zh-CN", "en"]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
  await page.route((url) => url.pathname.startsWith("/api/"), (r) =>
    r.request().method() === "GET" ? r.continue() : r.fulfill({ status: 405, body: "{}" }),
  );
  await page.goto(`${BASE}/v8`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  const demo = page.getByTestId("trial-tianjin-demo");
  if (await demo.count()) {
    await demo.click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 }).catch(() => {});
  }
  const journeyId = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id"));

  // The real payload, read by this device, then one field added -- nothing else touched.
  const real = await (await fetch(`${BASE}/api/v1/journeys/${journeyId}/experience`)).json();
  const flags = { ...(real.experience_flags ?? {}) };
  flags.feasibility_failures = [...(flags.feasibility_failures ?? []), "STALE_RECOMPOSE_REQUIRED"];
  const fixture = { ...real, experience_flags: flags };
  const fields_added = ["experience_flags.feasibility_failures"];

  await page.route(
    (url) => url.pathname.endsWith("/experience"),
    (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture) }),
  );
  await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  await page.waitForTimeout(2500);
  const reading = await page.evaluate(READ);
  await page.screenshot({ path: `${OUT}/items-open-${locale}-390px.png` });
  report.arms.push({ locale, journey_id: journeyId, fields_added, real_item_count: real.experience_flags?.feasibility_failures?.length ?? 0, fixture_item_count: flags.feasibility_failures.length, reading });
  console.log(
    `\n=== items-open fixture, ${locale} @ 390x844 ===\n` +
      `  data_count=${reading.panel_data_count} items=${reading.items.length} panel_h=${reading.panel.h} doc=${reading.doc_height}\n` +
      `  note_h=${reading.note?.h} note_chars=${reading.note?.text_chars}\n` +
      `  note_text=${reading.note?.text?.slice(0, 70)}\n` +
      `  item=${JSON.stringify(reading.items[0])?.slice(0, 260)}\n` +
      `  dom_order=${JSON.stringify(reading.dom_order)} band_state=${reading.band_state} empty_row=${reading.empty_row ? "RENDERED(bug)" : "absent"}`,
  );
  await ctx.close();
}
await browser.close();
writeFileSync(`${OUT}/items_open_counterarm_r1.json`, JSON.stringify(report, null, 2));
