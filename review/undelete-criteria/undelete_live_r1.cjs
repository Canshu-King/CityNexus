/**
 * Lane 6a150e1e, building three -- the live reading that the criteria will be written against.
 *
 * The building asks whether a traveller can bring a deleted trip back and can tell whether it
 * worked, from the interface rather than the docs. So this reads the real screen: it finds a
 * traveller's own deleted trip, opens the bin, presses the actual 找回 control, and records what
 * the screen says afterwards. It also records the states that must be honest rather than empty --
 * the no-viewer case, the empty case, and the door-absent case -- because "give an empty list and
 * let it look like nothing was deleted" is the failure the building names explicitly.
 *
 * Nothing here asserts. It records, with a receipt per state, so the criteria written next can
 * each name a case that this file already knows how to produce. Read-only against the product:
 * it presses the screen's own button the way a traveller would, and it does not touch the tree.
 */
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4833";
const WIDTH = Number(process.argv[3] || 390);
const RUNG = "r1";
const OUT = "D:/moodle/_qoder_6a_ord0531_20261001/undelete_live_" + WIDTH + "_" + RUNG + ".json";
const TIP = "ff7f62011821240835572bf4effe2e139ee2bada";
const JOURNEY = "b25faac4-d3a8-4671-a39e-e82b3d2d3d2f";

const READ_PANEL = () => {
  const q = (s) => document.querySelector(s);
  const txt = (s) => { const e = q(s); return e ? (e.textContent || "").trim().slice(0, 160) : null; };
  const panel = q('[data-testid="journey-trash-panel"]');
  return {
    panel_present: Boolean(panel),
    panel_aria: panel ? panel.getAttribute("aria-label") : null,
    kicker: txt(".v8-kicker"),
    data_count: panel ? panel.getAttribute("data-count") : null,
    state: {
      no_viewer: txt('[data-testid="trash-no-viewer"]'),
      loading: txt('[data-testid="trash-loading"]'),
      read_failed: txt('[data-testid="trash-read-failed"]'),
      empty: txt('[data-testid="trash-empty"]'),
      count: txt('[data-testid="trash-count"]'),
    },
    rows: [...document.querySelectorAll('[data-testid^="trash-row"], .cn-trash-row')].map((r) => ({
      text: (r.textContent || "").trim().slice(0, 90),
      has_action: Boolean(r.querySelector(".cn-trash-action")),
      action_label: (r.querySelector(".cn-trash-action") || {}).textContent || null,
      says_refusal: (r.textContent || "").trim().slice(0, 120),
    })),
    action_buttons: [...document.querySelectorAll(".cn-trash-action")].map((b) => ({
      label: (b.textContent || "").trim(), testid: b.getAttribute("data-testid"),
      disabled: b.disabled, box: (() => { const r = b.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }; })(),
    })),
    outcome: (() => {
      const cands = ["[data-testid='trash-outcome']", "[role='status']", "[role='alert']", ".cn-trash-outcome"];
      for (const s of cands) { const e = q(s); if (e && (e.textContent || "").trim()) return { sel: s, text: (e.textContent || "").trim().slice(0, 200) }; }
      return null;
    })(),
  };
};

(async () => {
  const browser = await chromium.launch();
  const report = { base: BASE, tip: TIP, width: WIDTH, steps: [], api: {} };
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: 844 }, locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.addInitScript((j) => localStorage.setItem("citynexus.v8.journey_id", j), JOURNEY);

  // Step 1: what does the server actually hold for this traveller?
  // Navigate BEFORE reading: fetch() needs a real origin, and on about:blank every call throws
  // "Failed to fetch" -- which is the arm's bug, not the product's.
  await page.goto(BASE + "/v8/trash", { waitUntil: "load" }).catch(() => {});
  await page.waitForTimeout(1800);
  const apiRead = await page.evaluate(async (base) => {
    const g = async (p) => { const r = await fetch(base + p); let b = null; try { b = await r.json(); } catch (e) {}
      return { path: p, status: r.status, keys: b && typeof b === "object" ? Object.keys(b).slice(0, 12) : null,
               n: Array.isArray(b) ? b.length : null,
               first: Array.isArray(b) && b[0] ? { id: b[0].id, title: b[0].title, bin_state: b[0].bin_state } : null }; };
    return { bin: await g("/api/v1/recycle-bin/journeys"), collections: await g("/api/v1/collections"),
             journeys: await g("/api/v1/journeys") };
  }, BASE).catch((e) => ({ error: String(e).slice(0, 160) }));
  report.api = apiRead;
  report.steps.push({ step: "api_read", got: apiRead });

  // Step 2: the bin screen as a traveller finds it
  await page.goto(BASE + "/v8/trash", { waitUntil: "load" }).catch(() => {});
  await page.waitForTimeout(2600);
  const before = await page.evaluate(READ_PANEL);
  report.steps.push({ step: "trash_screen_before", got: before });

  // Step 3: press the real 找回 control on the first row that offers one
  const pressed = await page.evaluate(() => {
    const b = document.querySelector(".cn-trash-action");
    if (!b) return { pressed: false, why: "no .cn-trash-action on screen" };
    b.click();
    return { pressed: true, label: (b.textContent || "").trim() };
  });
  await page.waitForTimeout(2600);
  const after = await page.evaluate(READ_PANEL);
  report.steps.push({ step: "press_action", pressed, got_after: after });

  // Step 4: the empty / honest-notice states, named by what the panel exposes
  report.steps.push({ step: "honest_states_present", got: {
    has_no_viewer_slot: Boolean(before.state.no_viewer !== undefined),
    no_viewer_text: before.state.no_viewer,
    empty_text: before.state.empty,
    read_failed_text: before.state.read_failed,
    count_text: before.state.count,
    data_count_attr: before.data_count,
  }});

  await ctx.close();
  await browser.close();
  if (!OUT.endsWith(RUNG + ".json")) { console.log("REFUSE_OVERWRITE: name must end with " + RUNG); process.exit(7); }
  else if (fs.existsSync(OUT)) { console.log("REFUSE_OVERWRITE: receipt on disk " + OUT); process.exit(7); }
  else { fs.writeFileSync(OUT, JSON.stringify(report, null, 1), "utf8"); }
  console.log(JSON.stringify({ api: report.api, before_state: before.state, rows: before.rows.length,
    actions: before.action_buttons.length, pressed, after_outcome: after.outcome }, null, 1));
})();
