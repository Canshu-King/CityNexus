/* ORD-0553 timezone follow-up — real-screen reading through an esbuild bundle, not through the dev server.

   Why not `vite dev`: measured at run time, the shared `frontend/node_modules` this worktree junctions
   to no longer contains `@babel/core`, which `@vitejs/plugin-react` needs for every `.tsx` -- so the dev
   server answers 500 for the whole component graph. That tree belongs to other lanes, so this script does
   not touch it. esbuild is present and transforms TSX on its own, so the real product component is
   bundled with its real providers and served from a loopback page this script owns. Same component, same
   `Intl` call, same react-query hook; only the bundler differs.

   What is judged: the clock number and the label under it must be one fact. The route stub hands the
   component one instant (`2026-10-10T15:30:00+08:00`) and the journey's own zone (`Asia/Shanghai`), while
   the browser context is given a device locale whose time shape differs from the app's (fi writes a dot,
   ar-EG writes Arabic-Indic digits). `expected` is computed in the page from the app locale -- the number
   a traveller should read -- not a string hard-coded here.

   Run: node review/taichenggong/tz_screen_bundle_r1.mjs --state=base|cand [--base=<40-hex>]
   Exit 0 for a clean candidate run; the base run reports how many arms follow the device today.
 */

import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const FRONTEND = path.join(REPO, "frontend");
const TARGET_REL = "frontend/src/features/execution/V10LiveExecutionPanel.tsx";
const TARGET = path.join(REPO, TARGET_REL);
const ENTRY = path.join(FRONTEND, "e2e", "fixtures", "taichenggong-0553tz-harness.tsx");
const BUILD = path.join(HERE, "_build");
const SHOTS = path.join(HERE, "screenshots");
const REF = "refs/heads/mirror/integration-frontend-apple-pass1";

const argv = process.argv.slice(2);
const STATE = (/^--state=(base|cand)$/.exec(argv.find((a) => a.startsWith("--state=")) ?? "") ?? [])[1] ?? "";
const fromArgs = (/^--base=([0-9a-f]{40})$/
  .exec(argv.find((a) => a.startsWith("--base=")) ?? ""))?.[1];
const liveTip = (spawnSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" })
  .stdout.split(/\s+/)[0] ?? "");
const PINNED = fromArgs ?? liveTip;
if (!["base", "cand"].includes(STATE) || !/^[0-9a-f]{40}$/.test(PINNED)) {
  console.error("usage: --state=base|cand [--base=<40-hex>]");
  process.exit(2);
}

const require_ = createRequire(path.join(FRONTEND, "package.json"));
const esbuild = require_("esbuild");
const { chromium } = require_("@playwright/test");
const sha = (t) => createHash("sha256").update(t).digest("hex").slice(0, 12);

const candBytes = readFileSync(TARGET, "utf8");
if (!candBytes.includes('toLocaleTimeString(locale === "zh-CN"')) {
  throw new Error("the file on disk is not this lane's candidate bytes");
}
const baseBytes = spawnSync("git", ["-C", REPO, "show", `${PINNED}:${TARGET_REL}`],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).stdout;
if (!baseBytes.includes("toLocaleTimeString([], {")) {
  throw new Error(`pinned ${PINNED.slice(0, 12)} does not carry the row this order names`);
}
const bytesFor = STATE === "base" ? baseBytes : candBytes;
const MARKER = { base: "toLocaleTimeString([], {", cand: 'toLocaleTimeString(locale === "zh-CN"' }[STATE];
const PORT = STATE === "base" ? 4641 : 4642;
const INSTANT = "2026-10-10T15:30:00+08:00";
const ZONE = "Asia/Shanghai";
const ARMS = [
  { app: "zh-CN", device: "fi-FI", why: "fi lays a dot where the app writes a colon" },
  { app: "zh-CN", device: "ar-EG", why: "Arabic-Indic digits under a Latin zone name" },
  { app: "en", device: "fi-FI", why: "the English arm against the same device shape" },
  { app: "en", device: "en-US", why: "a device that already agrees must not move" },
];

