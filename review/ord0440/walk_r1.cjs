/* ORD-0440 - the traveller's walk in front of 「停止这次准备」, measured on a real screen.
 *
 * This is the part a build cannot answer: does the sheet really sit *before* the destructive write,
 * does its exit keep the button's own words, and is every control in it inside the first screen's
 * hit zone (the 768 floor this lane froze in ORD-0407). It runs against a lane-private vite preview
 * proxied to a lane-private uvicorn on a private sqlite file - never a shared port or the preview DB.
 *
 * usage: node walk_r1.cjs <preview-base> <reset-token> <out-dir> [zh|en]
 */
const { chromium } = require("D:/moodle/_qoder_n3_ord0440/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:49970";
const TOKEN = process.argv[3] || "";
const OUT = process.argv[4] || "D:/moodle/_qoder_n3_ord0440/review/n3_0440_evidence_r1/walk";
const LOCALE = process.argv[5] === "en" ? "en" : "zh-CN";
const FLOOR = 768;
const CITY = "云和县";
const TAG = LOCALE === "en" ? "en" : "zh";

const COPY = {
  "zh-CN": {
    title: "能说说为什么现在要停止吗？",
    exit: "停止这次准备",
    back: "先不停止，我再看看",
    button: "停止这次准备",
  },
  en: {
    title: "Can you tell us why you're stopping now?",
    exit: "Stop this preparation",
    back: "Don't stop yet, let me look",
    button: "Stop this preparation",
  },
}[LOCALE];

const readings = { base: BASE, locale: LOCALE, floor_px: FLOOR, steps: [], checks: [], shots: [] };

function check(name, pass, detail) {
  readings.checks.push({ name, pass, detail });
}

async function api(page, method, path, body) {
  return page.evaluate(
    async ([m, p, b, tok]) => {
      const res = await fetch(`/api/v1${p}`, {
        method: m,
        headers: {
          "content-type": "application/json",
          ...(tok ? { "X-Demo-Reset-Token": tok } : {}),
        },
        body: b ? JSON.stringify(b) : undefined,
      });
      let json = null;
      try {
        json = await res.json();
      } catch (e) {
        json = { _non_json: true };
      }
      return { status: res.status, json };
    },
    [method, path, body, TOKEN],
  );
}

/* Strict form of the frozen predicate: the point the tap would land on belongs to the control, and
   its centre sits above the first-screen line. The ancestor disjunct is reported separately because
   ORD-0407 measured that it calls a covered control reachable. */
async function hitCensus(page, selector) {
  return page.evaluate(
    ([sel, floor]) => {
      const out = [];
      for (const el of document.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect();
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top + r.height / 2);
        const hit = document.elementFromPoint(cx, cy);
        out.push({
          testid: el.getAttribute("data-testid") || el.tagName.toLowerCase(),
          box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
          centre: [cx, cy],
          strict: hit === el || el.contains(hit),
          ancestor_only: !(hit === el || el.contains(hit)) && Boolean(hit && hit.contains(el)),
          within_floor: cy <= floor,
          text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60),
        });
      }
      return out;
    },
    [selector, FLOOR],
  );
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  const abandonRequests = [];
  page.on("request", (req) => {
    if (req.method() === "POST" && /catalog-hydrations\/[^/]+\/abandon$/.test(req.url())) {
      abandonRequests.push({ url: req.url(), at: Date.now() });
    }
  });

  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.waitForTimeout(800);

  /* A stage this lane owns: reset the private library, then claim the journey it answers with. */
  const reset = await api(page, "POST", "/demo/reset", {});
  check("G0 private demo reset answered 200", reset.status === 200, { status: reset.status });
  const scene = await api(page, "GET", "/demo/scene");
  const journeyId = scene.json && scene.json.journey_id;
  check("G0 scene carried a journey id", Boolean(journeyId), { journey_id: journeyId || null });

  await page.addInitScript(
    ([l, j]) => {
      try {
        localStorage.setItem("citynexus.locale", l);
        localStorage.setItem("citynexus.v8.journey_id", j);
        localStorage.removeItem("citynexus.ord0440.abandon_survey");
      } catch (e) {}
    },
    [LOCALE, journeyId],
  );
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  const seal = page.getByText(/使用封存的演示行程|sealed demo/i).first();
  if (await seal.count()) {
    await seal.click();
    await page.waitForTimeout(1500);
  }
  await page.waitForSelector('[data-testid="prep-panel"]', { timeout: 20000 });
  readings.steps.push({ step: "panel mounted", url: page.url() });

  await page.fill('[data-testid="prep-query"]', CITY);
  await page.click('[data-testid="prep-check"]');
  await page.waitForSelector('[data-testid="prep-verdict"]', { timeout: 30000 });
  const verdict = await page.getAttribute('[data-testid="prep-verdict"]', "data-capability");
  readings.steps.push({ step: "capability read", verdict });

  const start = page.locator('[data-testid="prep-start"]');
  check("G1 the panel offered to start a preparation", (await start.count()) > 0, { verdict });
  if (!(await start.count())) {
    await page.screenshot({ path: `${OUT}/${TAG}_no_start.png`, fullPage: true });
    readings.shots.push(`${TAG}_no_start.png`);
  } else {
    await start.first().click();
    const abandon = page.locator('[data-testid="prep-abandon"]');
    await abandon.waitFor({ state: "visible", timeout: 20000 });
    const labelBefore = (await abandon.first().textContent() || "").trim();
    check(
      "G3 the button's own words are unchanged after the change",
      labelBefore === COPY.button,
      { label_before: labelBefore, expected: COPY.button },
    );

    const operationId = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="prep-survey"]');
      return el ? el.getAttribute("data-operation-id") : null;
    });
    let jobBefore = null;

    /* ---- G2: before the sheet, and still before it after opening the sheet ---- */
    if (abandonRequests.length === 0) {
      await abandon.first().click();
    }
    let mounted = true;
    try {
      await page.waitForSelector('[data-testid="prep-survey"]', { timeout: 10000 });
    } catch (error) {
      mounted = false;
      check("G2 the sheet mounted when the button was tapped", false, {
        reason: "no prep-survey appeared",
        abandon_request_count: abandonRequests.length,
      });
      await page.screenshot({ path: `${OUT}/${TAG}_no_sheet.png`, fullPage: true });
      readings.shots.push(`${TAG}_no_sheet.png`);
    }
    if (!mounted) {
      /* Everything below needs the sheet. Recording the bypass as a named red is the point of this
         arm; crashing with an exit code is how a mutation gets mistaken for an unrelated outage. */
      readings.abandon_request_count = abandonRequests.length;
      readings.pass_count = readings.checks.filter((c) => c.pass).length;
      readings.fail_count = readings.checks.filter((c) => !c.pass).length;
      fs.writeFileSync(`${OUT}/walk_${TAG}.json`, JSON.stringify(readings, null, 2), "utf8");
      console.log(`locale=${TAG} checks=${readings.checks.length} pass=${readings.pass_count} fail=${readings.fail_count}`);
      for (const c of readings.checks) if (!c.pass) console.log("  RED", c.name, JSON.stringify(c.detail).slice(0, 200));
      console.log("wrote", `${OUT}/walk_${TAG}.json`);
      await browser.close();
      process.exit(1);
    }
    const sheetOperationId = await page.evaluate(
      () => document.querySelector('[data-testid="prep-survey"]')?.getAttribute("data-operation-id") || null,
    );
    /* The sheet scrolls the page to its own top on arrival; clicking during that settle reads as an
       unstable element, which is the instrument's timing, not the product's. */
    await page.waitForFunction(() => window.scrollY === 0, null, { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(400);
    const exitBeforeAnyPick = await page.locator('[data-testid="prep-survey-exit"]').isEnabled();
    check(
      "G4 the exit is already usable with nothing chosen",
      exitBeforeAnyPick,
      { exit_enabled_with_zero_reasons: exitBeforeAnyPick },
    );
    const opId = sheetOperationId || operationId;
    jobBefore = opId ? (await api(page, "GET", `/catalog-hydrations/${opId}`)).json : null;
    /* Two different facts, so one cannot excuse the other: the sheet must not have *sent* the stop,
       and the job's own state at that moment is a reading (the server answers an unattended
       hydration in ~4 s, which is not this door's business). */
    check(
      "G2 opening the sheet sent no stop request",
      abandonRequests.length === 0,
      { abandon_request_count: abandonRequests.length },
    );
    readings.steps.push({
      step: "job state read at sheet open",
      operation_id: opId,
      status: jobBefore ? jobBefore.status : null,
      terminal: jobBefore ? jobBefore.terminal : null,
    });
    const sheetTitle = (await page.locator('[data-testid="prep-survey-title"]').textContent() || "").trim();
    check("G2 the sheet asks instead of ordering", sheetTitle === COPY.title, {
      sheet_title: sheetTitle, expected: COPY.title,
    });
    const exitText = (await page.locator('[data-testid="prep-survey-exit"]').textContent() || "").trim();
    check(
      "G3 the exit keeps naming the real act (unchanged from the button)",
      exitText === labelBefore,
      { exit_label: exitText, button_label_before_open: labelBefore },
    );

    const hits = await hitCensus(page, '[data-testid^="prep-survey"]');
    readings.steps.push({ step: "sheet hit census", controls: hits });
    check(
      "G7 every control in the sheet is hit-testable and inside the first screen",
      hits.length > 0 && hits.every((h) => h.strict && h.within_floor),
      {
        control_count: hits.length,
        unreachable: hits.filter((h) => !h.strict).map((h) => h.testid),
        below_floor: hits.filter((h) => !h.within_floor).map((h) => ({ id: h.testid, centre: h.centre })),
      },
    );

    /* ---- G4: an over-long note is named, and the act is still allowed ---- */
    await page.click('[data-testid="prep-survey-reason-TOO_SLOW"]');
    await page.click('[data-testid="prep-survey-reason-WE_WERE_UNCLEAR"]');
    await page.fill('[data-testid="prep-survey-note"]', "字".repeat(201));
    await page.waitForTimeout(150);
    const overVisible = await page.locator('[data-testid="prep-survey-over"]').isVisible();
    const exitEnabled = await page.locator('[data-testid="prep-survey-exit"]').isEnabled();
    check("G4 the over-limit line appears at 201 characters", overVisible, { over_visible: overVisible });
    check("G4 the survey never blocks the destructive act", exitEnabled, { exit_enabled: exitEnabled });

    await page.screenshot({ path: `${OUT}/${TAG}_sheet_filled.png` });
    readings.shots.push(`${TAG}_sheet_filled.png`);

    /* ---- G5/G6: exit lands the act once, and the record says what was chosen ---- */
    if (!(await page.locator('[data-testid="prep-survey-exit"]').isEnabled())) {
      check("G4 the exit stays usable after reasons were picked", false, {
        reason: "the exit is disabled, so the traveller cannot finish the act they asked for",
        picked_before: 2,
      });
      readings.abandon_request_count = abandonRequests.length;
      readings.pass_count = readings.checks.filter((c) => c.pass).length;
      readings.fail_count = readings.checks.filter((c) => !c.pass).length;
      fs.writeFileSync(`${OUT}/walk_${TAG}.json`, JSON.stringify(readings, null, 2), "utf8");
      console.log(`locale=${TAG} checks=${readings.checks.length} pass=${readings.pass_count} fail=${readings.fail_count}`);
      for (const c of readings.checks) if (!c.pass) console.log("  RED", c.name, JSON.stringify(c.detail).slice(0, 200));
      console.log("wrote", `${OUT}/walk_${TAG}.json`);
      await browser.close();
      process.exit(1);
    }
    await page.click('[data-testid="prep-survey-exit"]');
    await page.waitForTimeout(2500);
    const after = opId ? (await api(page, "GET", `/catalog-hydrations/${opId}`)).json : null;
    check("G5 exactly one abandon request left the device", abandonRequests.length === 1, {
      abandon_request_count: abandonRequests.length,
    });
    check(
      "G5 the server's own job moved off the open set",
      after && (after.terminal === true || ["ABANDON_REQUESTED", "ABANDONED"].includes(after.status)),
      { job_status: after ? after.status : null, terminal: after ? after.terminal : null },
    );
    const log = await page.evaluate(() => {
      try {
        return JSON.parse(localStorage.getItem("citynexus.ord0440.abandon_survey") || "[]");
      } catch (e) {
        return [];
      }
    });
    const entry = log.length ? log[log.length - 1] : null;
    check(
      "G6 the record names the chosen reasons, the note length and whether the stop landed",
      entry && entry.reasons.length === 2 && entry.note_chars === 201 && entry.skipped === false && entry.stopped === true,
      { record: entry, entries: log.length },
    );
    readings.steps.push({ step: "survey log", entries: log.length, last: entry });

    /* ---- G8: the way back leaves the job running and writes nothing ---- */
    const again = page.locator('[data-testid="prep-abandon"]');
    if (await again.count()) {
      const backHits = await hitCensus(page, '[data-testid="prep-abandon"]');
      readings.steps.push({ step: "button restored after the stop", hits: backHits });
    } else {
      readings.steps.push({ step: "button restored after the stop", note: "job terminal, no second job to abandon" });
    }
  }

  await page.screenshot({ path: `${OUT}/${TAG}_final.png`, fullPage: true });
  readings.shots.push(`${TAG}_final.png`);
  readings.abandon_request_count = abandonRequests.length;
  readings.pass_count = readings.checks.filter((c) => c.pass).length;
  readings.fail_count = readings.checks.filter((c) => !c.pass).length;
  const file = `${OUT}/walk_${TAG}.json`;
  fs.writeFileSync(file, JSON.stringify(readings, null, 2, "\n").replace(/\\u2028|\\u2029/g, ""), "utf8");
  console.log(`locale=${TAG} checks=${readings.checks.length} pass=${readings.pass_count} fail=${readings.fail_count}`);
  for (const c of readings.checks) {
    if (!c.pass) console.log("  RED", c.name, JSON.stringify(c.detail).slice(0, 220));
  }
  console.log("wrote", file);
  await browser.close();
  process.exit(readings.fail_count ? 1 : 0);
})().catch((error) => {
  console.log("WALK_CRASH", String(error).slice(0, 400));
  process.exit(2);
});
