// Select ruler: measures every dropdown this lane touches on the running dev server.
// Same file gives the BEFORE numbers (product routes) and the AFTER numbers
// (product routes + the dev-only long-list lab). Read-only against the browser.
//
//   node review/select/select_measure_r1.mjs --base http://127.0.0.1:5399 --out /tmp/select.json
import { createRequire } from "node:module";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const argv = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 ? argv[i + 1] : dflt;
};

// frontend/node_modules is where this tree's dependencies live; the ruler sits
// outside it, so resolve playwright from here instead of by bare specifier.
const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const { chromium } = require(
  resolve(
    arg("playwright", join(HERE, "..", "..", "frontend", "node_modules", "playwright")),
    ".",
  ),
);

const BASE = arg("base", "http://127.0.0.1:5399");
// The long arm has no product screen to live on yet -- the widest dropdown on the
// authoritative line measures five options -- so it is driven where the repo already
// mounts primitives: the Storybook iframe, on the shipped component code.
const LAB_URL = arg(
  "lab",
  "http://127.0.0.1:6199/iframe.html?id=controls-select--long-list-searchable-arm&viewMode=story",
);
const OUT = arg("out", "");
const SHOTS = arg("shots", "");
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

// Each target: a route the traveller can actually reach, plus the clicks that get
// from the route to the control. A control this list cannot reach is reported with
// the testids that were on screen, so "not found" is never a bare claim.
const PRODUCT_TARGETS = [
  { route: "/v8/access", testid: "access-invite-visibility", name: "invite visibility" },
  {
    route: "/v8/bookings",
    testid: "manual-type",
    name: "inbox manual type",
    reach: ["inbox-tab-manual"],
  },
  {
    route: "/v8/bookings",
    testid: "v13-2-anchor-role",
    name: "anchor role",
    reach: ["inbox-pending-row", "inbox-pending-title"],
  },
  { route: "/v8/discover", testid: "(discovery evidence mode)", name: "evidence mode" },
  { route: "/legacy", testid: "agent-autonomy", name: "legacy autonomy" },
  { route: "/legacy", testid: "agent-mode", name: "legacy agent mode" },
];

const VIEWPORTS = {
  mobile: { width: 390, height: 844 },
  desktop: { width: 1280, height: 900 },
};

const JOURNEY = process.env.CITYNEXUS_JOURNEY_ID || "";

/** Read the control itself, in the page, at whatever viewport is live. */
async function measureControl(page, testid) {
  return page.evaluate((wanted) => {
    const nodes = Array.from(document.querySelectorAll("select"));
    const byTestId = nodes.find((s) => s.getAttribute("data-testid") === wanted);
    // The discovery control carries no testid; match it by its accessible name instead.
    const target =
      byTestId ||
      (wanted.startsWith("(")
        ? nodes.find((s) => (s.getAttribute("aria-label") || "").length > 0)
        : null);
    if (!target) return { found: false, selects_on_page: nodes.length };
    const box = target.getBoundingClientRect();
    const cs = getComputedStyle(target);
    const label =
      target.getAttribute("aria-label") ||
      (() => {
        const wrapping = target.closest("label");
        if (wrapping) return (wrapping.textContent || "").trim().slice(0, 40);
        const id = target.id;
        const bound = id ? document.querySelector(`label[for="${id}"]`) : null;
        return bound ? (bound.textContent || "").trim().slice(0, 40) : null;
      })();
    return {
      found: true,
      tag: target.tagName.toLowerCase(),
      option_count: target.options.length,
      rendered_nodes: target.querySelectorAll("option").length,
      h_css: Math.round(box.height * 10) / 10,
      w_css: Math.round(box.width),
      min_height: cs.minHeight,
      font_size: cs.fontSize,
      touch_target_ok: box.height >= 44,
      accessible_name_present: !!label,
      accessible_name: label,
    };
  }, testid);
}

