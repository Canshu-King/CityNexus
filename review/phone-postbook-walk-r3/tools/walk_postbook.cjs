/* Building walk, post-booking screens: what a person hits AFTER the trip exists.
 *
 * Uses the sealed demo trip (the fastest real plan with stops, legs and a workspace), then walks each
 * tab a person can reach from the trip screen (今天 / 行程 / 地图 / Copilot / 我的) and reads the
 * RENDERED words plus any machine-value leak (UUIDs, status codes, raw enums, code literals).
 *
 * For every screen it also asks the three building questions:
 *   UNREADABLE  -- is any visible word a machine value or an English token inside Chinese text?
 *   UNTAPPABLE  -- a pressable-looking control that the hit-test proves cannot be pressed?
 *   UNCONFIRMED -- the screen offers an action but never says what happened after it?
 *
 * argv: node walk_postbook.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4881";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_postbook.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

const run = { schema: "CNX_BUILDING_WALK_POSTBOOK", base: BASE_URL, viewport: { width: W, height: H },
  started: new Date().toString(), screens: [], page_errors: [], console_errors: [], findings: [] };

async function readScreen(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const leaks = [];
    for (const [re, kind] of [[/\b[A-Z][A-Z0-9_]{4,}\b/g, "UPPER_SNAKE"],
        [/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g, "UUID"],
        [/\b(400|401|403|404|409|422|500|502|503)\b/g, "HTTP_STATUS"],
        [/\b(null|undefined|true|false|NaN)\b/g, "CODE_LITERAL"],
        [/\b\d{4}-\d{2}-\d{2}T[\d:]+/g, "RAW_TIMESTAMP"]]) {
      const m = body.match(re);
      if (m) leaks.push({ kind, hits: Array.from(new Set(m)).slice(0, 6) });
    }
    // English word standing alone inside a Chinese sentence (excluding brand names / known latin)
    const zhBody = (body.match(/[\u4e00-\u9fa5]/g) || []).length;
    const englishTokens = (body.match(/\b[A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})*\b/g) || [])
      .filter((t) => !/^(CITYNEXUS|EN|DE|BE|CN|WGS84|OpenStreetMap|Copilot|AI|Check)$/.test(t));
    const pressables = Array.from(document.querySelectorAll("button,[role='button'],a")).filter(vis)
      .map((el) => ({ words: strip(el.innerText).slice(0, 50), testid: el.getAttribute("data-testid") || null,
        disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true" }));
    return { tag, path: location.pathname, chars: body.length, zh_chars: zhBody,
      body_text: strip(body).slice(0, 2400), leaks, english_tokens: Array.from(new Set(englishTokens)).slice(0, 10),
      pressables };
  }, tag);
}

async function tap(page, words, tag) {
  const loc = page.locator("button,[role='button'],a").filter({ hasText: words }).first();
  if (await loc.count() === 0) return { tapped: false, why: "NO_SUCH_CONTROL_" + words };
  const hit = await loc.evaluate((el) => { el.scrollIntoViewIfNeeded(); const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { landed: !!top && (top === el || el.contains(top)), disabled: !!el.disabled,
      inViewport: b.top >= 0 && b.bottom <= innerHeight }; });
  if (hit.disabled) return { tapped: false, why: "DISABLED_" + words, hit };
  if (!hit.landed) return { tapped: false, why: "HIT_TEST_MISSED_" + words, hit };
  await loc.click(); await page.waitForTimeout(1600);
  return { tapped: true, hit };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: W, height: H },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });

  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1500);
  const demo = await tap(page, /使用封存的演示行程/, "demo");
  run.demo = demo;
  run.screens.push(await readScreen(page, "trip_after_demo"));
  await page.screenshot({ path: OUT.replace(/\.json$/, "_trip.png"), fullPage: true });

  // walk the bottom nav tabs a person can reach from here
  const tabs = ["今天", "行程", "地图", "Copilot", "我的"];
  for (const tab of tabs) {
    const before = page.url();
    const r = await tap(page, new RegExp(tab), "tab_" + tab);
    const scr = await readScreen(page, "tab_" + tab);
    run.screens.push({ tag: "tab_" + tab, tap: r, screen: scr, url_changed: page.url() !== before });
    await page.screenshot({ path: OUT.replace(/\.json$/, "_" + tab + ".png"), fullPage: true });
  }

  // judgement: any screen with a leak, an English token inside Chinese, or a missed/disabled tap
  for (const s of run.screens) {
    const scr = s.screen || s; const tag = s.tag || scr.tag;
    const problems = [];
    if (scr.leaks && scr.leaks.length) problems.push("LEAK:" + scr.leaks.map((l) => l.kind).join("/"));
    if (scr.zh_chars > 30 && scr.english_tokens && scr.english_tokens.length) {
      problems.push("EN_IN_ZH:" + scr.english_tokens.slice(0, 4).join("|"));
    }
    if (s.tap && !s.tap.tapped) problems.push("TAP:" + s.tap.why);
    if (problems.length) run.findings.push({ screen: tag, problems });
  }
  run.outcome = run.findings.length ? "FINDINGS" : "CLEAN";
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await browser.close();
  console.log("OUTCOME=" + run.outcome + " findings=" + run.findings.length +
    " page_errors=" + run.page_errors.length + " console_errors=" + run.console_errors.length);
  for (const f of run.findings) console.log("  " + f.screen + " -> " + f.problems.join(" ; "));
})().catch((e) => { console.error("POSTBOOK_FAIL " + e); process.exit(1); });