/**
 * ORD-0382 online self-verification -- the first reading of the shipped three-stage surface taken
 * from the live chain (127.0.0.1:4781), which now serves this order's own generation.
 *
 * Zero writes: the two mutating legs (`POST .../agent/commands`, `POST .../plans/generate`) are
 * answered inside this browser and never leave it -- the standing rule is no demo/reset and no touch
 * to `_preview.db`, and pressing 开始规划 on the real chain would otherwise create a mission and,
 * through the fallback leg, candidate plans on the only journey left.  Everything else -- the bundle
 * bytes, the shell reads, the sheet's baseline `/plans` read, the post-cancel read-back -- is the
 * real server answering for real.  So the numbers the waiting bar and the closing card speak are
 * online readings, not fixture rows.
 *
 * Assertions read `body.innerText`, per the commander's instruction.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = "http://127.0.0.1:4781";
const OUT = "D:/moodle/_qoder_q_ord0382_evidence/online";
mkdirSync(OUT, { recursive: true });
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const log = [];
const record = (step, data) => {
  log.push({ step, ...data });
  console.log(`\n### ${step}`);
  for (const [k, v] of Object.entries(data)) console.log(`  ${k} = ${typeof v === "string" ? v : JSON.stringify(v)}`);
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();

/* The withheld legs, counted so the receipt can state that neither ever reached the store. */
const withheld = { commands: 0, generates: 0 };
const forwarded = { reads: 0, writes: 0 };
page.on("request", (req) => {
  const u = new URL(req.url());
  if (!u.pathname.startsWith("/api/v1")) return;
  if (req.method() === "GET" || req.method() === "HEAD") forwarded.reads += 1;
  else if (!u.pathname.endsWith("/agent/commands") && !u.pathname.endsWith("/plans/generate")) forwarded.writes += 1;
});
/* Held open, then answered here. `abort()` would settle the leg in milliseconds and the waiting
   block would never be on screen to read; `{}` is the same answer the repo's own gate arm
   `plan-ai-cancel-aborts-request` gives, so this probe invents no fourth envelope. The request
   still never leaves the browser: the store sees no mission. */
await page.route("**/api/v1/journeys/*/agent/commands", async (route) => {
  withheld.commands += 1;
  await new Promise((r) => setTimeout(r, 25_000));
  try {
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  } catch {
    /* the traveller stopped waiting first, which is the state being measured */
  }
});
await page.route("**/api/v1/journeys/*/plans/generate", (route) => {
  withheld.generates += 1;
  void route.fulfill({
    status: 422,
    contentType: "application/json",
    body: JSON.stringify({ error: { code: "MOBILITY_DATA_UNAVAILABLE", message: "withheld by the ORD-0382 online probe" } }),
  });
});

const painted = async (testId) => {
  const loc = page.getByTestId(testId).first();
  if (!(await loc.count())) return null;
  return (await loc.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
};
const shot = async (name) => {
  const path = `${OUT}/${name}.png`;
  await page.screenshot({ path });
  return path;
};

/* --- 0. is this generation really the one on the wire? ------------------------------- */
await page.goto(`${BASE}/v8`, { waitUntil: "load" });
await page.waitForTimeout(1500);
const bundleProbe = await page.evaluate(async () => {
  const src = Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src"));
  const hits = {};
  for (const url of src) {
    const text = await (await fetch(url)).text();
    hits[url] = {
      bytes: new Blob([text]).size,
      run_strip: (text.match(/plan-ai-run-strip/g) || []).length,
      view_chat: (text.match(/去看会话/g) || []).length,
      no_day_signal: (text.match(/不按天报/g) || []).length,
      aftermath: (text.match(/plan-ai-aftermath/g) || []).length,
    };
  }
  return hits;
});
record("0-deployed-generation", {
  scripts: Object.keys(bundleProbe).length,
  probe: bundleProbe,
  body_head: (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 120),
  screenshot: await shot("00-online-entry"),
});

/* --- 1. reach Today on the only journey the chain has, then open the sheet ----------- */
/* If the shell wants a journey it asks for one: the sealed-demo entry is a read-only adoption
   (ORD-0209 removed its POST), and the write counter below is what proves that claim rather than
   repeating it. */
if (await page.getByTestId("trial-setup").count()) {
  const btn = page.getByTestId("trial-tianjin-demo");
  if (await btn.count()) {
    await btn.click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 });
  }
}
await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
await page.waitForTimeout(2000);
const heading = await painted("today-heading");
if (!(await page.getByTestId("hub-plan-with-ai").count())) {
  record("1-blocked", { why: "no 帮我规划 entry on this screen", heading, screenshot: await shot("01-no-entry") });
} else {
  await page.getByTestId("hub-plan-with-ai").click();
  await page.getByTestId("plan-ai-input").fill("一天之内把老城和江边都走一遍，别太赶。");
  await page.waitForTimeout(1200);
  record("1-sheet-online", {
    heading,
    preflight: await painted("plan-ai-preflight"),
    preflight_state: await page.getByTestId("plan-ai-preflight").getAttribute("data-ai-state"),
    examples: await painted("plan-ai-examples"),
    screenshot: await shot("01-online-sheet"),
  });

  /* --- 2. enter the wait: the scope line's numbers come from a real online /plans read -- */
  await page.getByTestId("plan-ai-submit").click();
  await page.getByTestId("plan-ai-live").waitFor({ timeout: 15_000 });
  await page.waitForTimeout(2500);
  record("2-waiting-online", {
    elapsed: await painted("plan-ai-elapsed"),
    scope: await painted("plan-ai-scope"),
    asked: await painted("plan-ai-asked"),
    screenshot: await shot("02-online-waiting"),
  });

  /* --- 3. leave it, and read the strip on another route ------------------------------- */
  await page.getByTestId("plan-ai-view-chat").click();
  await page.waitForTimeout(1500);
  record("3-left-online", {
    url: page.url(),
    strip: await painted("plan-ai-run-strip"),
    sheet_present: await page.getByTestId("plan-ai-sheet").count(),
    screenshot: await shot("03-online-strip"),
  });

  /* --- 4. come back and stop it: the closing card's read-back is a real online read ---- */
  await page.getByTestId("plan-ai-run-resume").click();
  await page.getByTestId("plan-ai-live").waitFor({ timeout: 10_000 });
  const backAgain = await painted("plan-ai-elapsed");
  await page.getByTestId("plan-ai-cancel").click();
  await page.getByTestId("plan-ai-result").waitFor({ timeout: 20_000 });
  await page.waitForTimeout(2000);
  record("4-closing-online", {
    elapsed_after_return: backAgain,
    status: await page.getByTestId("plan-ai-result").getAttribute("data-result-status"),
    result: await painted("plan-ai-result"),
    aftermath: await painted("plan-ai-aftermath"),
    aftermath_read: await page.getByTestId("plan-ai-aftermath").getAttribute("data-aftermath-read"),
    screenshot: await shot("04-online-closing"),
  });
}

record("9-traffic", {
  withheld_by_this_probe: withheld,
  real_reads_forwarded: forwarded.reads,
  other_writes_forwarded: forwarded.writes,
  note: "commands/generate never left the browser; every GET is the live server answering",
});
writeFileSync(`${OUT}/readings.json`, JSON.stringify(log, null, 2) + "\n", "utf-8");
await browser.close();
console.log("\nOK online readings in", OUT);
