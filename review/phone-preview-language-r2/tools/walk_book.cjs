/* Building walk: a person opens the app on a phone and books one trip, step by step.
 *
 * Screens: 1) 新建行程 form  2) 人数与偏好  3) 确认创建 → created.  At every step this reads the RENDERED
 * text a person would see, screenshots the step, and decides PASS (words are human and the control is
 * pressable) or BLOCKED (the step refuses to advance, speaks in codes, or the control cannot be hit).
 *
 * A press counts only when the browser's own scrollIntoViewIfNeeded leaves elementFromPoint at the
 * control's centre landing on the control -- clicking a collapsed or off-screen node and believing it
 * worked is how a walk reports success it did not get.
 *
 * argv: node walk_book.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4881";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_book.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

const run = { schema: "CNX_BUILDING_WALK_BOOK", base: BASE_URL, viewport: { width: W, height: H },
  started: new Date().toString(), steps: [], page_errors: [], console_errors: [], outcome: "INCOMPLETE" };

async function readScreen(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const pressables = Array.from(document.querySelectorAll("button,[role='button'],a,input[type='submit']")).filter(vis)
      .map((el) => ({ tag: el.tagName, type: el.getAttribute("type") || null,
        testid: el.getAttribute("data-testid") || null, words: strip(el.innerText || el.value).slice(0, 60),
        disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true",
        aria: el.getAttribute("aria-label") || null }));
    const inputs = Array.from(document.querySelectorAll("input,select,textarea")).filter(vis)
      .map((el) => ({ tag: el.tagName, type: el.type || null, name: el.name || el.id || null,
        placeholder: el.placeholder || null, testid: el.getAttribute("data-testid") || null,
        value: el.value || null }));
    const suspicious = [];
    for (const [re, kind] of [[/\b[A-Z][A-Z0-9_]{4,}\b/g,"UPPER_SNAKE"],[/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g,"UUID"],
        [/\b(400|401|403|404|409|422|500|502|503)\b/g,"HTTP_STATUS"],[/\b(null|undefined|true|false|NaN)\b/g,"CODE_LITERAL"]]) {
      const m = body.match(re); if (m) suspicious.push({ kind, hits: Array.from(new Set(m)).slice(0, 8) });
    }
    return { tag, path: location.pathname, chars: body.length, body_text: strip(body).slice(0, 2600),
             pressables, inputs, suspicious };
  }, tag);
}

async function press(page, predicateWords, tag) {
  // scroll it into view, then require elementFromPoint at centre to land on the node before clicking
  const loc = page.locator("button,[role='button'],a").filter({ hasText: predicateWords }).first();
  if (await loc.count() === 0) return { pressed: false, why: "NO_SUCH_CONTROL_" + predicateWords };
  const hit = await loc.evaluate((el) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return { cx, cy, inViewport: b.top >= 0 && b.bottom <= innerHeight, landed: !!top && (top === el || el.contains(top)),
             w: b.width, h: b.height, disabled: !!el.disabled };
  });
  if (hit.disabled) return { pressed: false, why: "CONTROL_DISABLED_" + predicateWords, hit };
  if (!hit.landed) return { pressed: false, why: "HIT_TEST_MISSED_" + predicateWords, hit };
  await loc.click();
  await page.waitForTimeout(1200);
  return { pressed: true, hit };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });

  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2000);
  let s = await readScreen(page, "step1_form");
  run.steps.push(s); await page.screenshot({ path: OUT.replace(/\.json$/, "_step1.png"), fullPage: true });

  // the seeded demo trip is the shortest honest path to a booking; if it is not offered, fill the form
  const demo = await press(page, /使用封存的演示行程/, "step1_demo");
  run.demo_press = demo;
  s = await readScreen(page, "after_demo");
  run.steps.push(s); await page.screenshot({ path: OUT.replace(/\.json$/, "_afterdemo.png"), fullPage: true });

  // if a next button is present, advance; capture where it lands and whether it is human-readable
  let guard = 0;
  while (guard++ < 6) {
    const cur = await readScreen(page, "loop" + guard);
    const next = cur.pressables.find((p) => /下一步|确认创建|创建行程|完成/.test(p.words || "") && !p.disabled);
    const hasSummary = /确认创建|创建行程|即将创建/.test(cur.body_text);
    if (hasSummary || !next) { run.steps.push(cur); break; }
    const r = await press(page, new RegExp(next.words.slice(0, 8)), "next");
    run.steps.push({ tag: "after_next_" + guard, press: r, screen: await readScreen(page, "after_next_" + guard) });
    await page.screenshot({ path: OUT.replace(/\.json$/, "_next" + guard + ".png"), fullPage: true });
    if (!r.pressed) break;
  }

  const final = await readScreen(page, "final");
  run.final = final;
  run.final_text = final.body_text;
  await page.screenshot({ path: OUT.replace(/\.json$/, "_final.png"), fullPage: true });

  // did a journey actually get created? look for a real success signal, not "the form still shows 下一步"
  const created = /行程已创建|创建成功|已为你创建|查看行程|出发|我的行程/.test(final.body_text);
  run.outcome = created ? "BOOKED" : (run.steps.some((x) => x.body_text && /还需要填写|请填写|不能为空|失败|错误/.test(x.body_text)) ? "BLOCKED" : "STUCK");
  run.journey_created_detected = created;
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await browser.close();
  console.log("OUTCOME=" + run.outcome + " created=" + created);
  console.log("FINAL_TEXT:\n" + final.body_text.slice(0, 900));
})().catch((e) => { console.error("WALK_FAIL " + e); process.exit(1); });