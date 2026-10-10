/* ORD-0553 timezone follow-up, real-screen reading for V10LiveExecutionPanel's clock cell.

   What is painted: the product component is mounted by frontend/e2e/fixtures/taichenggong-0553tz-harness.tsx,
   its own `useExecutionClock` read is answered by a route stub carrying one fixed instant
   (`2026-10-10T15:30:00+08:00`) and the journey's own zone (`Asia/Shanghai`).  The device locale is
   set per arm through the browser context, which is exactly the quantity the order judges: an empty
   locale argument hands the *shape* of the number to the device, while the label under it is written
   in the traveller's chosen language.

   Two byte states, so the reading is a pair and not a claim:
     base  the bytes on the authoritative tip this branch was cut from
     cand  this lane's bytes
   Exit 0 only when every arm paints the number the app locale implies, i.e. the device could not
   override the shape; the base run is expected to fail that assertion on the arms whose device locale
   formats differently (fi uses a dot, ar-EG uses Arabic-Indic digits) -- that failure is the evidence,
   so it is printed and counted, and only the candidate run must be clean.

   Run: node review/taichenggong/tz_screen_read_r1.mjs --state=base|cand [--base=<40-hex>]
 */

import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const FRONTEND = path.join(REPO, "frontend");
const TARGET_REL = "frontend/src/features/execution/V10LiveExecutionPanel.tsx";
const TARGET = path.join(REPO, TARGET_REL);
const SHOTS = path.join(HERE, "screenshots");
const REF = "refs/heads/mirror/integration-frontend-apple-pass1";
const HARNESS = "/e2e/fixtures/taichenggong-0553tz-harness.tsx";

const argv = process.argv.slice(2);
const STATE = (/^--state=(base|cand)$/.exec(argv.at(-1) ?? "")?.[1]) ?? "";
const PINNED = (/^--base=([0-9a-f]{40})$/.exec(argv.join(" ")) ?? [])[1]
  ?? (() => {
    const out = spawnSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" }).stdout;
    return out.split(/\s+/)[0];
  })();
if (!["base", "cand"].includes(STATE)) { console.error("usage: --state=base|cand [--base=<40-hex>]"); process.exit(2); }
if (!/^[0-9a-f]{40}$/.test(PINNED)) { console.error("the pinned generation is not a 40-hex"); process.exit(2); }

const { chromium } = createRequire(path.join(FRONTEND, "package.json"))("@playwright/test");
const sha = (t) => createHash("sha256").update(t).digest("hex").slice(0, 12);

const candBytes = readFileSync(TARGET, "utf8");
if (!candBytes.includes('toLocaleTimeString(locale === "zh-CN"')) {
  throw new Error("the file on disk is not this lane's candidate bytes");
}
const baseBytes = spawnSync("git", ["-C", REPO, "show", `${PINNED}:${TARGET_REL}`],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).stdout;
if (!baseBytes.includes("toLocaleTimeString([], {")) {
  throw new Error(`the pinned generation ${PINNED.slice(0, 12)} does not carry the row this order names`);
}
const MARKER = { base: "toLocaleTimeString([], {", cand: 'toLocaleTimeString(locale === "zh-CN"' }[STATE];
const PORTS = { base: 4631, cand: 4632 };
const PORT = PORTS[STATE];

const INSTANT = "2026-10-10T15:30:00+08:00";
const ZONE = "Asia/Shanghai";
const ARMS = [
  { app: "zh-CN", device: "fi-FI", why: "Finnish lays a dot where the app writes a colon" },
  { app: "zh-CN", device: "ar-EG", why: "Arabic-Indic digits against the label's Latin zone name" },
  { app: "en", device: "fi-FI", why: "the English arm, same device shape" },
  { app: "en", device: "en-US", why: "a device whose shape already agrees, must not move" },
];

const rows = [];
const say = (l) => { rows.push(l); console.log(l); };
const listening = spawnSync("netstat", ["-ano", "-p", "TCP"], { encoding: "utf8" }).stdout
  .split("\n").filter((l) => l.includes("LISTENING") && l.includes(`:${PORT} `));
if (listening.length) { console.error(`port ${PORT} already LISTENING; refusing a neighbour's server`); process.exit(3); }

mkdirSync(SHOTS, { recursive: true });
writeFileSync(TARGET, STATE === "base" ? baseBytes : candBytes, "utf8");
say(`0 state=${STATE} pinned=${PINNED} live_tip=${(spawnSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" }).stdout.split(/\s+/)[0] ?? "")} bytes sha=${sha(STATE === "base" ? baseBytes : candBytes)}`);

