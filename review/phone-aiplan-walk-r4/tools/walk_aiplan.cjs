/* Building walk, AI-planning + Copilot: can a person start a plan, and can they TELL whether it worked?
 *
 * This stack runs with AI disabled, which is exactly the honest case for the "不知道成没成" class: when
 * planning cannot run, does the screen say so in words a person can act on -- or does it hang, show a
 * spinner forever, or report success while nothing was generated?
 *
 * It drives the real control (AI 帮我规划), reads the rendered words, waits for any change, and then
 * judges the outcome on THREE questions a person would ask:
 *   did it say it started?  did it say what happened?  can I tell success from failure?
 *
 * argv: node walk_aiplan.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4881";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_aiplan.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

const run = { schema: "CNX_BUILDING_WALK_AIPLAN", base: BASE_URL, viewport: { width: W, height: H },
  started: new Date().toString(), steps: [], page_errors: [], console_errors: [], api: [],
  verdict: null };

async function readScreen(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const buttons = Array.from(document.querySelectorAll("button,[role='button']")).filter(vis)
      .map((el) => ({ words: strip(el.innerText).slice(0, 40), testid: el.getAttribute("data-testid") || null,
        disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true" }));
    const alerts = Array.from(document.querySelectorAll("[role='alert'],[role='status'],.v8-alert,.v8-notice,.v8-error"))
      .filter(vis).map((el) => strip(el.innerText).slice(0, 200));
    const spinners = Array.from(document.querySelectorAll(".v8-spinner,[aria-busy='true']")).filter(vis).length;
    return { tag, chars: body.length, body_text: strip(body).slice(0, 2400), buttons, alerts, spinners };
  }, tag);
}

async function press(page, words) {
  const loc = page.locator("button,[role='button']").filter({ hasText: words }).first();
  if (await loc.count() === 0) return { pressed: false, why: "NO_SUCH_CONTROL_" + words };
  const hit = await loc.evaluate((el) => { el.scrollIntoViewIfNeeded(); const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { landed: !!top && (top === el || el.contains(top)), disabled: !!el.disabled }; });
  if (hit.disabled) return { pressed: false, why: "DISABLED_" + words, hit };
  if (!hit.landed) return { pressed: false, why: "HIT_TEST_MISSED_" + words, hit };
  await loc.click();
  return { pressed: true, hit };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: W, height: H },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });
  page.on("response", async (r) => {
    const u = r.url();
    if (/\/(plan|plans|extract|intake|agent|copilot)/.test(u) && !u.includes("/assets/")) {
      let detail = "";
      try { detail = (await r.text()).slice(0, 300); } catch (e) { /* body gone */ }
      run.api.push({ url: u.replace(/[0-9a-f-]{36}/g, "<id>"), status: r.status(), detail });
    }
  });

  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1500);
  const demo = await press(page, /使用封存的演示行程/);
  run.demo = demo;
  const before = await readScreen(page, "before_ai");
  run.steps.push(before);
  await page.screenshot({ path: OUT.replace(/\.json$/, "_before.png"), fullPage: true });

  // press the real planning control
  const ai = await press(page, /AI\s*帮我规划/);
  run.ai_press = ai;
  // give it time to either answer or visibly hang
  await page.waitForTimeout(6000);
  const after = await readScreen(page, "after_ai");
  run.steps.push(after);
  await page.screenshot({ path: OUT.replace(/\.json$/, "_after.png"), fullPage: true });
  await page.waitForTimeout(4000);
  const settled = await readScreen(page, "settled");
  run.steps.push(settled);
  await page.screenshot({ path: OUT.replace(/\.json$/, "_settled.png"), fullPage: true });

  // the three questions, answered from the rendered words
  const saidSomething = (s) => s.chars !== before.chars || s.body_text !== before.body_text;
  const q = {
    started_says_so: ai.pressed,
    screen_changed_after_press: saidSomething(after),
    says_what_happened: /没有|无法|不能|失败|拒绝|未配置|没开|不可用|需要|请先|稍后|重试|错误|不支持/.test(after.body_text),
    still_spinning_at_settle: settled.spinners > 0,
    // a person can tell success from failure if the screen carries EITHER a success sentence or a
    // refusal sentence -- silence after a press is the "不知道成没成" failure
    distinguishable: /生成|已创建|方案|候选|行程已|好了|完成/.test(settled.body_text)
      || /没有|无法|不能|失败|拒绝|未配置|没开|不可用|需要|请先|稍后|重试|错误|不支持/.test(settled.body_text),
  };
  run.questions = q;
  run.verdict = q.distinguishable && !q.still_spinning_at_settle ? "TELLABLE" : "UNTELLABLE";
  run.final_text = settled.body_text;
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await browser.close();
  console.log("VERDICT=" + run.verdict + " api_calls=" + run.api.length +
    " page_errors=" + run.page_errors.length + " console_errors=" + run.console_errors.length);
  console.log("questions=" + JSON.stringify(q));
  console.log("api=" + JSON.stringify(run.api.map((a) => a.url + " " + a.status)));
  console.log("SETTLED_TEXT:\n" + (settled.body_text || "").slice(0, 700));
})().catch((e) => { console.error("AIPLAN_FAIL " + e); process.exit(1); });