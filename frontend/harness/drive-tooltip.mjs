/* Private-browser driver for the tooltip order.  The Playwright MCP browser is one process shared
   by every lane on this box, and two of my calls there were stabilised by somebody else's
   navigation instead of my page, so the measurements come from a browser of our own.
   Run from `frontend/`:  node _scratch/drive_tooltip_r1.mjs
   Writes readings to _scratch/tip_readings_r1.json and screenshots beside it. */
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";

const PAGE_URL = "http://127.0.0.1:6111/harness/tooltip-harness.html";
const OUT = new URL("./_out/", import.meta.url).pathname.replace(/^\//, "");
const R = {};
const errs = [];

const contrast = (bg, fg) => {
  const nums = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  const lum = (rgb) => {
    const c = rgb.map((v) => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const l1 = lum(nums(bg));
  const l2 = lum(nums(fg));
  return Math.round(((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)) * 100) / 100;
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 980, height: 760 }, locale: "zh-CN" });
const page = await ctx.newPage();
page.on("pageerror", (e) => errs.push("pageerror:" + String(e.message).slice(0, 200)));
page.on("console", (m) => {
  if (m.type() === "error") errs.push("console:" + String(m.text()).slice(0, 200));
});

await page.goto(PAGE_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForSelector("#arm-a .v12-activity-title", { timeout: 60000 });
await page.waitForTimeout(700);

R.mount = await page.evaluate(() => ({
  root_children: document.getElementById("root").children.length,
  body_chars: document.body.innerText.trim().length,
  long_text_in_dom: document.body.innerText.includes("waiting hall three"),
  animation_count: document.getAnimations().length,
}));

const geom = await page.evaluate(() => {
  const info = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, missing: true };
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      clipped: el.scrollWidth - el.clientWidth > 1,
      whiteSpace: cs.whiteSpace,
      textOverflow: cs.textOverflow,
      text_len: (el.textContent || "").length,
    };
  };
  const card = document.getElementById("arm-a");
  const cr = card.getBoundingClientRect();
  return {
    a: info("#arm-a .v12-activity-title"),
    b: info("#arm-b .cn-collections__item-note"),
    c: info("#arm-c .v12-activity-title"),
    card_overflow: getComputedStyle(card).overflow,
    card_rect: [Math.round(cr.x), Math.round(cr.y), Math.round(cr.width), Math.round(cr.height), Math.round(cr.bottom)],
  };
});
R.geometry = geom;

/* arm A — the clipped label inside the clipping card */
const anchorA = page.locator("#arm-a .v12-activity-title");
await page.mouse.move(12, 12);
await page.waitForTimeout(150);
await anchorA.hover({ timeout: 20000 });
R.arm_a_bubbles_at_once = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);
await page.waitForTimeout(220);
R.arm_a_bubbles_after_220ms = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);
R.arm_a_bubble = await anchorA.evaluate((el) => {
  const b = document.querySelector(".cn-tip");
  if (!b) return null;
  const cs = getComputedStyle(b);
  const r = b.getBoundingClientRect();
  return {
    role: b.getAttribute("role"),
    parent_is_body: b.parentElement === document.body,
    position: cs.position,
    equals_full_value: b.textContent === el.textContent,
    bubble_text_len: b.textContent.length,
    anchor_text_len: el.textContent.length,
    opacity: cs.opacity,
    whiteSpace: cs.whiteSpace,
    overflowY: cs.overflowY,
    font_size: cs.fontSize,
    bg: cs.backgroundColor,
    fg: cs.color,
    rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    viewport: [window.innerWidth, window.innerHeight],
    in_viewport: r.x >= 0 && r.y >= 0 && r.right <= window.innerWidth + 1 && r.bottom <= window.innerHeight + 1,
    describedby_matches: b.id !== "" && el.getAttribute("aria-describedby") === b.id,
  };
});
R.arm_a_contrast = R.arm_a_bubble ? contrast(R.arm_a_bubble.bg, R.arm_a_bubble.fg) : null;
await page.screenshot({ path: OUT + "tip1008_arm_a_hover.png" });

/* does the bubble escape the card's own clip?  the card clips; the bubble must still be whole */
R.arm_a_escapes_card_clip = await page.evaluate(() => {
  const b = document.querySelector(".cn-tip");
  const card = document.getElementById("arm-a");
  if (!b || !card) return null;
  const br = b.getBoundingClientRect();
  const cr = card.getBoundingClientRect();
  const ix = Math.max(br.x, cr.x);
  const iy = Math.max(br.y, cr.y);
  const iw = Math.min(br.right, cr.right) - ix;
  const ih = Math.min(br.bottom, cr.bottom) - iy;
  const overlap = iw > 0 && ih > 0 ? { x: ix + iw / 2, y: iy + ih / 2, area: Math.round(iw * ih) } : null;
  const probe = overlap ? document.elementFromPoint(overlap.x, overlap.y) : null;
  return {
    /* The decisive arm: a point inside BOTH the card's box and the bubble's box has to hit the
       bubble.  A bubble that was a descendant of the card would be cut at that pixel by the card's
       own `overflow: hidden` — which is the ORD-0510 failure this design has to clear. */
    overlap_px: overlap ? overlap.area : 0,
    overlap_point_hits_bubble: probe !== null && (probe === b || b.contains(probe)),
    bubble_whole_in_viewport: br.right <= window.innerWidth + 1 && br.bottom <= window.innerHeight + 1,
    bubble_rect: [Math.round(br.x), Math.round(br.y), Math.round(br.width), Math.round(br.height)],
    card_rect: [Math.round(cr.x), Math.round(cr.y), Math.round(cr.width), Math.round(cr.height)],
  };
});

