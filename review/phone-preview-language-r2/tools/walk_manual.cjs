/* Building walk, second path: the person who does NOT take the demo shortcut -- they type a city and
 * places and press 下一步 through all three steps to create a trip.
 *
 * This is where "点不动" and "不知道成没成" actually live: a disabled Next is fine if the screen says
 * what is missing and takes you there; it is a defect if the Next stays dead with no explanation, or if
 * a step advances without saying what happened.  Every step is read as rendered words and screenshotted.
 *
 * argv: node walk_manual.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4881";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_manual.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

const run = { schema: "CNX_BUILDING_WALK_MANUAL", base: BASE_URL, viewport: { width: W, height: H },
  started: new Date().toString(), steps: [], page_errors: [], console_errors: [], outcome: "INCOMPLETE" };

async function readScreen(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const pressables = Array.from(document.querySelectorAll("button,[role='button'],a")).filter(vis)
      .map((el) => ({ words: strip(el.innerText).slice(0, 60), testid: el.getAttribute("data-testid") || null,
        disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true" }));
    const suspicious = [];
    for (const [re, kind] of [[/\b[A-Z][A-Z0-9_]{4,}\b/g,"UPPER_SNAKE"],[/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g,"UUID"],
        [/\b(400|401|403|404|409|422|500|502|503)\b/g,"HTTP_STATUS"],[/\b(null|undefined|true|false|NaN)\b/g,"CODE_LITERAL"]]) {
      const m = body.match(re); if (m) suspicious.push({ kind, hits: Array.from(new Set(m)).slice(0, 8) });
    }
    const missing = body.match(/还需要填写[：:][^\n。]*/g) || [];
    return { tag, path: location.pathname, chars: body.length, body_text: strip(body).slice(0, 2600),
             pressables, suspicious, missing_calls: missing };
  }, tag);
}

async function press(page, words, tag) {
  const loc = page.locator("button,[role='button'],a").filter({ hasText: words }).first();
  if (await loc.count() === 0) return { pressed: false, why: "NO_SUCH_CONTROL_" + words };
  const hit = await loc.evaluate((el) => { el.scrollIntoViewIfNeeded(); const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { landed: !!top && (top === el || el.contains(top)), disabled: !!el.disabled,
             inViewport: b.top >= 0 && b.bottom <= innerHeight }; });
  if (hit.disabled) return { pressed: false, why: "DISABLED_" + words, hit };
  if (!hit.landed) return { pressed: false, why: "HIT_TEST_MISSED_" + words, hit };
  await loc.click(); await page.waitForTimeout(1400);
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
  await page.waitForTimeout(1800);
  run.steps.push(await readScreen(page, "step1_empty"));
  await page.screenshot({ path: OUT.replace(/\.json$/, "_step1.png"), fullPage: true });

  // is the empty Next explained? press one missing-field jump first: a person would
  const jump = await press(page, /目的地/, "step1_jump");
  run.missing_jump = jump;
  run.after_jump = await readScreen(page, "after_jump");
  await page.screenshot({ path: OUT.replace(/\.json$/, "_jump.png"), fullPage: true });

  // fill the three required text fields
  await page.locator("[data-testid='trial-city']").fill("北京");
  await page.locator("[data-testid='trial-arrival']").fill("北京站");
  await page.locator("[data-testid='trial-departure']").fill("天安门");
  await page.waitForTimeout(900);
  run.step1_filled = await readScreen(page, "step1_filled");
  await page.screenshot({ path: OUT.replace(/\.json$/, "_filled.png"), fullPage: true });

  // advance through the steps
  for (let i = 1; i <= 4; i++) {
    const cur = await readScreen(page, "loop" + i);
    const next = cur.pressables.find((p) => /下一步|确认创建|创建行程|完成|生成/.test(p.words || "") && !p.disabled);
    if (!next) { run.steps.push(cur); run.stall_at = cur.tag + " next_candidates=" +
      JSON.stringify(cur.pressables.filter((p) => /下一步|确认|创建|完成|生成/.test(p.words || ""))); break; }
    const r = await press(page, new RegExp(next.words.slice(0, 6)), "advance" + i);
    const scr = await readScreen(page, "after_advance" + i);
    run.steps.push({ tag: "advance" + i, press: r, screen: scr });
    await page.screenshot({ path: OUT.replace(/\.json$/, "_adv" + i + ".png"), fullPage: true });
    if (!r.pressed) { run.stall_at = "advance" + i; break; }
    if (/行程已创建|创建成功|已为你创建|查看行程|打开行程工作台/.test(scr.body_text)) { run.created = true; break; }
  }
  run.final = await readScreen(page, "final");
  run.final_text = run.final.body_text;
  await page.screenshot({ path: OUT.replace(/\.json$/, "_final.png"), fullPage: true });
  run.outcome = run.created ? "BOOKED" : (run.stall_at ? "STALLED_AT_" + run.stall_at : "STUCK");
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await browser.close();
  console.log("OUTCOME=" + run.outcome + " created=" + !!run.created + " stall=" + (run.stall_at || "-"));
  console.log("step1_filled_text:\n" + (run.step1_filled.body_text || "").slice(0, 500));
  console.log("FINAL:\n" + (run.final_text || "").slice(0, 700));
})().catch((e) => { console.error("MANUAL_FAIL " + e); process.exit(1); });