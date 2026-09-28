/**
 * ORD-0382 layout probe -- measures the three defects the commander read off the live screen, at
 * 320 / 360 / 390 / 414, on whatever generation the given base serves.
 *
 * Nothing here is inferred from CSS: every number is a bounding box, a computed style or
 * `document.elementFromPoint` at the control's own centre, which is the reachability ruler this
 * project already uses (ORD-0382 / ORD-0338: a clipped control is not a covered one, and
 * `scrolled > 0` does not prove anything).
 *
 * Zero writes: the two mutating legs are answered inside the browser and never leave it.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0382_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0382_OUT ?? "D:/moodle/_qoder_q_ord0382_evidence/layout";
mkdirSync(OUT, { recursive: true });
const WIDTHS = [320, 360, 390, 414];

const box = (el) => {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return {
    x: Math.round(r.x), y: Math.round(r.y),
    w: Math.round(r.width), h: Math.round(r.height),
    lines: Math.round(r.height / (parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.45)),
    font: cs.fontSize, color: cs.color, bg: cs.backgroundColor,
    weight: cs.fontWeight, overflow: cs.textOverflow,
    ellipsis: cs.webkitLineClamp || "",
  };
};

const results = [];
const browser = await chromium.launch();

for (const width of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), "zh-CN");
  await page.route("**/api/v1/journeys/*/agent/commands", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
  await page.route("**/api/v1/journeys/*/plans/generate", (route) =>
    route.fulfill({ status: 422, contentType: "application/json", body: "{}" }));
  await page.goto(`${BASE}/v8`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  if (await page.getByTestId("trial-setup").count()) {
    const btn = page.getByTestId("trial-tianjin-demo");
    if (await btn.count()) {
      await btn.click();
      await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 });
    }
  }
  await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  await page.waitForTimeout(1800);
  const entry = page.getByTestId("hub-plan-with-ai");
  if (!(await entry.count())) {
    results.push({ width, error: "no entry", body: (await page.locator("body").innerText()).slice(0, 120) });
    await ctx.close();
    continue;
  }
  await entry.click();
  await page.getByTestId("plan-ai-sheet").waitFor({ timeout: 15_000 });
  await page.waitForTimeout(900);

  const m = await page.evaluate(() => {
    const q = (sel) => document.querySelector(sel);
    const box = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
        line_h: cs.lineHeight, font: cs.fontSize, color: cs.color, bg: cs.backgroundColor, weight: cs.fontWeight,
      };
    };
    const sheet = q(".plan-ai-sheet");
    const headText = q(".plan-ai-head > div");
    const small = q(".plan-ai-head small");
    const close = q(".plan-ai-close");
    const chips = Array.from(document.querySelectorAll(".plan-ai-examples button"));
    const dismiss = document.querySelector('[data-testid="plan-ai-dismiss"]');
    const submit = document.querySelector('[data-testid="plan-ai-submit"]');
    /* What the chip will actually put into the box when pressed -- read off the click handler's
       effect, not off the label: fill the textarea by clicking, then read the value back. */
    const chipRows = chips.map((c) => ({ label: c.textContent, box: box(c) }));
    const scroll = q(".plan-ai-scroll");
    return {
      sheet: box(sheet),
      viewport: { w: innerWidth, h: innerHeight },
      head_text: box(headText),
      head_small: box(small),
      close: box(close),
      chips: chipRows,
      textarea: box(q(".plan-ai-field textarea")),
      scroll: { ...box(scroll), scrollH: scroll?.scrollHeight, clientH: scroll?.clientHeight },
      actions: { dismiss: box(dismiss), submit: box(submit) },
      /* hit-test: is the centre of each control the thing that actually receives the press? */
      hit: {
        close: close ? (document.elementFromPoint(close.getBoundingClientRect().x + close.getBoundingClientRect().width / 2, close.getBoundingClientRect().y + close.getBoundingClientRect().height / 2) === close) : null,
        dismiss: dismiss ? ((r) => document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === dismiss)(dismiss.getBoundingClientRect()) : null,
        submit: submit ? ((r) => document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === submit)(submit.getBoundingClientRect()) : null,
        chips: chips.map((c) => { const r = c.getBoundingClientRect(); return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === c; }),
      },
      in_viewport: {
        close: close ? close.getBoundingClientRect().bottom <= innerHeight : null,
        submit: submit ? submit.getBoundingClientRect().bottom <= innerHeight : null,
        dismiss: dismiss ? dismiss.getBoundingClientRect().bottom <= innerHeight : null,
      },
    };
  });

  /* Does pressing a chip put the FULL sentence in the box, or the truncated label? */
  const chipTruth = [];
  for (let i = 0; i < m.chips.length; i += 1) {
    await page.locator(".plan-ai-examples button").nth(i).click();
    const value = await page.getByTestId("plan-ai-input").inputValue();
    chipTruth.push({ label: m.chips[i].label, submitted_text: value, label_is_full_text: value === m.chips[i].label });
    await page.getByTestId("plan-ai-input").fill("");
  }
  const wrapped = await page.evaluate(() => {
    const el = document.querySelector(".plan-ai-head small");
    if (!el) return null;
    const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.2;
    return { text: el.textContent, lines: Math.round(el.getBoundingClientRect().height / lh) };
  });
  results.push({
    width,
    sheet_w: m.sheet?.w, head_text_w: m.head_text?.w, close_w: m.close?.w,
    close_x: m.close?.x, textarea_w: m.textarea?.w,
    head_small: wrapped, chips: chipTruth, chip_boxes: m.chips,
    actions: m.actions, hit: m.hit, in_viewport: m.in_viewport,
    scroll: m.scroll,
    screenshot: `${OUT}/sheet-${width}.png`,
  });
  await page.screenshot({ path: `${OUT}/sheet-${width}.png` });
  await ctx.close();
}

writeFileSync(`${OUT}/measurements.json`, JSON.stringify(results, null, 2) + "\n", "utf-8");
await browser.close();
for (const r of results) {
  console.log(`\n### width=${r.width} sheet_w=${r.sheet_w} head_text_w=${r.head_text_w} close_w=${r.close_w} textarea_w=${r.textarea_w}`);
  console.log(`  head_small lines=${r.head_small?.lines} text=${r.head_small?.text}`);
  for (const c of r.chips ?? []) console.log(`  chip label_is_full_text=${c.label_is_full_text} label=${JSON.stringify(c.label)} submitted=${JSON.stringify(c.submitted_text)}`);
  console.log(`  hit close=${r.hit?.close} dismiss=${r.hit?.dismiss} submit=${r.hit?.submit} chips=${JSON.stringify(r.hit?.chips)}`);
  console.log(`  in_viewport close=${r.in_viewport?.close} dismiss=${r.in_viewport?.dismiss} submit=${r.in_viewport?.submit}`);
  console.log(`  submit_box=${JSON.stringify(r.actions?.submit)} dismiss_box=${JSON.stringify(r.actions?.dismiss)}`);
}