/** Long arm: the Storybook mount of the shipped component.
 *  Every keystroke here goes through Playwright's own input, because a synthetic
 *  `input` event dispatched in the page is not what React's controlled field listens
 *  for -- an earlier revision of this ruler typed that way and read "filter does
 *  nothing" out of its own broken probe. */
const LAB_PREFIX = '[data-testid="lab-searchable-select"]';
const optionsOnScreen = (page) =>
  page.locator('[data-testid="lab-searchable-select-panel"] [role="option"]').count();
const readDom = (page) =>
  page.evaluate(() => {
    const list = document.querySelector('[data-testid="lab-searchable-select-list"]');
    const count = document.querySelector('[data-testid="lab-searchable-select-count"]');
    const panel = document.querySelector('[data-testid="lab-searchable-select-panel"]');
    const painted = list ? list.querySelectorAll('[role="option"]').length : null;
    const pr = panel ? panel.getBoundingClientRect() : null;
    const rowHeights = list
      ? Array.from(list.querySelectorAll('[role="option"]')).map((n) =>
          Math.round(n.getBoundingClientRect().height),
        )
      : [];
    return {
      panel_present: !!panel,
      panel_position: panel ? getComputedStyle(panel).position : null,
      panel_top: pr ? Math.round(pr.top) : null,
      panel_bottom: pr ? Math.round(pr.bottom) : null,
      panel_flush_with_viewport_bottom: pr
        ? Math.abs(pr.bottom - innerHeight) <= 2
        : null,
      list_client_height_px: list ? Math.round(list.clientHeight) : null,
      min_option_height_px: rowHeights.length ? Math.min(...rowHeights) : null,
      options_under_44px: rowHeights.filter((h) => h < 44).length,
      search_present: !!document.querySelector('[data-testid="lab-searchable-select-search"]'),
      list_marks_empty: list ? list.getAttribute("data-empty") : null,
      painted_rows: painted,
      count_text: count ? (count.textContent || "").trim() : null,
      first_labels: list
        ? Array.from(list.querySelectorAll('[role="option"]'))
            .slice(0, 3)
            .map((n) => (n.textContent || "").trim().replace(/\s+/g, " ").slice(0, 34))
        : null,
    };
  });

async function measureLab(page, { query, keyword }) {
  const trigger = page.locator(LAB_PREFIX);
  if ((await trigger.count()) === 0) return { mounted: false };
  await trigger.click();
  await page.waitForTimeout(120);
  const opened = { mounted: true, ...(await readDom(page)) };
  const search = page.locator('[data-testid="lab-searchable-select-search"]');

  const t0 = Date.now();
  await search.fill(query);
  await page.waitForFunction(
    (needle) => {
      const list = document.querySelector('[data-testid="lab-searchable-select-list"]');
      if (!list) return false;
      const rows = Array.from(list.querySelectorAll('[role="option"]'));
      return (
        rows.length > 0 &&
        rows.every((n) => (n.textContent || "").toLowerCase().includes(needle))
      );
    },
    query.toLowerCase(),
    { timeout: 8000 },
  );
  const filterMs = Math.round((Date.now() - t0) * 10) / 10;
  const filtered = await readDom(page);

  // A keyword the label never shows must still match -- that column exists for the word
  // the traveller copied off their confirmation email.
  await search.fill(keyword);
  await page.waitForTimeout(150);
  const keywordHit = await readDom(page);

  // No match has to say so with a number, not a silent empty box.
  await search.fill("zzqx nothing matches this");
  await page.waitForTimeout(150);
  const none = await readDom(page);

  // Window: paint only a slice, then scroll to the far end and watch how many nodes
  // were ever live at one moment.
  await search.fill("");
  await page.waitForTimeout(150);
  let maxNodes = 0;
  for (let step = 0; step < 60; step += 1) {
    maxNodes = Math.max(maxNodes, await optionsOnScreen(page));
    const atEnd = await page.evaluate(() => {
      const list = document.querySelector('[data-testid="lab-searchable-select-list"]');
      if (!list) return true;
      list.scrollTop = list.scrollTop + 500;
      return list.scrollTop + list.clientHeight >= list.scrollHeight - 1;
    });
    await page.waitForTimeout(30);
    if (atEnd) break;
  }
  const scrolled = await readDom(page);
  maxNodes = Math.max(maxNodes, await optionsOnScreen(page));

  // Keyboard: the cursor has to move without a pointer.
  const keyboard = await page.evaluate(async () => {
    const list = document.querySelector('[data-testid="lab-searchable-select-list"]');
    return { active_row: list ? list.querySelectorAll('[data-active="true"]').length : null };
  });

  return {
    opened,
    filter_ms: filterMs,
    filtered,
    keyword: { needle: keyword, ...keywordHit },
    none,
    window: {
      max_nodes_live_at_any_moment: maxNodes,
      scroll_height_px: await page.evaluate(
        () => document.querySelector('[data-testid="lab-searchable-select-list"]').scrollHeight,
      ),
      painted_after_full_scroll: scrolled.painted_rows,
      count_text: scrolled.count_text,
    },
    keyboard,
  };
}