/* leave → must close */
await page.mouse.move(12, 12);
await page.waitForTimeout(320);
R.arm_a_bubbles_after_leave = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);

/* arm C — negative control: the label fits, so hovering must produce nothing */
const anchorC = page.locator("#arm-c .v12-activity-title");
await anchorC.hover({ timeout: 20000 });
await page.waitForTimeout(400);
R.arm_c_bubbles = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);
await page.screenshot({ path: OUT + "tip1008_arm_c_negative.png" });
await page.mouse.move(12, 12);
await page.waitForTimeout(200);

/* arm B — the long bilingual note */
const anchorB = page.locator("#arm-b .cn-collections__item-note");
await anchorB.hover({ timeout: 20000 });
await page.waitForTimeout(260);
R.arm_b_bubble = await anchorB.evaluate((el) => {
  const b = document.querySelector(".cn-tip");
  if (!b) return null;
  const cs = getComputedStyle(b);
  const r = b.getBoundingClientRect();
  return {
    equals_full_value: b.textContent === el.textContent,
    bubble_text_len: b.textContent.length,
    anchor_text_len: el.textContent.length,
    clientHeight: b.clientHeight,
    scrollHeight: b.scrollHeight,
    content_scrollable: b.scrollHeight > b.clientHeight,
    whiteSpace: cs.whiteSpace,
    overflowWrap: cs.overflowWrap,
    line_count: parseFloat(cs.lineHeight) > 0 ? Math.round(r.height / parseFloat(cs.lineHeight)) : -1,
    rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    in_viewport: r.right <= window.innerWidth + 1 && r.bottom <= window.innerHeight + 1,
  };
});
await page.screenshot({ path: OUT + "tip1008_arm_b_longnote.png" });

/* Escape closes — the arm is only meaningful on a bubble proven open in the same breath, so the
   open count is read first and carried. */
await page.mouse.move(12, 12);
await page.waitForTimeout(240);
await anchorA.hover({ timeout: 20000 });
await page.waitForTimeout(220);
R.escape_precondition_bubbles = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);
await page.keyboard.press("Escape");
await page.waitForTimeout(240);
R.bubbles_after_escape = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);

/* dark theme, on a bubble proven open the same way */
await page.mouse.move(12, 12);
await page.waitForTimeout(240);
await anchorA.hover({ timeout: 20000 });
await page.waitForTimeout(220);
R.dark_precondition_bubbles = await page.evaluate(() => document.querySelectorAll(".cn-tip").length);
R.dark = await page.evaluate(() => {
  const b = document.querySelector(".cn-tip");
  if (!b) return null;
  document.documentElement.setAttribute("data-theme", "dark");
  const cs = getComputedStyle(b);
  return { bg: cs.backgroundColor, fg: cs.color, opacity: cs.opacity };
});
R.dark_contrast = R.dark ? contrast(R.dark.bg, R.dark.fg) : null;
await page.screenshot({ path: OUT + "tip1008_arm_a_dark.png" });
await page.evaluate(() => document.documentElement.removeAttribute("data-theme"));

/* touch arm: no hover capability, so a tap must pin the bubble and it must survive the finger
   leaving, then close on a tap outside */
const tctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  isMobile: true,
  deviceScaleFactor: 3,
  locale: "zh-CN",
});
const tpage = await tctx.newPage();
await tpage.goto(PAGE_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await tpage.waitForSelector("#arm-a .v12-activity-title", { timeout: 60000 });
await tpage.waitForTimeout(500);
R.touch_media = await tpage.evaluate(() => ({
  hover_none: window.matchMedia("(hover: none)").matches,
  pointer_coarse: window.matchMedia("(pointer: coarse)").matches,
}));
const box = await tpage.locator("#arm-a .v12-activity-title").boundingBox();
await tpage.evaluate(
  (b) => window.scrollTo(0, Math.max(0, b.y - 200)),
  box,
);
const box2 = await tpage.locator("#arm-a .v12-activity-title").boundingBox();
const hit = await tpage.evaluate(
  (b) => {
    const el = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
    const target = document.querySelector("#arm-a .v12-activity-title");
    return { hit_is_target: el === target || (el !== null && target.contains(el)) };
  },
  box2,
);
await tpage.touchscreen.tap(box2.x + box2.width / 2, box2.y + box2.height / 2);
await tpage.waitForTimeout(250);
R.touch_after_tap = await tpage.evaluate(() => {
  const b = document.querySelector(".cn-tip");
  return {
    bubbles: document.querySelectorAll(".cn-tip").length,
    pinned: b ? b.getAttribute("data-pinned") : null,
    text_len: b ? b.textContent.length : 0,
  };
});
await tpage.screenshot({ path: OUT + "tip1008_touch_tapped.png" });
await tpage.touchscreen.tap(320, 700);
await tpage.waitForTimeout(250);
R.touch_after_tap_outside = await tpage.evaluate(() => document.querySelectorAll(".cn-tip").length);

R.hit_provenance = hit;
R.errors = errs;
await ctx.close();
await tctx.close();
await browser.close();

writeFileSync(OUT + "tip_readings_r1.json", JSON.stringify({ R }, null, 1), "utf8");
console.log(JSON.stringify({ R }, null, 1));