const rows = [];
const say = (l) => { rows.push(l); console.log(l); };
mkdirSync(BUILD, { recursive: true });
mkdirSync(SHOTS, { recursive: true });

const html = `<!doctype html><html><head><meta charset="utf-8"><title>tz harness</title></head>
<body><script type="module" src="/bundle.js"></script></body></html>`;

writeFileSync(TARGET, bytesFor, "utf8");
say(`0 state=${STATE} pinned=${PINNED} live_tip=${liveTip} bytes sha=${sha(bytesFor)}`);

let server;
let browser;
let mismatches = 0;
try {
  const out = path.join(BUILD, `tz_bundle_${STATE}.js`);
  await esbuild.build({
    entryPoints: [ENTRY], bundle: true, outfile: out, platform: "browser", format: "esm",
    jsx: "automatic", define: { "process.env.NODE_ENV": '"development"' }, logLevel: "silent",
  });
  const bundle = readFileSync(out, "utf8");
  const flat = (s) => s.replace(/\s+/g, "");
  if (!flat(bundle).includes(flat(MARKER))) {
    throw new Error(`the bundle does not carry the ${STATE} bytes of the product file`);
  }
  say(`0b bundle length ${bundle.length}, carries the ${STATE} marker`);

  server = createServer((req, res) => {
    if (req.url === "/bundle.js") {
      res.writeHead(200, { "content-type": "text/javascript" });
      res.end(bundle);
    } else {
      res.writeHead(200, { "content-type": "text/html" });
      res.end(html);
    }
  });
  await new Promise((done) => server.listen(PORT, "127.0.0.1", done));

  browser = await chromium.launch();
  for (const arm of ARMS) {
    const context = await browser.newContext({ locale: arm.device, viewport: { width: 390, height: 844 },
      serviceWorkers: "block" });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 140)));
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
        return r.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify({ observations: [] }) });
      }
      return r.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ detail: "lane stub" }) });
    });
    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "load" });
    const panel = page.locator('[data-testid="v10-live-execution-panel"]');
    await panel.first().waitFor({ state: "visible", timeout: 30_000 });
    const cell = panel.locator(".v10-metric").first();
    const number = (await cell.locator("strong").innerText()).replace(/\s+/g, " ").trim();
    const label = (await cell.locator("small").innerText()).replace(/\s+/g, " ").trim();
    const expected = await page.evaluate(([instant, zone, app]) => new Intl.DateTimeFormat(
      app === "zh-CN" ? "zh-CN" : "en-GB",
      { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: zone },
    ).format(new Date(instant)), [INSTANT, ZONE, arm.app]);
    const agrees = number === expected;
    if (!agrees) mismatches += 1;
    const file = path.join(SHOTS, `tzbundle_${STATE}_${arm.app}_${arm.device}.png`);
    await page.screenshot({ path: file });
    say(`1 arm app=${arm.app} device=${arm.device} :: ${arm.why}`);
    say(`2   painted=${JSON.stringify(number)} label=${JSON.stringify(label)} expectation_from_app_locale=${JSON.stringify(expected)} agrees=${agrees}`);
    say(`3   screenshot=${path.relative(REPO, file).replace(/\\/g, "/")} page_errors=${errors.length ? errors.join(" | ") : "none"}`);
    await context.close();
  }
} finally {
  if (browser) await browser.close();
  if (server) server.close();
  writeFileSync(TARGET, candBytes, "utf8");
  const back = sha(readFileSync(TARGET, "utf8"));
  say(`4 restored candidate bytes sha=${back} expected=${sha(candBytes)} match=${back === sha(candBytes)}`);
}

say(`5 arms=${ARMS.length} arms_following_the_device_instead_of_the_app_locale=${mismatches}`);
say(`6 ${STATE === "cand"
  ? (mismatches === 0 ? "PASS every arm reads in the app locale's shape" : `FAIL ${mismatches} arm(s) still follow the device`)
  : `BASE recorded: ${mismatches} arm(s) follow the device on the tip this branch was cut from`}`);
writeFileSync(path.join(HERE, `tz_screen_${STATE}_r1.txt`), rows.join("\n") + "\n", "utf8");
if (STATE === "cand" && mismatches !== 0) process.exit(1);
