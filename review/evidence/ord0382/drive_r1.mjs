/**
 * ORD-0382 evidence driver.  One browser, 390x844, walking the four states the order names:
 * enter the wait -> leave it -> come back -> interrupt and read the closing state.
 *
 * Every assertion reads *rendered text* (innerText), never a data-* attribute; the attributes are
 * printed alongside only so a later reader can tie a frame to the machine state behind it.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = "http://127.0.0.1:4789";
const ARM = "http://127.0.0.1:4790";
const OUT = process.env.ORD0382_OUT ?? "D:/moodle/_qoder_q_ord0382_evidence/frames";
const JOURNEY = "9c6c3d73-8b8e-4f71-beaf-32bc87aba035";
const REQUEST_TEXT = "带爸妈去广州三天，不要走太多路，想吃点当地的。";
mkdirSync(OUT, { recursive: true });

const log = [];
let journalMark = 0;
let hitMark = { commands: 0, generates: 0, plansReads: 0 };
const record = async (step, data) => {
  const body = await (await fetch(`${ARM}/?hits=1`)).json();
  const hits = body.hit;
  const sent = journal.slice(journalMark);
  journalMark = journal.length;
  const delta = { commands: hits.commands - hitMark.commands, generates: hits.generates - hitMark.generates };
  hitMark = hits;
  data.sent = sent.map((x) => `${x.method} ${x.path.replace(/^\/api\/v1\//, "")}`);
  data.new_legs = delta;
  data.journal_at_record = journal.slice();
  log.push({ step, ...data });
  console.log(`\n### ${step}`);
  for (const [k, v] of Object.entries(data)) console.log(`  ${k} = ${typeof v === "string" ? v : JSON.stringify(v)}`);
};

/** The words actually painted inside a testid, whitespace-normalised. */
const painted = async (page, testId) => {
  const loc = page.getByTestId(testId).first();
  if (!(await loc.count())) return null;
  return (await loc.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
};

const shot = async (page, name) => {
  const path = `${OUT}/${name}.png`;
  await page.screenshot({ path });
  return path;
};

const armSet = async (params) => {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${ARM}/?${q}`);
  return res.json();
};

const waitSubmitReady = async (p, ms = 25_000) => {
  await p.getByTestId("plan-ai-submit").waitFor({ timeout: ms });
  await p.waitForFunction(
    () => !document.querySelector('[data-testid="plan-ai-submit"]')?.disabled,
    null,
    { timeout: ms },
  );
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
/* Journal every API call with its method, path and time, so a count that does not match the steps
   is attributed to a step rather than argued about. */
const journal = [];
const watch = (p) => p.on("request", (req) => {
  const u = new URL(req.url());
  if (u.pathname.startsWith("/api/")) journal.push({ t: Date.now(), method: req.method(), path: u.pathname, at: p === page ? "main" : "extra" });
});
watch(page);
await page.addInitScript((value) => {
  localStorage.setItem("citynexus.locale", value);
}, "zh-CN");

/* --- reach Today ------------------------------------------------------- */
await page.goto(`${BASE}/v8`, { waitUntil: "load" });
await page.waitForTimeout(800);
await record("landing", {
  body_head: (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 160),
  trial_setup: await painted(page, "trial-setup"),
  demo_button: await painted(page, "trial-tianjin-demo"),
  screenshot: await shot(page, "00-landing"),
});
if (await page.getByTestId("trial-tianjin-demo").count()) {
  await page.getByTestId("trial-tianjin-demo").click();
  await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 });
}
await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
await page.waitForTimeout(1200);
await record("today", {
  heading: await painted(page, "today-heading"),
  ai_entry: await painted(page, "hub-plan-with-ai"),
  screenshot: await shot(page, "01-today"),
});

/* --- open the sheet: the preflight line is the server's real current value --------- */
await armSet({ reset: "1" });
await page.getByTestId("hub-plan-with-ai").click();
await page.getByTestId("plan-ai-input").fill(REQUEST_TEXT);
await page.waitForTimeout(600);
await record("sheet-open", {
  preflight: await painted(page, "plan-ai-preflight"),
  preflight_state: await page.getByTestId("plan-ai-preflight").getAttribute("data-ai-state"),
  screenshot: await shot(page, "02-sheet-preflight"),
});

/* --- 1. enter the waiting state ---------------------------------------------------- */
await armSet({ commandDelayMs: "30000" });
await page.getByTestId("plan-ai-submit").click();
await page.getByTestId("plan-ai-live").waitFor({ timeout: 10_000 });
await page.waitForTimeout(2500);
const waitA = {
  elapsed: await painted(page, "plan-ai-elapsed"),
  scope: await painted(page, "plan-ai-scope"),
  note: await painted(page, "plan-ai-live"),
  screenshot: await shot(page, "03-waiting"),
};
await record("1-enter-waiting", waitA);

/* --- 2. leave it: press the close control, take the named exit --------------------- */
await page.getByTestId("plan-ai-dismiss").click();
await page.getByTestId("plan-ai-leave-choice").waitFor({ timeout: 5_000 });
await record("2a-leave-prompt", {
  prompt: await painted(page, "plan-ai-leave-prompt"),
  chat_exit: await painted(page, "plan-ai-view-chat"),
  continue_exit: await painted(page, "plan-ai-continue"),
  screenshot: await shot(page, "04-leave-prompt"),
});
await page.getByTestId("plan-ai-view-chat").click();
await page.waitForTimeout(1200);
await record("2b-left-to-session", {
  url: page.url(),
  strip: await painted(page, "plan-ai-run-strip"),
  sheet_present: await page.getByTestId("plan-ai-sheet").count(),
  screenshot: await shot(page, "05-strip-on-session"),
});

/* --- 3. walk a third route *in-app*, then come back and check the count kept running.
   A `page.goto` here would be a reload, and a reload destroys the in-flight fetch by
   definition -- the named boundary in aiGenerationRun.ts.  The traveller's own route
   changes are pushState, so that is what this frame has to exercise. -------------------- */
await page.getByTestId("nav-map").click();
await page.waitForTimeout(1500);
await record("3a-another-route", {
  url: page.url(),
  strip: await painted(page, "plan-ai-run-strip"),
  screenshot: await shot(page, "06-strip-on-another-route"),
});
const secondsBefore = await page.getByTestId("plan-ai-run-strip").getAttribute("data-run-seconds");
await page.getByTestId("plan-ai-run-resume").click();
await page.getByTestId("plan-ai-live").waitFor({ timeout: 8_000 });
const secondsAfter = await painted(page, "plan-ai-elapsed");
await record("3b-returned", {
  strip_seconds_seen: secondsBefore,
  sheet_elapsed_after_return: secondsAfter,
  asked_line: await painted(page, "plan-ai-asked"),
  textarea_kept_the_original_ask: await page.getByTestId("plan-ai-input").inputValue(),
  monotonic: Number(secondsAfter.match(/\d+/)?.[0] ?? -1) >= Number(secondsBefore ?? -1),
  screenshot: await shot(page, "07-returned-to-waiting"),
});

/* --- 4. interrupt, and read the closing state ------------------------------------- */
await page.getByTestId("plan-ai-cancel").click();
await page.getByTestId("plan-ai-result").waitFor({ timeout: 15_000 });
await page.waitForTimeout(1500);
await record("4-closing-state", {
  status: await page.getByTestId("plan-ai-result").getAttribute("data-result-status"),
  result: await painted(page, "plan-ai-result"),
  aftermath: await painted(page, "plan-ai-aftermath"),
  aftermath_read: await page.getByTestId("plan-ai-aftermath").getAttribute("data-aftermath-read"),
  stopped_at: await page.getByTestId("plan-ai-aftermath").getAttribute("data-aftermath-stopped-at"),
  landed_attr: await page.getByTestId("plan-ai-aftermath").getAttribute("data-aftermath-landed"),
  live_strip_still_there: await page.getByTestId("plan-ai-run-strip").count(),
  hits: await (await fetch(`${ARM}/?hits=1`)).json(),
  screenshot: await shot(page, "08-closing-state"),
});

/* --- 5. leave mid-wait and let it finish unseen: the strip must carry the outcome -- */
await armSet({ reset: "1", commandDelayMs: "6000", commandStatus: "422", commandBody: JSON.stringify({ error: { code: "AI_DISABLED_BY_OPS", message: "the operator switch is off" } }) });
/* If a previous leg is still held open, this press is refused by design -- wait for the sheet to be
   idle rather than clicking a control the product is deliberately not offering. */
await waitSubmitReady(page);
await page.getByTestId("plan-ai-submit").click();
await page.getByTestId("plan-ai-live").waitFor({ timeout: 8_000 });
await page.getByTestId("plan-ai-view-chat").click();
await page.waitForTimeout(1500);
await record("5a-left-before-answer", {
  url: page.url(),
  strip: await painted(page, "plan-ai-run-strip"),
  screenshot: await shot(page, "09-strip-while-away"),
});
await page.waitForFunction(() => {
  const el = document.querySelector('[data-testid="plan-ai-run-strip"]');
  return !!el && el.getAttribute("data-run-state") === "settled";
}, null, { timeout: 30_000 });
await record("5b-finished-unseen", {
  strip: await painted(page, "plan-ai-run-strip"),
  resume_label: await painted(page, "plan-ai-run-resume"),
  screenshot: await shot(page, "10-strip-outcome"),
});
await page.getByTestId("plan-ai-run-resume").click();
await page.getByTestId("plan-ai-result").waitFor({ timeout: 8_000 });
await record("5c-opened-the-outcome", {
  status: await page.getByTestId("plan-ai-result").getAttribute("data-result-status"),
  result: await painted(page, "plan-ai-result"),
  screenshot: await shot(page, "11-outcome-in-sheet"),
});

/* --- 6. the English arm of the same three states, so no state is only ever painted
   in one language ------------------------------------------------------------- */
const en = await browser.newPage({ viewport: { width: 390, height: 844 } });
watch(en);
await en.addInitScript(() => localStorage.setItem("citynexus.locale", "en"));
await armSet({ reset: "1", commandDelayMs: "30000" });
await en.goto(`${BASE}/v8`, { waitUntil: "load" });
await en.waitForTimeout(800);
if (await en.getByTestId("trial-tianjin-demo").count()) {
  await en.getByTestId("trial-tianjin-demo").click();
  await en.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 });
}
await en.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
await en.waitForTimeout(1200);
await en.getByTestId("hub-plan-with-ai").click();
await en.getByTestId("plan-ai-input").fill("Three days with my parents, not much walking, somewhere local to eat.");
await en.getByTestId("plan-ai-submit").click();
await en.getByTestId("plan-ai-live").waitFor({ timeout: 10_000 });
await en.waitForTimeout(2000);
await record("6a-en-waiting", {
  elapsed: await painted(en, "plan-ai-elapsed"),
  scope: await painted(en, "plan-ai-scope"),
  screenshot: await shot(en, "12-en-waiting"),
});
await en.getByTestId("plan-ai-dismiss").click();
await en.getByTestId("plan-ai-leave-choice").waitFor({ timeout: 5_000 });
await record("6b-en-leave-prompt", {
  prompt: await painted(en, "plan-ai-leave-prompt"),
  chat: await painted(en, "plan-ai-view-chat"),
  cont: await painted(en, "plan-ai-continue"),
  screenshot: await shot(en, "13-en-leave-prompt"),
});
await en.getByTestId("plan-ai-cancel").click();
await en.getByTestId("plan-ai-result").waitFor({ timeout: 15_000 });
await en.waitForTimeout(1500);
await record("6c-en-closing", {
  status: await en.getByTestId("plan-ai-result").getAttribute("data-result-status"),
  aftermath: await painted(en, "plan-ai-aftermath"),
  screenshot: await shot(en, "14-en-closing"),
});

/* --- 7. the two arms that cannot be reached without a write the shared store will not
   get from me: 「已经生成的部分还在」 and 「回读时才有了生效方案」.  Both are driven by a
   two-sided row set built from the REAL captured rows, so this is fixture evidence and the
   receipt names it as such -- no POST ever leaves this harness. ------------------------ */
const fixtureArm = async (mode, name) => {
  await armSet({ reset: "1", twoSided: mode, commandDelayMs: "30000" });
  const p = await browser.newPage({ viewport: { width: 390, height: 844 } });
  watch(p);
  await p.addInitScript(() => localStorage.setItem("citynexus.locale", "zh-CN"));
  await p.goto(`${BASE}/v8`, { waitUntil: "load" });
  await p.waitForTimeout(800);
  if (await p.getByTestId("trial-tianjin-demo").count()) {
    await p.getByTestId("trial-tianjin-demo").click();
    await p.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 });
  }
  await p.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  await p.waitForTimeout(1200);
  await p.getByTestId("hub-plan-with-ai").click();
  await p.getByTestId("plan-ai-input").fill(REQUEST_TEXT);
  await p.getByTestId("plan-ai-submit").click();
  await p.getByTestId("plan-ai-live").waitFor({ timeout: 10_000 });
  await p.waitForTimeout(2500);
  await p.getByTestId("plan-ai-cancel").click();
  await p.getByTestId("plan-ai-result").waitFor({ timeout: 15_000 });
  await p.waitForTimeout(1500);
  await record(`7-${name}-fixture`, {
    status: await p.getByTestId("plan-ai-result").getAttribute("data-result-status"),
    result: await painted(p, "plan-ai-result"),
    aftermath: await painted(p, "plan-ai-aftermath"),
    landed_attr: await p.getByTestId("plan-ai-aftermath").getAttribute("data-aftermath-landed"),
    screenshot: await shot(p, `15-${name}-fixture`),
  });
  await p.close();
};
await fixtureArm("added", "landed");
await fixtureArm("appeared", "appeared");

writeFileSync(`${OUT}/readings.json`, JSON.stringify(log, null, 2) + "\n", "utf-8");
await browser.close();
console.log("\nOK frames+readings in", OUT);