const vite = spawn(process.execPath, [path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js"),
  "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { cwd: FRONTEND, stdio: "ignore" });

const waitDev = async () => {
  for (let i = 0; i < 90; i += 1) {
    const probe = spawnSync("node", ["-e",
      `fetch("http://127.0.0.1:${PORT}/").then(r=>process.stdout.write(String(r.status))).catch(()=>{})`],
      { encoding: "utf8" });
    if ((probe.stdout ?? "").trim() !== "") return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
};

let mismatches = 0;
try {
  if (!(await waitDev())) throw new Error(`vite did not answer on ${PORT}`);
  const served = await (await fetch(`http://127.0.0.1:${PORT}/src/features/execution/V10LiveExecutionPanel.tsx`)).text();
  if (!served.includes(MARKER)) throw new Error(`served module is not the ${STATE} bytes`);
  say(`0b served module carries the ${STATE} marker, length ${served.length}`);

  const browser = await chromium.launch();
  for (const arm of ARMS) {
    const context = await browser.newContext({ locale: arm.device, viewport: { width: 390, height: 844 },
      serviceWorkers: "block" });
    const page = await context.newPage();
    await page.addInitScript((loc) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", loc);
    }, arm.app);
    await page.route((u) => u.pathname.startsWith("/api/"), (r) => {
      const p = r.request().url();
      if (p.includes("/execution-clock")) {
        return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
          journey_id: "tc0553tz-journey", now: INSTANT, timezone: ZONE, used_timezone: ZONE,
          timezone_honoured: true, source: "EXECUTION_CLOCK", current_activity_id: null,
        }) });
      }
      if (p.includes("/web-observations")) {
        return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ observations: [] }) });
      }
      return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ detail: "lane stub" }) });
    });
    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "load" });
    const pageBytes = await page.evaluate(async (h) => (await fetch(h)).text(), HARNESS);
    const ownsState = pageBytes.includes(MARKER);
    await page.addScriptTag({ type: "module", url: HARNESS });
    const panel = page.locator('[data-testid="v10-live-execution-panel"]');
    await panel.first().waitFor({ state: "visible", timeout: 25_000 });
    const cell = panel.locator(".v10-metric").first();
    const number = (await cell.locator("strong").innerText()).replace(/\s+/g, " ").trim();
    const label = (await cell.locator("small").innerText()).replace(/\s+/g, " ").trim();
    /* The expectation is computed in the page, from the same instant and zone, in the app's locale --
       that is the judgement the order states, not a string this file hard-codes. */
    const expected = await page.evaluate(([instant, zone, app]) => new Intl.DateTimeFormat(
      app === "zh-CN" ? "zh-CN" : "en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: zone },
    ).format(new Date(instant)), [INSTANT, ZONE, arm.app]);
    const agrees = number === expected;
    if (!agrees) mismatches += 1;
    const file = path.join(SHOTS, `tz_${STATE}_${arm.app}_${arm.device}.png`);
    await page.screenshot({ path: file });
    say(`1 arm app=${arm.app} device=${arm.device} (${arm.why})`);
    say(`2   painted=${JSON.stringify(number)} label=${JSON.stringify(label)} app-locale expectation=${JSON.stringify(expected)} agrees=${agrees}`);
    say(`3   page-fetched component bytes are this state's: ${ownsState}; screenshot=${path.relative(REPO, file).replace(/\\/g, "/")}`);
    await context.close();
  }
  await browser.close();
} finally {
  vite.kill("SIGTERM");
  writeFileSync(TARGET, candBytes, "utf8");
  const back = sha(readFileSync(TARGET, "utf8"));
  say(`4 restored candidate bytes sha=${back} expected=${sha(candBytes)} match=${back === sha(candBytes)}`);
}

say(`5 arms=${ARMS.length} disagreeing_with_app_locale=${mismatches}`);
const verdict = STATE === "cand"
  ? (mismatches === 0 ? "PASS every arm paints the app locale's shape" : `FAIL ${mismatches} arm(s) still follow the device`)
  : `BASE recorded (${mismatches} arm(s) follow the device today)`;
say(`6 ${verdict}`);
writeFileSync(path.join(HERE, `tz_screen_${STATE}_r1.txt`), rows.join("\n") + "\n", "utf8");
if (STATE === "cand" && mismatches !== 0) process.exit(1);
