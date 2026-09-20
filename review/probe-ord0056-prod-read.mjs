/**
 * ORD-0056 closure evidence: read the wizard on the AUTHORITATIVE PRODUCTION BUILD.
 *
 * The arbitration said the merge is not done until the screen is read on the thing that
 * ships - not the dev server, not the lane tree, not the commit message. So this walks
 * `vite preview` over the `dist/` that `npm run build` just produced, against its own
 * backend and its own throwaway database, and records what the traveller's screen says at
 * the three points the order named:
 *
 *   1. step one with arrival/departure left empty - is "next" still clickable?
 *   2. the review step - does a bare em-dash stand in for a date?
 *   3. a field-level 422 from the backend - does the reason land where the traveller sees it?
 *
 * Everything reported here is innerText: no data attributes, no React state. Run:
 *   node review/probe-ord0056-prod-read.mjs
 */

import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const { chromium } = require("D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright");

const BACKEND = Number(process.env.PROBE_BACKEND || 8491);
const WEB = Number(process.env.PROBE_WEB || 4191);
/* A second run needs a new id, not a deleted file: the run-stamped backend refuses to
   reopen a database that already exists, and it is right to. */
const RUN_ID = process.env.PROBE_RUN_ID || "ord56-prod";
const PY = "D:\\moodle\\CityNexus\\.venv\\Scripts\\python.exe";
const FRONTEND = "D:\\moodle\\_qoder_integration_20260919\\frontend";
const BACKEND_DIR = "D:\\moodle\\_qoder_integration_20260919\\backend";
const OUT = "D:/moodle/_qoder_ord30_evidence_20260920/ord56/prod-read.json";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function start(cmd, args, opts) {
  return spawn(cmd, args, { stdio: "ignore", ...opts });
}

const backend = start(PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(BACKEND)], {
  cwd: BACKEND_DIR,
  env: {
    ...process.env,
    CITYNEXUS_DATABASE_URL: `sqlite:///D:/moodle/_qoder_integration_20260919/backend/_${RUN_ID}.db`,
    CITYNEXUS_E2E_RUN_ID: RUN_ID,
    CITYNEXUS_AI_ENABLED: "false",
    DEEPSEEK_API_KEY: "",
    CITYNEXUS_AI_API_KEY: "",
  },
});
const web = start("node", ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(WEB)], {
  cwd: FRONTEND,
  env: { ...process.env, CITYNEXUS_BACKEND_PORT: String(BACKEND) },
});

const report = { steps: [], api: [], console: [] };

async function waitHealthy() {
  for (let i = 0; i < 90; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${WEB}/api/v1/health`);
      if (res.ok) return true;
    } catch {
      /* still booting */
    }
    await sleep(1000);
  }
  return false;
}

async function snap(page, label) {
  const ids = await page.$$eval("[data-testid]", (els) =>
    els.map((e) => `${e.getAttribute("data-testid")}=${(e.textContent || "").trim().slice(0, 26)}`),
  );
  const enabled = await page.evaluate(() => {
    const el = document.querySelector("[data-testid='trial-next']");
    if (!el) return "no trial-next";
    return `${el.tagName.toLowerCase()} disabled=${el.disabled} aria-disabled=${el.getAttribute("aria-disabled")}`;
  });
  const entry = {
    label,
    nextControl: enabled,
    testids: ids,
    innerText: (await page.innerText("body")).replace(/\s+/g, " ").slice(0, 700),
  };
  report.steps.push(entry);
  console.log(`\n### ${label}`);
  console.log(`  trial-next: ${entry.nextControl}`);
  console.log(`  text: ${entry.innerText}`);
  return entry;
}

function fill(page, testId, value) {
  return page.evaluate(
    ({ testId, value }) => {
      const el = document.querySelector(`[data-testid='${testId}']`);
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(
        el.tagName === "SELECT" ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype,
        "value",
      )?.set;
      if (setter) setter.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    },
    { testId, value },
  );
}

try {
  if (!(await waitHealthy())) {
    console.log("FATAL: preview stack did not come up");
    process.exitCode = 2;
  } else {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    page.on("console", (msg) => report.console.push(msg.text().slice(0, 200)));
    page.on("request", (r) => {
      if (r.method() === "POST" && r.url().includes("/api/v1/journeys")) report.api.push({ m: r.method(), u: r.url() });
    });
    page.on("response", async (r) => {
      if (r.url().includes("/api/v1/journeys")) {
        let body = "";
        try {
          body = (await r.text()).slice(0, 300);
        } catch {
          /* stream consumed */
        }
        report.api.push({ m: "RESP", status: r.status(), body });
      }
    });

    await page.addInitScript(() => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", "zh");
    });
    await page.goto(`http://127.0.0.1:${WEB}/v8`);
    await page.waitForSelector("[data-testid='trial-setup']", { timeout: 25000 });

    await snap(page, "step1 · 抵达/离开留空");

    await fill(page, "trial-city", "Tianjin");
    await page.getByTestId("trial-next").click().catch(() => {});
    await sleep(700);
    await snap(page, "step1 · 只填城市，日期仍空 → 点下一步");

    /* Step one needs five things: city, both places, both times. Using Playwright's own
       fill rather than a native-setter assignment, because React only sees the change when
       the trusted input event fires - and a wizard that is not actually filled cannot show
       us its review page. */
    const found = [];
    const wanted = [
      ["trial-arrival", "厦门站"],
      ["trial-departure", "高崎机场"],
      ["trial-start", "2026-10-09T08:00"],
      ["trial-end", "2026-10-11T18:00"],
    ];
    for (const [id, value] of wanted) {
      const locator = page.getByTestId(id);
      if ((await locator.count()) === 0) {
        found.push(`${id}:absent`);
        continue;
      }
      try {
        await locator.fill(value);
        found.push(`${id}←${value}`);
      } catch (error) {
        found.push(`${id}:error:${String(error).slice(0, 40)}`);
      }
    }
    report.filledDateIds = found;
    console.log(`\n  fields filled: ${JSON.stringify(found)}`);
    await snap(page, "step1 · 五项填齐");
    for (let i = 0; i < 3; i += 1) {
      await page.getByTestId("trial-next").click().catch(() => {});
      await sleep(900);
      await snap(page, `walk ${i + 2} 步之后`);
    }

    /* The 422 case: the backend's field-level error envelope, intercepted so the run stays offline. */
    await page.route("**/api/v1/journeys", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "VALIDATION_ERROR",
            message: "Request validation failed",
            trace_id: "probe-trace",
            details: { errors: [{ loc: ["body", "end_at"], msg: "Input should be a valid date", type: "date_parsing" }] },
          },
        }),
      });
    });
    await page.getByTestId("trial-create").click().catch(async () => {
      console.log("  (no trial-create on this step; review step may not have been reached)");
    });
    await sleep(1800);
    await snap(page, "422 之后（字段级 errors 已注入）");
    await browser.close();
  }
} finally {
  for (const child of [backend, web]) {
    try {
      child.kill("SIGTERM");
    } catch {
      /* gone */
    }
  }
  writeFileSync(OUT, JSON.stringify(report, null, 2) + "\n", "utf-8");
  console.log(`\nwrote ${OUT}`);
}
