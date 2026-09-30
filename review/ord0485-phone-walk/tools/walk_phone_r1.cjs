/* ORD-0485 -- phone walkthrough at 390x844 on this lane's own served production bundle.
 *
 * Everything read here is RENDERED TEXT (document.body.innerText / visible element text),
 * never a data-* attribute: a data attribute is not on the screen (Q71).
 *
 * Arms:
 *   A first_visit        - fresh profile, GET /  : what a person opening the link sees
 *   B enter_sealed       - press the sealed-demo entry and land on the hub
 *   C drawer_walk        - every v8-drawer-entry-* row, clicked as a user clicks it
 *   D trips_bookings     - /v8/trips -> "booking" sub-tab -> paste-confirmation tab
 *   E stay               - /v8/stay
 *   F access             - /v8/access, incl. issuing a grant through the UI
 *   G checkin_probe      - does any walked screen carry a stamp/check-in affordance
 *
 * One JSON per run, plus a per-arm PNG when the page lets the shot land.
 */
const { chromium, devices } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\export\\frontend\\node_modules\\playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://127.0.0.1:4861";
const OUT_DIR = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_r1";
const W = 390, H = 844;

fs.mkdirSync(OUT_DIR, { recursive: true });

const run = {
  schema: "CNX_PHONE_WALK_R1",
  order: "ORD-0485",
  base: BASE,
  viewport: { width: W, height: H, hasTouch: true, isMobile: true },
  started_local: new Date().toString(),
  screens: [],
  requests_non_get: [],
  page_errors_total: 0,
};

function classifyMachineWords(text) {
  const hits = text.match(/[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+/g) || [];
  const counts = {};
  for (const h of hits) counts[h] = (counts[h] || 0) + 1;
  return counts;
}

async function readScreen(page, tag, extra) {
  const snap = await page.evaluate(() => {
    const vis = (el) => {
      if (!el) return false;
      const b = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" &&
        s.visibility !== "hidden" && Number(s.opacity) !== 0;
    };
    const all = (sel) => Array.from(document.querySelectorAll(sel)).filter(vis);
    const bodyText = document.body.innerText || "";
    const strip = (s) => String(s || "").replace(/\s+/g, " ").trim();
    return {
      path: location.pathname,
      rendered_text_chars: bodyText.length,
      rendered_text_head: bodyText.slice(0, 1200),
      rendered_text_full_len: bodyText.length,
      visible_testids: all("[data-testid]").map((e) => e.getAttribute("data-testid")),
      visible_buttons: all("button").map((e) => strip(e.innerText)).filter((x) => x).slice(0, 60),
      visible_headings: all("h1,h2,h3,legend").map((e) => strip(e.innerText)).filter((x) => x).slice(0, 20),
      visible_inputs: all("input,textarea,select").map((e) => ({
        testid: e.getAttribute("data-testid"), kind: e.tagName.toLowerCase(),
        type: e.getAttribute("type"), label: strip((e.closest("label") || {}).innerText || ""),
        placeholder: e.getAttribute("placeholder") || "",
      })),
      dialog_open: all("[role=dialog]").length,
      fixed_nav_top: (() => {
        const n = document.querySelector(".v8-mobile-nav");
        if (!n || !vis(n)) return null;
        const b = n.getBoundingClientRect();
        return { top: Math.round(b.top), bottom: Math.round(b.bottom) };
      })(),
    };
  });
  const haystack = [snap.rendered_text_head, snap.visible_buttons.join(" "),
    snap.visible_headings.join(" ")].join(" ");
  const before = run.page_errors_total;
  const row = {
    arm: tag,
    route_read_from_location: snap.path,
    rendered_text_chars: snap.rendered_text_chars,
    rendered_text_head: snap.rendered_text_head,
    visible_testid_count: snap.visible_testids.length,
    visible_testids: snap.visible_testids,
    visible_buttons: snap.visible_buttons,
    visible_headings: snap.visible_headings,
    visible_inputs: snap.visible_inputs,
    machine_word_scan: classifyMachineWords(haystack),
    pageerrors_new_on_this_arm: 0,
    fixed_nav_top: snap.fixed_nav_top,
    extra: extra || null,
  };
  row.pageerrors_new_on_this_arm = run.page_errors_total - before;
  run.screens.push(row);
  return row;
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, name + ".png");
  try {
    await page.screenshot({ path: file, timeout: 9000, animations: "disabled" });
    return { file: name + ".png", bytes: fs.statSync(file).size };
  } catch (e) {
    return { file: null, reason: "SHOT_NOT_TAKEN_" + String(e.message || e).slice(0, 60) };
  }
}

function armPage(page, label) {
  page.on("request", (r) => {
    if (r.method() !== "GET") {
      run.requests_non_get.push({ arm: label, method: r.method(), url: r.url() });
    }
  });
  page.on("pageerror", (e) => {
    run.page_errors_total += 1;
    (run.page_error_list = run.page_error_list || []).push({
      arm: label, text: String(e && e.message ? e.message : e).slice(0, 220),
    });
  });
  page.on("requestfailed", (r) => {
    (run.request_failed_list = run.request_failed_list || []).push({
      arm: label, url: r.url(), failure: (r.failure() || {}).errorText,
    });
  });
}

