/**
 * ORD-0263 A3: does a write leg that never settles make the screen tell the same lie?
 *
 * Real clicks on the real production bundle, against a real origin that accepts POSTs and never
 * answers them. Nothing here mocks the network: the wizard is filled and submitted the way a
 * traveller fills it, then this reader samples what the screen says -- every second, plus once more
 * after the traveller uses the screen's own "停止等待" door.
 *
 * Two findings must stay distinguishable, so both are recorded separately:
 *   - the screen stays silent (a stuck promise, no sentence) -> not a false attribution;
 *   - the screen blames the network / the origin -> it speaks falsely, same family as the fifth state.
 *
 * usage: node q263_a3_leg.js --url U --profile DIR --out FILE [--seconds 35]
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);

function arg(name, dflt) {
  const i = process.argv.indexOf("--" + name);
  if (i === -1) return dflt;
  const next = process.argv[i + 1];
  return next === undefined || next.startsWith("--") ? true : next;
}

const text = async (page, sel) => {
  if ((await page.locator(sel).count().catch(() => 0)) === 0) return "";
  return ((await page.locator(sel).first().innerText({ timeout: 800 }).catch(() => "")) || "").trim();
};

(async () => {
  const url = arg("url", "http://127.0.0.1:4441/v8/hub");
  const profile = arg("profile");
  const out = arg("out");
  const seconds = Number(arg("seconds", "35"));
  const ctx = await chromium.launchPersistentContext(profile, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const writes = [];
  const settled = [];
  page.on("request", (r) => {
    if (r.method() !== "GET" && r.url().includes("/api/")) {
      writes.push({ method: r.method(), url: r.url().replace(/^https?:\/\/[^/]+/, ""), at: Date.now() });
    }
  });
  page.on("response", (r) => {
    if (r.request().method() !== "GET") settled.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ""), status: r.status() });
  });

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 }).catch((e) => e.message);
  for (let i = 0; i < 40 && !(await page.locator('[data-testid="trial-setup"]').count()); i += 1) {
    await page.waitForTimeout(250);
  }
  // the wizard is the first screen with no journey id; if a shell is up instead, open it by its control
  if (!(await page.locator('[data-testid="trial-setup"]').count())) {
    const open = page.locator('button:has-text("新建行程")').first();
    if (await open.count()) await open.click().catch(() => {});
    await page.waitForTimeout(1200);
  }

  const fillLog = [];
  async function fill(testid, value) {
    const loc = page.locator(`[data-testid="${testid}"]`).first();
    const exists = await loc.count();
    let before = "", after = "";
    if (exists) {
      before = await loc.inputValue().catch(() => "READ_FAILED");
      await loc.fill(value).catch((e) => e.message);
      after = await loc.inputValue().catch(() => "READ_FAILED");
    }
    fillLog.push({ testid, present: Boolean(exists), before, typed: value, after });
  }
  await fill("trial-city", "北京");
  await page.waitForTimeout(700);
  await fill("trial-arrival", "北京南站");
  await fill("trial-departure", "北京南站");
  await page.waitForTimeout(400);

  const stepLog = [];
  for (const testid of ["trial-next", "trial-next"]) {
    const hintBefore = await text(page, '[data-testid="trial-required-hint"]');
    const btn = page.locator(`[data-testid="${testid}"]`).first();
    const pressed = (await btn.count()) > 0;
    if (pressed) await btn.click({ timeout: 3000 }).catch((e) => stepLog.push({ click_error: String(e).slice(0, 90) }));
    await page.waitForTimeout(900);
    stepLog.push({
      pressed, testid, hint_before_click: hintBefore,
      hint_after_click: await text(page, '[data-testid="trial-required-hint"]'),
      live: await text(page, '[aria-live]').catch(() => ""),
      step_body_present: {
        step1: await page.locator('[data-testid="trial-step1-body"]').count(),
        step2: await page.locator('[data-testid="trial-step2-body"]').count(),
        step3: await page.locator('[data-testid="trial-step3-body"]').count(),
      },
    });
  }

  const createBtn = page.locator('[data-testid="trial-create"]').first();
  const createPresent = await createBtn.count();
  const createState = createPresent ? {
    aria_disabled: await createBtn.getAttribute("aria-disabled"),
    disabled: await createBtn.isDisabled().catch(() => null),
    label: await createBtn.innerText({ timeout: 800 }).catch(() => ""),
  } : null;
  if (createPresent) await createBtn.click({ timeout: 3000 }).catch((e) => stepLog.push({ create_click_error: String(e).slice(0, 90) }));

  const t0 = Date.now();
  const samples = [];
  let stopped = null;
  while (Date.now() - t0 < seconds * 1000) {
    const s = {
      elapsed_s: Number(((Date.now() - t0) / 1000).toFixed(1)),
      body: (await text(page, "main")) || (await text(page, "body")),
      live: await text(page, '[aria-live="polite"]'),
      wait_outcome: await text(page, '[data-testid="trial-wait-outcome"]'),
      create_error: await text(page, '[data-testid="trial-create-error"]'),
      nodes: {
        "trial-setup": await page.locator('[data-testid="trial-setup"]').count(),
        "failure-view": await page.locator('[data-testid="failure-view"]').count(),
        "today-heading": await page.locator('[data-testid="today-heading"]').count(),
        "load-failed": await page.locator('[data-testid="load-failed"]').count(),
        "offline-retry": await page.locator('[data-testid="offline-retry"]').count(),
        "backend-unreachable": await page.locator('[data-testid="backend-unreachable"]').count(),
      },
      stop_button: await page.locator('button:has-text("停止等待")').count(),
      attribution_last: await page.evaluate(() => {
        const rows = Array.isArray(window.citynexusAttribution) ? window.citynexusAttribution : null;
        return rows && rows.length ? rows[rows.length - 1] : null;
      }),
    };
    samples.push(s);
    // once the screen offers its own way out, use it and record what it then says
    if (!stopped && s.stop_button > 0 && s.elapsed_s > 8) {
      const btn = page.locator('button:has-text("停止等待")').first();
      const box = await btn.boundingBox().catch(() => null);
      const hit = box ? await page.evaluate(([x, y]) => {
        const el = document.elementFromPoint(x, y);
        return el ? (el.closest("button") ? (el.closest("button").innerText || "").trim().slice(0, 30) : el.tagName) : "NONE";
      }, [box.x + box.width / 2, box.y + box.height / 2]) : null;
      await btn.click({ timeout: 2500 }).catch((e) => { stopped = { click_error: String(e).slice(0, 90) }; });
      await page.waitForTimeout(2000);
      stopped = {
        clicked_at_s: s.elapsed_s, hit_test: hit,
        after_body: (await text(page, "main")) || (await text(page, "body")),
        after_wait_outcome: await text(page, '[data-testid="trial-wait-outcome"]'),
        after_live: await text(page, '[aria-live="polite"]'),
        after_create_error: await text(page, '[data-testid="trial-create-error"]'),
        after_nodes: s.nodes,
      };
      samples.push({ elapsed_s: s.elapsed_s + 2, after_stop: true, body: stopped.after_body });
      break;
    }
    await page.waitForTimeout(1000);
  }

  const uniqSentences = [];
  for (const s of samples) {
    for (const line of (s.body || "").split("\n").map((x) => x.trim()).filter(Boolean)) {
      if (!uniqSentences.includes(line)) uniqSentences.push(line);
    }
  }
  const LIE = /网络不可用|没能出去|没有收到任何回答|服务(暂时)?不可用|离线/;
  const result = {
    label: "A3_write_leg_hangs", at: new Date().toISOString(), url, seconds,
    render_shape: "persistent context, phone 390x844 zh-CN, real clicks on the production bundle",
    fills: fillLog, steps: stepLog, create_button: createState,
    writes_seen: writes, write_responses_settled: settled,
    stop_waiting_used: stopped,
    sentences_ever_on_screen: uniqSentences,
    ever_blamed_network_or_origin: uniqSentences.some((x) => LIE.test(x)),
    phase_lines_seen: [...new Set(samples.map((s) => s.wait_outcome).filter(Boolean))],
    attribution_samples: samples.map((s) => s.attribution_last).filter(Boolean),
    sample_count: samples.length,
    samples,
  };
  fs.writeFileSync(out, JSON.stringify(result, null, 1), "utf8");
  console.log(`A3: writes=${writes.map((w) => w.method + " " + w.url).join(",") || "none"} `
    + `settled=${settled.length} blames_network=${result.ever_blamed_network_or_origin} `
    + `phases=${JSON.stringify(result.phase_lines_seen).slice(0, 60)} stop=${stopped ? "used" : "never offered"} -> ${path.basename(out)}`);
  await ctx.close();
})().catch((e) => { console.error("A3 READER THREW: " + (e && e.stack || e)); process.exit(9); });
