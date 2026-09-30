/* ORD-0485 -- phone walkthrough r2 at 390x844 on this lane's served production bundle.
 *
 * r1's drawer loop aborted on every row: the helper clicked the menu button while the
 * backdrop still covered it, Playwright refused the covered click, and my catch moved on to
 * the next selector instead of noticing the drawer was already open.  r2 checks for an open
 * drawer FIRST, and only then taps the menu.
 *
 * Everything read is RENDERED TEXT. The machine-word scan runs over the whole rendered body
 * text, not a head slice.  A stamp/check-in scan is taken per screen, because that door
 * landed on the line with no UI attached to it.
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\export\\frontend\\node_modules\\playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://127.0.0.1:4861";
const OUT_DIR = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_r2";
const W = 390, H = 844;
fs.mkdirSync(OUT_DIR, { recursive: true });

const run = {
  schema: "CNX_PHONE_WALK_R2", order: "ORD-0485", base: BASE,
  viewport: { width: W, height: H, hasTouch: true, isMobile: true },
  started_local: new Date().toString(),
  screens: [], requests_non_get: [], page_errors_total: 0,
};

const STAMP_WORDS = ["打卡", "check-in", "checkin", "stamp", "footprint", "足迹"];

async function readScreen(page, tag, extra) {
  const snap = await page.evaluate((stampWords) => {
    const vis = (el) => {
      if (!el) return false;
      const b = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" &&
        s.visibility !== "hidden" && Number(s.opacity) !== 0;
    };
    const all = (sel) => Array.from(document.querySelectorAll(sel)).filter(vis);
    const strip = (s) => String(s || "").replace(/\s+/g, " ").trim();
    const bodyText = document.body.innerText || "";
    const counts = {};
    for (const w of stampWords) {
      const re = new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
      counts[w] = (bodyText.match(re) || []).length;
    }
    const nav = document.querySelector(".v8-mobile-nav");
    const navRect = nav && vis(nav) ? nav.getBoundingClientRect() : null;
    return {
      path: location.pathname,
      rendered_text_chars: bodyText.length,
      rendered_text_head: bodyText.slice(0, 1500),
      visible_testids: all("[data-testid]").map((e) => e.getAttribute("data-testid")),
      visible_buttons: all("button,a,summary").map((e) => strip(e.innerText)).filter((x) => x).slice(0, 80),
      visible_headings: all("h1,h2,h3,legend").map((e) => strip(e.innerText)).filter((x) => x).slice(0, 24),
      visible_inputs: all("input,textarea,select").map((e) => ({
        testid: e.getAttribute("data-testid"), kind: e.tagName.toLowerCase(),
        type: e.getAttribute("type"),
        label: strip((e.closest("label") || {}).innerText || ""),
        placeholder: e.getAttribute("placeholder") || "",
      })),
      stamp_word_counts: counts,
      stamp_matching_testids: all("[data-testid]").map((e) => e.getAttribute("data-testid"))
        .filter((t) => /check|stamp|foot|punch/i.test(t || "")),
      machine_words_full_text: (() => {
        const hits = bodyText.match(/[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+/g) || [];
        const c = {};
        for (const h of hits) c[h] = (c[h] || 0) + 1;
        return c;
      })(),
      bottom_nav_band: navRect ? { top: Math.round(navRect.top), bottom: Math.round(navRect.bottom) } : null,
      drawer_open: vis(document.querySelector("[data-testid='v8-nav-drawer']")),
      inert_overlay: all("[role=dialog]").length,
    };
  }, STAMP_WORDS);
  const row = Object.assign({
    arm: tag,
    route_read_from_location: snap.path,
    rendered_text_chars: snap.rendered_text_chars,
    rendered_text_head: snap.rendered_text_head,
    visible_testid_count: snap.visible_testids.length,
    visible_testids: snap.visible_testids,
    visible_buttons: snap.visible_buttons,
    visible_headings: snap.visible_headings,
    visible_inputs: snap.visible_inputs,
    machine_word_scan: snap.machine_words_full_text,
    stamp_word_counts: snap.stamp_word_counts,
    stamp_matching_testids: snap.stamp_matching_testids,
    bottom_nav_band: snap.bottom_nav_band,
    drawer_open_after_read: snap.drawer_open,
    dialog_count: snap.inert_overlay,
    pageerrors_total_at_read: run.page_errors_total,
    extra: extra || null,
  }, {});
  run.screens.push(row);
  return row;
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, name.replace(/[^A-Za-z0-9_.-]/g, "_") + ".png");
  try {
    await page.screenshot({ path: file, timeout: 9000, animations: "disabled" });
    return { png: path.basename(file), bytes: fs.statSync(file).size };
  } catch (e) {
    return { png: null, reason: "SHOT_NOT_TAKEN_" + String(e.message || e).slice(0, 70) };
  }
}

async function drawerVisible(page) {
  return await page.evaluate(() => {
    const d = document.querySelector("[data-testid='v8-nav-drawer']");
    if (!d) return false;
    const b = d.getBoundingClientRect();
    return b.width > 0 && b.height > 0;
  });
}

async function openDrawer(page) {
  if (await drawerVisible(page)) return { opened_with: "already-open" };
  const btn = page.locator("[data-testid='v8-mobile-menu']").first();
  if ((await btn.count()) === 0) return { opened_with: null, why: "MENU_BUTTON_ABSENT" };
  try {
    await btn.click({ timeout: 6000 });
  } catch (e) {
    return { opened_with: null, why: "MENU_CLICK_REFUSED_" + String(e.message).slice(0, 70) };
  }
  for (let i = 0; i < 10; i += 1) {
    if (await drawerVisible(page)) return { opened_with: "v8-mobile-menu" };
    await page.waitForTimeout(300);
  }
  return { opened_with: null, why: "DRAWER_NOT_VISIBLE_AFTER_CLICK" };
}

function armPage(page, label) {
  page.on("request", (r) => {
    if (r.method() !== "GET") run.requests_non_get.push({ arm: label, method: r.method(), url: r.url() });
  });
  page.on("pageerror", (e) => {
    run.page_errors_total += 1;
    (run.page_error_list = run.page_error_list || []).push({
      arm: label, text: String(e && e.message ? e.message : e).slice(0, 220) });
  });
  page.on("requestfailed", (r) => {
    (run.request_failed_list = run.request_failed_list || []).push({
      arm: label, url: r.url(), failure: (r.failure() || {}).errorText });
  });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const page = await ctx.newPage();
  armPage(page, "A_first_visit");

  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(6000);
  const a = await readScreen(page, "A_first_visit");
  a.screenshot = await shot(page, "A_first_visit");
  a.wizard_mounted = (await page.locator("[data-testid='trial-setup']").count()) > 0;

  const demoBtn = page.locator("[data-testid='trial-tianjin-demo']");
  a.sealed_entry_in_dom = await demoBtn.count();
  if (a.sealed_entry_in_dom > 0) {
    try { await demoBtn.first().click({ timeout: 6000 }); } catch (e) {
      a.sealed_entry_click_refused = String(e.message).slice(0, 120);
    }
  }
  await page.waitForTimeout(12000);
  const b = await readScreen(page, "B_after_sealed_demo");
  b.screenshot = await shot(page, "B_after_sealed_demo");
  b.wizard_still_mounted = (await page.locator("[data-testid='trial-setup']").count()) > 0;

  // ---- C: every drawer row, clicked the way a traveller clicks it ----------
  const probe = await openDrawer(page);
  const entries = await page.locator("[data-testid^='v8-drawer-entry-']")
    .evaluateAll((els) => els.map((e) => ({
      testid: e.getAttribute("data-testid"),
      text: (e.innerText || "").replace(/\s+/g, " ").trim(),
    })));
  run.drawer = { open_probe: probe, entry_count: entries.length, entries };

  for (const entry of entries) {
    const key = entry.testid.replace("v8-drawer-entry-", "");
    const opened = await openDrawer(page);
    if (opened.opened_with === null) {
      run.screens.push({ arm: "C_drawer_" + key, entry_label: entry.text,
        ABORT: "DRAWER_DID_NOT_OPEN", why: opened.why });
      continue;
    }
    const loc = page.locator("[data-testid='" + entry.testid + "']").first();
    try {
      await loc.click({ timeout: 6000 });
    } catch (e) {
      run.screens.push({ arm: "C_drawer_" + key, entry_label: entry.text,
        ABORT: "CLICK_REFUSED_" + String(e.message).slice(0, 90) });
      continue;
    }
    await page.waitForTimeout(5000);
    const row = await readScreen(page, "C_drawer_" + key, { entry_label: entry.text,
      expected_route: "/v8/" + key });
    row.reached_expected_route = row.route_read_from_location === "/v8/" + key;
    row.screenshot = await shot(page, "C_" + key);
  }

  // ---- D: Trips -> 预订 -> 粘贴确认信息 (clicks, not addresses) -----------
  await page.goto(BASE + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(7000);
  await readScreen(page, "D1_trips_landed");
  for (const tab of ["trips-tab-bookings", "inbox-tab-paste"]) {
    const loc = page.locator("[data-testid='" + tab + "']").first();
    if ((await loc.count()) === 0) {
      run.screens.push({ arm: "D2_" + tab, ABORT: "TESTID_NOT_IN_DOM" });
      continue;
    }
    try { await loc.click({ timeout: 6000 }); } catch (e) {
      run.screens.push({ arm: "D2_" + tab, ABORT: "CLICK_REFUSED_" + String(e.message).slice(0, 90) });
      continue;
    }
    await page.waitForTimeout(4000);
    const row = await readScreen(page, "D2_" + tab);
    row.screenshot = await shot(page, "D_" + tab);
  }

  // ---- E/F/G: the three named screens, each as a hard address -------------
  for (const [tag, route] of [["E_stay", "/v8/stay"], ["F_access", "/v8/access"],
    ["G_hub_refresh", "/v8/hub"]]) {
    await page.goto(BASE + route, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(6000);
    const row = await readScreen(page, tag);
    row.screenshot = await shot(page, tag);
  }

  await ctx.close();
  run.finished_local = new Date().toString();
  fs.writeFileSync(path.join(OUT_DIR, "walk_r2.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("SCREENS=" + run.screens.length + " ABORTS=" +
    run.screens.filter((s) => s.ABORT).length + " NONGET=" + run.requests_non_get.length +
    " PAGEERRORS=" + run.page_errors_total + " DRAWER=" + run.drawer.entry_count);
  await browser.close();
})().catch((e) => {
  run.FATAL = String(e && e.stack ? e.stack : e).slice(0, 900);
  fs.writeFileSync(path.join(OUT_DIR, "walk_r2.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("FATAL_SEE_JSON");
  process.exitCode = 1;
});