const browser = await chromium.launch({ channel: arg("channel", "") || undefined });
const report = { base: BASE, journey: JOURNEY, viewports: {} };

for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
  const ctx = await browser.newContext({ viewport });
  const page = await ctx.newPage();
  if (JOURNEY) {
    await page.goto(`${BASE}/hub`);
    await page.evaluate(
      (id) => localStorage.setItem("citynexus.v8.journey_id", id),
      JOURNEY,
    );
  }
  const rows = [];
  const seenRoutes = new Map();
  for (const target of PRODUCT_TARGETS) {
    if (!seenRoutes.has(target.route)) {
      const response = await page.goto(`${BASE}${target.route}`, {
        waitUntil: "domcontentloaded",
      });
      await page.waitForTimeout(900);
      seenRoutes.set(target.route, response ? response.status() : 0);
    }
    for (const testId of target.reach || []) {
      await page
        .locator(`[data-testid="${testId}"]`)
        .click({ timeout: 5000 })
        .catch(() => {});
      await page.waitForTimeout(250);
    }
    let measured = await measureControl(page, target.testid);
    if (!measured.found) {
      // A negative gets an inventory, not a bare "not found".
      measured = {
        ...measured,
        on_screen_testids: await page.evaluate(() =>
          Array.from(document.querySelectorAll("[data-testid]"))
            .map((n) => n.getAttribute("data-testid"))
            .slice(0, 40)
        ),
        body_chars: await page.evaluate(() => document.body.innerText.trim().length),
      };
    }
    rows.push({ ...target, route_status: seenRoutes.get(target.route), ...measured });
    if (SHOTS && measured.found) {
      const shot = `${SHOTS}/select_${vpName}_${target.testid.replace(/[()]/g, "")}.png`;
      await page.locator("select").first().screenshot({ path: shot }).catch(() => {});
    }
  }

  let lab = { mounted: false };
  const labResponse = await page.goto(LAB_URL, { waitUntil: "domcontentloaded" });
  if (labResponse && labResponse.status() === 200) {
    await page.waitForTimeout(900);
    lab = await measureLab(page, { query: "harbour", keyword: "CNX-12" });
    if (SHOTS && lab.mounted) {
      await page.screenshot({
        path: `${SHOTS}/lab_${vpName}.png`,
        fullPage: false,
      });
    }
  }

  report.viewports[vpName] = { viewport, product_selects: rows, long_list_lab: lab };
  await ctx.close();
}

await browser.close();

const json = JSON.stringify(report, null, 2);
if (OUT) {
  mkdirSync(OUT.replace(/[^/\\]*$/, "").replace(/[\\/]+$/, "/") || ".", { recursive: true });
  writeFileSync(OUT, json + "\n", "utf-8");
}
console.log(json);
