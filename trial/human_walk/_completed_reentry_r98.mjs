import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

const ROOT = "D:/moodle/_cmdr_rescue_v3_1022";
const LIVE = "D:/moodle/_cmdr_v3_live_1022";
const DB = LIVE + "/completed_reentry_1026.db";
const BACKEND = ROOT + "/backend";
const PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe";
const NODE = "C:/Program Files/nodejs/node.exe";
const KEY = "completed-reentry-presenter-key-0123456789abcdef0123456789abcdef";
const SECRET = "completed-reentry-secret-0123456789abcdef0123456789abcdef";
const OUT = ROOT + "/trial/results/20261022_v3_human_chrome/completed-reentry-98.txt";
const SHOT = ROOT + "/trial/results/20261022_v3_human_chrome/classroom-completed-reentry-98.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };

const raw = JSON.parse(fs.readFileSync(LIVE + "/.demo_pairing_ticket", "utf8"));
const journey = raw.journey_id;

async function waitFor(url, tries = 90) {
  for (let index = 0; index < tries; index += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch { /* not up yet */ }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return false;
}

async function post(path, body, headers) {
  const response = await fetch("http://127.0.0.1:60400" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(headers || {}) },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let parsed = {};
  try { parsed = JSON.parse(text); } catch { parsed = { raw: text.slice(0, 120) }; }
  return { status: response.status, body: parsed };
}

const logFd = fs.openSync(LIVE + "/completed_reentry_backend.log", "w");
const backend = spawn(PY, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND], {
  cwd: BACKEND,
  env: {
    ...process.env,
    CITYNEXUS_DATABASE_URL: "sqlite:///" + DB.replace(/\\/g, "/"),
    CITYNEXUS_TRAVELER_AUTH_SECRET: SECRET,
    CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS: "3600",
    CITYNEXUS_DEMO_MODE: "true",
    CITYNEXUS_DEMO_DATABASE_PATH: DB,
    CITYNEXUS_DEMO_PRESENTER_KEY: KEY,
    CITYNEXUS_SIMULATION_ENABLED: "true",
    PYTHONPATH: BACKEND,
  },
  stdio: ["ignore", logFd, logFd],
});
let frontend = null;

try {
  const healthy = await waitFor("http://127.0.0.1:60400/api/v1/health");
  note(`BACKEND_HEALTHY ${healthy}`);
  if (!healthy) throw new Error("backend not healthy");
  const issued = await post("/api/v1/demo/pairing", { journey_id: journey }, { "X-CityNexus-Presenter-Key": KEY });
  note(`PAIRING ${JSON.stringify({ status: issued.status, has_ticket: Boolean(issued.body.ticket), error: issued.body.error })}`);
  if (issued.status !== 201 || !issued.body.ticket) throw new Error("no ticket");

  frontend = spawn(NODE, ["node_modules/vite/bin/vite.js", "--port", "14495", "--strictPort", "--host", "127.0.0.1"], {
    cwd: ROOT + "/frontend",
    env: { ...process.env, CITYNEXUS_BACKEND_PORT: "60400" },
    stdio: "ignore",
  });
  const pageUp = await waitFor("http://127.0.0.1:14495/revolution");
  note(`FRONTEND_UP ${pageUp}`);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
  await page.goto(`http://127.0.0.1:14495/revolution#pair=${encodeURIComponent(issued.body.ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(6500);
  const reading = await page.evaluate(() => {
    const banner = document.querySelector('[data-testid="rev-demo-error-banner"]');
    return {
      banner: banner ? banner.textContent : null,
      clock: document.querySelectorAll('[data-testid="rev-classroom-clock"]').length,
      presenter: document.querySelectorAll('[data-testid="rev-presenter"]').length,
      entry: document.querySelectorAll('[data-testid="rev-jump-clock"]').length,
      tab: document.querySelectorAll('[data-testid="rev-mobile-screen-trips"]').length,
    };
  });
  note(`SCREEN ${JSON.stringify(reading)}`);
  note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
  await page.screenshot({ path: SHOT, fullPage: false });
  await browser.close();
} finally {
  for (const child of [frontend, backend]) {
    if (!child) continue;
    spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  }
  fs.closeSync(logFd);
}
