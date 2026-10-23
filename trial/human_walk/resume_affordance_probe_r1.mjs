/**
 * Is the retry the traveller can actually press?
 *
 * walk-103's own dock arm (departure_full_walk_r23.mjs:109) is printing, every minute, that the screen says
 * 「Agent 上一轮没有答完，这次的服务暂时不可用。你可以再说一次…」 while the Agent's run sits at
 * FAILED_EXTERNAL / MODEL_HTTP_503.  That refutes the "silent stall" I suspected.  The open half is the button:
 * WorkspaceActions.tsx:644 renders 继续研究 for RESUMABLE/FAILED_RECOVERABLE but disables it unless
 * aiReady && !busy && modelConsent, so "the words are there" and "the door is pressable" are two different claims.
 * This attaches read-only: it never clicks, never types, never changes storage, so the walk running in the same
 * browser keeps its own state.  PRESS=1 is the only mode that acts, and this run does not use it.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.PROBE_LOG || "resume-affordance-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const pages = context.pages();
say(`TABS ${JSON.stringify(pages.map((candidate) => candidate.url())).slice(0, 500)}`);

for (let index = 0; index < pages.length; index += 1) {
  const page = pages[index];
  const body = flat(await page.locator("body").innerText({ timeout: 8000 }).catch(() => "(unreadable)"));
  if (!/上一轮没有答完|继续研究/.test(body)) { say(`TAB_${index} IRRELEVANT ${body.slice(0, 60)}`); continue; }
  const dock = await read(page, '[data-testid="rev-dock-status"]');
  const resume = page.getByRole("button", { name: /继续研究/ }).first();
  const seen = await resume.isVisible().catch(() => false);
  const disabled = seen ? await resume.isDisabled().catch(() => "(unreadable)") : null;
  const box = seen ? await resume.boundingBox().catch(() => null) : null;
  say(`TAB_${index} url=${page.url()}`);
  say(`TAB_${index} DOCK ${dock.slice(0, 200)}`);
  say(`TAB_${index} RESUME_BUTTON visible=${seen} disabled=${JSON.stringify(disabled)} box=${JSON.stringify(box)}`);
  const consent = await read(page, ".rev-mission-consent, [aria-label='对话设置']");
  say(`TAB_${index} CONSENT_NEARBY ${consent.slice(0, 120)}`);
}
async function read(target, selector) {
  return flat(await target.locator(selector).first().innerText({ timeout: 4000 }).catch(() => "(unreadable)"));
}
await browser.close().catch(() => undefined);