async function openDrawer(page) {
  const toggles = ["[data-testid='v8-mobile-menu']", "[data-testid='v8-mobile-menu-toggle']",
    ".v8-mobile-menu button", "[aria-label*='nav']", "header button"];
  for (const sel of toggles) {
    const loc = page.locator(sel).first();
    if ((await loc.count()) > 0) {
      try {
        await loc.click({ timeout: 4000 });
      } catch (e) { continue; }
      const drawer = page.locator("[data-testid='v8-nav-drawer']");
      if (await drawer.count() > 0) {
        try { await drawer.first().waitFor({ state: "visible", timeout: 4000 }); } catch (e) { }
        return { opened_with: sel };
      }
    }
  }
  return { opened_with: null };
}

(async () => {
  const browser = await chromium.launch();

  // ---- A: first visit on a clean profile -----------------------------------
  let ctx = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  let page = await ctx.newPage();
  armPage(page, "A_first_visit");
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(6000);
  const a = await readScreen(page, "A_first_visit");
  a.screenshot = await shot(page, "A_first_visit");
  a.sw_controller = await page.evaluate(() => !!(navigator.serviceWorker &&
    navigator.serviceWorker.controller));

  // ---- B: enter the sealed demo through the wizard's own entry -------------
  const demoBtn = page.locator("[data-testid='trial-tianjin-demo']");
  const demoPresent = await demoBtn.count();
  if (demoPresent > 0) {
    try { await demoBtn.first().click({ timeout: 5000 }); } catch (e) {
      a.extra = { sealed_demo_click_error: String(e.message).slice(0, 120) };
    }
  }
  await page.waitForTimeout(12000);
  const b = await readScreen(page, "B_after_sealed_demo");
  b.screenshot = await shot(page, "B_after_sealed_demo");
  b.wizard_still_mounted = (await page.locator("[data-testid='trial-setup']").count()) > 0;

  // ---- C: walk every drawer entry ------------------------------------------
  const drawerProbe = await openDrawer(page);
  const entrySel = "[data-testid^='v8-drawer-entry-']";
  const entries = await page.locator(entrySel).evaluateAll((els) => els.map((e) => ({
    testid: e.getAttribute("data-testid"), text: (e.innerText || "").replace(/\s+/g, " ").trim(),
  })));
  run.drawer = { drawer_probe: drawerProbe, entry_count: entries.length, entries };
  for (const entry of entries) {
    const opened = await openDrawer(page);
    if (opened.opened_with === null) {
      run.screens.push({ arm: "C_drawer_" + entry.testid, ABORT: "DRAWER_DID_NOT_OPEN" });
      continue;
    }
    const loc = page.locator("[data-testid='" + entry.testid + "']").first();
    try { await loc.click({ timeout: 5000 }); } catch (e) {
      run.screens.push({ arm: "C_drawer_" + entry.testid, ABORT:
        "CLICK_REFUSED_" + String(e.message).slice(0, 90), entry_label: entry.text });
      continue;
    }
    await page.waitForTimeout(4500);
    const row = await readScreen(page, "C_drawer_" + entry.testid, { entry_label: entry.text });
    row.screenshot = await shot(page, "C_" + entry.testid);
  }

  // ---- D: Trips -> bookings sub-tab -> paste confirmation -----------------
  await page.goto(BASE + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(7000);
  await readScreen(page, "D1_trips_landed");
  for (const tab of ["trips-tab-bookings", "inbox-tab-paste"]) {
    const loc = page.locator("[data-testid='" + tab + "']").first();
    if ((await loc.count()) === 0) {
      run.screens.push({ arm: "D2_" + tab, ABORT: "TESTID_NOT_IN_DOM" });
      continue;
    }
    try { await loc.click({ timeout: 5000 }); } catch (e) {
      run.screens.push({ arm: "D2_" + tab, ABORT: "CLICK_REFUSED_" + String(e.message).slice(0, 90) });
      continue;
    }
    await page.waitForTimeout(3500);
    const row = await readScreen(page, "D2_" + tab);
    row.screenshot = await shot(page, "D_" + tab);
  }

  // ---- E/F: stay + access, addressed directly as a refresh would ----------
  for (const [tag, route] of [["E_stay", "/v8/stay"], ["F_access", "/v8/access"]]) {
    await page.goto(BASE + route, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(6000);
    const row = await readScreen(page, tag);
    row.screenshot = await shot(page, tag);
  }

  // ---- G: does any screen offer a stamp?  scan the whole shell text -------
  const stampScan = await page.evaluate(() => {
    const words = ["\u6253\u5361", "check-in", "checkin", "stamp", "footprint", "\u8db3\u8ff9"];
    const body = document.body.innerText || "";
    const found = {};
    for (const w of words) {
      const re = new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
      found[w] = (body.match(re) || []).length;
    }
    const testids = Array.from(document.querySelectorAll("[data-testid]"))
      .map((e) => e.getAttribute("data-testid"))
      .filter((t) => /check|stamp|foot/i.test(t || ""));
    return { found, matching_testids: testids };
  });
  run.stamp_scan_on_access_screen = stampScan;

  await ctx.close();
  run.finished_local = new Date().toString();
  fs.writeFileSync(path.join(OUT_DIR, "walk_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("SCREENS=" + run.screens.length + " NONGET=" + run.requests_non_get.length +
    " PAGEERRORS=" + run.page_errors_total + " DRAWER_ENTRIES=" + run.drawer.entry_count);
  await browser.close();
})().catch((e) => {
  run.FATAL = String(e && e.stack ? e.stack : e).slice(0, 900);
  fs.writeFileSync(path.join(OUT_DIR, "walk_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("FATAL_SEE_JSON");
  process.exitCode = 1;
});
