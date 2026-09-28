/**
 * ORD-0402 slice 2 -- the acceptance run: real clicks on real rows over this lane's own server.
 *
 * Four arms, all of them judged on rendered text (`innerText`), never on a `data-*` attribute -- a
 * screen reader and an OCR pass read what is written here, and the ORD-0400 drawer defect was covered
 * by exactly the kind of claim that attributes carry:
 *   A  the bin lists what the server says is binned, and every 找回 button is hit-tested at 390x844
 *      before and after a scroll, with the scroll's owner named (document or container);
 *   B  one real tap brings one real trip back -- checked in the server's own answers afterwards, not
 *      just in what the screen said;
 *   C  a tap on a row that is no longer binned answers 「这条已经在你的行程列表里了」 rather than a
 *      code, and the token stays on the details face;
 *   D  reading the bin again shows the empty state, which is a different sentence from "could not
 *      read" and from "the door is missing".
 *
 * The out-of-band undelete in arm C is a real POST to the landed product door, so the stale row the
 * traveller then taps is a state the product can genuinely reach (a second device, a second tab, a
 * tap that landed after the list was drawn) -- not a fixture.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const UI = process.env.ORD0402_UI ?? "http://127.0.0.1:4302";
const API = process.env.ORD0402_API_ORIGIN ?? "http://127.0.0.1:8714";
const OUT = process.env.ORD0402_OUT ?? "D:/moodle/_qoder_q_ord0402_evidence";
const WIDTH = Number(process.env.ORD0402_WIDTH ?? 390);
const HEIGHT = Number(process.env.ORD0402_HEIGHT ?? 844);
mkdirSync(OUT, { recursive: true });

const JOURNEYS = JSON.parse(process.env.ORD0402_JOURNEYS ?? "[]");

const api = async (method, path) => {
  const r = await fetch(`${API}${path}`, { method, headers: { "Content-Type": "application/json" } });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = text.slice(0, 200);
  }
  return { status: r.status, body };
};

const READ_SCREEN = () => {
  const panel = document.querySelector('[data-testid="journey-trash-panel"]');
  const rows = [...document.querySelectorAll('[data-testid="trash-row"]')];
  const buttons = [...document.querySelectorAll('[data-testid="trash-bring-back"]')];
  const describe = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      y: Math.round(r.y + window.scrollY),
      h: Math.round(r.height),
      w: Math.round(r.width),
      centre_x: Math.round(r.x + r.width / 2),
      centre_y: Math.round(r.y + r.height / 2),
      text: (el.innerText || "").replace(/\s+/g, " ").trim(),
    };
  };
  const hit = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return {
      centre: { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) },
      in_viewport: r.y >= 0 && r.bottom <= window.innerHeight,
      returns_the_button: !!top && top === el,
      what_is_on_top: top
        ? `${top.tagName.toLowerCase()}:${(top.getAttribute("data-testid") || (typeof top.className === "string" ? top.className.split(" ")[0] : "")).slice(0, 30)}`
        : "null(outside viewport)",
    };
  };
  const scrollers = [];
  for (let el = buttons[0]; el; el = el.parentElement) {
    const cs = getComputedStyle(el);
    if (el.scrollHeight - el.clientHeight > 1 && ["auto", "scroll"].includes(cs.overflowY)) {
      scrollers.push(`${el.tagName.toLowerCase()}.${(typeof el.className === "string" ? el.className : "").slice(0, 40)}`);
    }
  }
  return {
    panel_present: !!panel,
    panel_data_count: panel?.getAttribute("data-count") ?? null,
    panel_text: (panel?.innerText || "").replace(/\s+/g, " ").trim(),
    rows: rows.map((li) => ({
      journey: li.getAttribute("data-cnx-journey"),
      title: describe(li.querySelector('[data-testid="trash-row-title"]')),
      state: describe(li.querySelector('[data-testid="trash-row-state"]')),
      deleted_at: describe(li.querySelector('[data-testid="trash-row-deleted-at"]')),
      button: describe(li.querySelector('[data-testid="trash-bring-back"]')),
    })),
    button_hits: buttons.map(hit),
    scrollable_ancestors_of_first_button: scrollers,
    document_scroll_height: document.scrollingElement.scrollHeight,
    document_scroll_top: document.scrollingElement.scrollTop,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    outcome: describe(document.querySelector('[data-testid="trash-outcome"]')),
    empty_state: describe(document.querySelector('[data-testid="trash-empty"]')),
    read_failed: describe(document.querySelector('[data-testid="trash-read-failed"]')),
    details_open: !!document.querySelector(".cn-trash-details[open]"),
    reason_token_mounted: [...document.querySelectorAll('[data-cnx-field="reason_code"]')].map((el) => el.textContent),
  };
};

const browser = await chromium.launch();
const run = { ui: UI, api_origin: API, viewport: { WIDTH, HEIGHT }, journeys: JOURNEYS, arms: [] };

for (const locale of ["zh-CN", "en"]) {
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: HEIGHT } });
  const page = await ctx.newPage();
  await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
  if (JOURNEYS[0]) {
    await page.addInitScript((id) => localStorage.setItem("citynexus.v8.journey_id", id), JOURNEYS[0]);
  }
  run.arms.push({ locale, steps: [] });
  const steps = run.arms[run.arms.length - 1].steps;

  const step = async (name, extra = {}) => {
    const reading = await page.evaluate(READ_SCREEN);
    steps.push({ name, ...extra, screen: reading });
    await page.screenshot({ path: `${OUT}/trash-${locale}-${steps.length}-${name}.png` });
    return reading;
  };

  // Re-bin both trips so each locale run starts from the same durable state, through real doors:
  // a trip the landed list still shows is put back in the bin with the product's own DELETE.
  for (const id of JOURNEYS) {
    const listed = await api("GET", "/api/v1/journeys");
    if (Array.isArray(listed.body) && listed.body.some((j) => j.id === id)) {
      const del = await api("DELETE", `/api/v1/journeys/${id}`);
      steps.push({ name: "rebin", journey: id, delete_status: del.status });
    }
  }
  await page.goto(`${UI}/v8/trash`, { waitUntil: "load" });
  await page.waitForTimeout(2500);

  const a = await step("A_bin_listed");
  // Scroll the first button into the middle of the screen and hit-test again: the arm names which
  // scroller moved, because "I can click it" without an owner is the claim ORD-0400 died of.
  const scrollOwner = await page.evaluate(() => {
    const btn = document.querySelector('[data-testid="trash-bring-back"]');
    const before = document.scrollingElement.scrollTop;
    btn?.scrollIntoView({ block: "center" });
    return { before, after: document.scrollingElement.scrollTop };
  });
  const a2 = await step("A2_after_scroll", { scroll: scrollOwner });

  if (a.rows.length > 0) {
    const target = a.rows[0].journey;
    await page.getByTestId("trash-bring-back").first().click();
    await page.waitForTimeout(2200);
    const b = await step("B_after_one_tap", { tapped_journey: target });
    const serverList = await api("GET", "/api/v1/journeys");
    const serverBin = await api("GET", "/api/v1/recycle-bin/journeys");
    steps.push({
      name: "B_server_truth",
      landed_list_count: Array.isArray(serverList.body) ? serverList.body.length : null,
      landed_list_ids: (serverList.body || []).map((j) => j.id),
      assembly_bin_count: Array.isArray(serverBin.body) ? serverBin.body.length : null,
      brought_back_id_visible_on_landed_door: (serverList.body || []).some((j) => j.id === target),
    });

    // Arm C: undelete the remaining row out of band, then tap the stale row the traveller still sees.
    if (b.rows.length > 0) {
      const stale = b.rows[0].journey;
      const oob = await api("POST", `/api/v1/journeys/${stale}/undelete`);
      steps.push({ name: "C_out_of_band_undelete", journey: stale, status: oob.status, reason_code: oob.body?.error?.reason_code ?? null });
      await page.getByTestId("trash-bring-back").first().click();
      await page.waitForTimeout(2000);
      await step("C_second_tap_on_stale_row", { stale_journey: stale });
    }
    const refreshBtn = page.getByTestId("trash-refresh");
    if (await refreshBtn.count()) {
      await refreshBtn.click();
      await page.waitForTimeout(1800);
      await step("D_after_reading_again");
    }
  }
  await ctx.close();
}
await browser.close();
writeFileSync(`${OUT}/trash_two_arms_r1.json`, JSON.stringify(run, null, 2));

for (const arm of run.arms) {
  console.log(`\n##### ${arm.locale}`);
  for (const s of arm.steps) {
    if (s.name === "rebin") continue;
    if (s.screen) {
      console.log(
        `  ${s.name.padEnd(26)} rows=${s.screen.rows.length} count=${s.screen.panel_data_count} ` +
          `hits=${s.screen.button_hits.map((h) => `${h.in_viewport ? "in" : "off"}/${h.returns_the_button ? "self" : h.what_is_on_top}`).join(",")} ` +
          `scrollers=${s.screen.scrollable_ancestors_of_first_button.length}`,
      );
      console.log(`      outcome=${JSON.stringify(s.screen.outcome?.text ?? null)} empty=${JSON.stringify(s.screen.empty_state?.text ?? null)} token=${JSON.stringify(s.screen.reason_token_mounted)} details_open=${s.screen.details_open}`);
    } else {
      console.log(`  ${s.name.padEnd(26)} ${JSON.stringify(s).slice(0, 200)}`);
    }
  }
}
