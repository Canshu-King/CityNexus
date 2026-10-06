/* Is 「AI 帮我规划」 a real pressable control on the trip screen? Find it, hit-test it, press it, and read
 * what the screen says afterwards. The previous walk reported TELLABLE without ever pressing it (the
 * selector missed), so this one proves the press landed before it judges anything. */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");
const OUT = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_aiplan_press.json";
(async () => {
  const run = { schema: "CNX_BUILDING_WALK_AIPLAN_PRESS", started: new Date().toString(),
    steps: [], page_errors: [], console_errors: [], api: [] };
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  p.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });
  p.on("response", async (r) => {
    const u = r.url();
    if (/\/(plans|extract|intake|agent)/.test(u) && !u.includes("/assets/")) {
      let d = ""; try { d = (await r.text()).slice(0, 200); } catch (e) {}
      run.api.push({ url: u.replace(/[0-9a-f-]{36}/g, "<id>"), method: r.request().method(), status: r.status(), detail: d });
    }
  });
  const snap = (tag) => p.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const bb = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return bb.width > 0 && bb.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const all = Array.from(document.querySelectorAll("button,[role='button'],a")).filter(vis)
      .map((el) => ({ tag: el.tagName, words: strip(el.innerText).slice(0, 40), testid: el.getAttribute("data-testid") || null,
        disabled: !!el.disabled }));
    return { tag, chars: body.length, body_text: strip(body).slice(0, 2400), controls: all,
      spinner: Array.from(document.querySelectorAll(".v8-spinner,[aria-busy='true']")).filter(vis).length };
  }, tag);

  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  const demo = p.locator("button").filter({ hasText: /使用封存的演示行程/ }).first();
  if (await demo.count()) { await demo.click(); await p.waitForTimeout(2500); }
  const before = await snap("before_ai");
  run.steps.push(before);
  // list every control so the AI one is identified by what is actually there
  console.log("CONTROLS:");
  for (const c of before.controls) console.log("  " + c.tag + " " + JSON.stringify(c.words) + " testid=" + c.testid + " disabled=" + c.disabled);

  // find the AI control by its words, then hit-test and press it
  const aiInfo = await p.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const els = Array.from(document.querySelectorAll("button,[role='button'],a"))
      .filter((el) => /AI\s*帮我规划|帮我规划/.test(strip(el.innerText)));
    const el = els[0];
    if (!el) return { found: false };
    el.scrollIntoViewIfNeeded();
    const bb = el.getBoundingClientRect();
    const cx = bb.left + bb.width / 2, cy = bb.top + bb.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return { found: true, tag: el.tagName, words: strip(el.innerText), disabled: !!el.disabled,
      cx, cy, w: bb.width, h: bb.height, landed: !!top && (top === el || el.contains(top)) };
  });
  run.ai_control = aiInfo;
  let pressed = false;
  if (aiInfo.found && !aiInfo.disabled) {
    await p.mouse.click(aiInfo.cx, aiInfo.cy);
    pressed = true;
    run.pressed = true;
    await p.waitForTimeout(7000);
  } else { run.pressed = false; }
  const after = await snap("after_ai");
  run.steps.push(after);
  await p.screenshot({ path: OUT.replace(/\.json$/, "_after.png"), fullPage: true });
  run.after_text = after.body_text;
  run.spinner_after = after.spinner;
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await b.close();
  console.log("AI_CONTROL=" + JSON.stringify(aiInfo));
  console.log("PRESSED=" + pressed + " spinner_after=" + after.spinner);
  console.log("POST_STATE_TEXT:\n" + after.body_text.slice(0, 500));
})().catch((e) => { console.error("AIPRESS_FAIL " + e); process.exit(1); });