/**
 * ORD-0263 fifth state: read the screen the way HARNESS's ruler reads it -- expanded.
 *
 * His `judge_v5` parses `key=value` attribution fields out of the *rendered* text, and those fields live inside
 * `<details data-testid="failure-attribution"><summary>归因详情</summary><code …>{telemetry}</code></details>`,
 * which is collapsed by default. So this reader expands it by clicking the summary (not by setting `open`,
 * which would not be what a traveller does), then reports:
 *   - the whole rendered text of the failure region (what the ruler parses),
 *   - the browser's own Resource Timing for the journey read and the health read (status + duration),
 *   - the IndexedDB row count (the column his sixth condition compares against),
 *   - the visible recovery controls by their rendered labels.
 * Nothing is inferred: a field that could not be measured stays null.
 *
 * usage: node q263_s5_expand_read.js --url U --profile DIR --out FILE [--mode html]
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);

function arg(n, d) {
  const i = process.argv.indexOf("--" + n);
  return i === -1 ? d : process.argv[i + 1];
}

(async () => {
  const url = arg("url"), profile = arg("profile"), out = arg("out"), mode = arg("mode", "html");
  const ctx = await chromium.launchPersistentContext(profile, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const nav0 = Date.now();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 }).catch((e) => e.message);

  // wait for a classified state: the failure view (or the live shell), never a bare skeleton
  let settledAt = null, saw = {};
  for (let i = 0; i < 60; i += 1) {
    saw = {
      "failure-view": await page.locator('[data-testid="failure-view"]').count(),
      "today-heading": await page.locator('[data-testid="today-heading"]').count(),
      "trial-setup": await page.locator('[data-testid="trial-setup"]').count(),
    };
    if (Object.values(saw).some((v) => v > 0)) { settledAt = Date.now() - nav0; break; }
    await page.waitForTimeout(250);
  }

  const expand = { present: 0, clicked: false, line_before: null, line_after: null };
  const det = page.locator('details[data-testid="failure-attribution"]');
  expand.present = await det.count();
  const code = page.locator('[data-testid="failure-attribution-line"]');
  if (expand.present) {
    expand.line_before = (await code.count()) ? await code.first().innerText({ timeout: 1200 }).catch(() => "") : "";
    await det.locator("summary").first().click({ timeout: 3000 }).catch((e) => { expand.click_error = String(e).slice(0, 90); });
    await page.waitForTimeout(500);
    expand.open_after = await page.evaluate(() => {
      const el = document.querySelector('details[data-testid="failure-attribution"]');
      return el ? el.open : null;
    });
    expand.clicked = true;
    expand.line_after = (await code.count()) ? await code.first().innerText({ timeout: 1200 }).catch(() => "") : "";
  }

  const regionText = await (async () => {
    const f = page.locator('[data-testid="failure-view"]');
    if (await f.count()) return await f.first().innerText({ timeout: 1500 }).catch(() => "");
    const m = page.locator("main");
    return (await m.count()) ? await m.first().innerText({ timeout: 1500 }).catch(() => "") : "";
  })();
  const bodyText = await page.locator("body").innerText({ timeout: 1500 }).catch(() => "");

  const timing = await page.evaluate(() => {
    const rows = performance.getEntriesByType("resource").filter((r) => r.name.includes("/api/"))
      .map((r) => ({ url: r.name.replace(/^https?:\/\/[^/]+/, ""), duration_ms: Math.round(r.duration),
                     status: r.responseStatus, kind: r.initiatorType }));
    return { all: rows.slice(-12),
             journey: rows.filter((r) => r.url.includes("/experience")).slice(-1)[0] || null,
             health: rows.filter((r) => r.url.includes("/health")).slice(-1)[0] || null };
  });

  const snap = await page.evaluate(async () => {
    try {
      const dbs = await indexedDB.databases();
      if (!dbs.some((d) => d.name === "citynexus-offline")) return { rows: null, reason: "db absent" };
      return await new Promise((res) => {
        const rq = indexedDB.open("citynexus-offline");
        rq.onsuccess = () => {
          const db = rq.result;
          if (!Array.from(db.objectStoreNames).includes("journeys")) { res({ rows: null, reason: "store absent" }); db.close(); return; }
          const c = db.transaction("journeys", "readonly").objectStore("journeys").count();
          c.onsuccess = () => { res({ rows: c.result }); db.close(); };
          c.onerror = () => res({ rows: null, reason: "count threw" });
        };
        rq.onerror = () => res({ rows: null, reason: "open threw" });
      });
    } catch (e) { return { rows: null, reason: String(e && e.message) }; }
  });

  const buttons = [];
  for (const sel of ["failure-read-cached", "failure-retry"]) {
    const l = page.locator(`[data-testid="${sel}"]`);
    const n = await l.count();
    buttons.push({ testid: sel, count: n, label: n ? await l.first().innerText({ timeout: 1000 }).catch(() => "") : null });
  }

  const result = {
    mode, at: new Date().toISOString(), url, settled_after_ms: settledAt, state_nodes: saw,
    rendered_text: regionText, body_text_head: bodyText.replace(/\s+/g, " ").trim().slice(0, 300),
    attribution_expand: expand, resource_timing: timing, snapshot: snap,
    buttons: buttons.map((b) => b.label).filter(Boolean),
    in_memory_attribution_last: await page.evaluate(() => {
      const r = Array.isArray(window.citynexusAttribution) ? window.citynexusAttribution : null;
      return r && r.length ? r[r.length - 1] : null;
    }),
    service_worker: await page.evaluate(() => Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)),
  };
  fs.writeFileSync(out, JSON.stringify(result, null, 1), "utf8");
  console.log(`${mode}: nodes=${JSON.stringify(saw)} expanded=${expand.clicked} line_after_len=${(expand.line_after || "").length} `
    + `timing=${JSON.stringify(timing.journey)} rows=${JSON.stringify(snap.rows)} buttons=${JSON.stringify(result.buttons)} -> ${path.basename(out)}`);
  await ctx.close();
})().catch((e) => { console.error("EXPAND READER THREW: " + (e && e.stack || e)); process.exit(9); });
