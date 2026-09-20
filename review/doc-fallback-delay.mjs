/**
 * Settle the document `networkTimeoutSeconds` by measurement, not by argument.
 *
 * A4's acceptance asks two things of a production build behind a worker that caches the
 * `/v8/*` document:
 *   A. a document delayed 4 s must still be served from the network (the stale-shell bug
 *      that made 3 s untenable must not come back at the new value);
 *   B. a document delayed beyond the configured budget may fall back to the cached,
 *      same-version document.
 *
 * Case A under a 10 s budget proves nothing about an 8 s budget -- the response simply
 * arrives before both -- so the script builds and measures at each budget it is given.
 * vite.config.ts is patched, built, tested, and restored byte-for-byte (sha checked), and
 * nothing here changes any number in the repository: the value that ships is decided from
 * the recorded table.
 */

import { execFileSync, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, copyFileSync, existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import path from "node:path";

const require_ = createRequire("D:/moodle/_qoder_ui_overnight_20260920/frontend/index.js");
const { chromium } = require_("playwright");

const FRONTEND = "D:/moodle/_qoder_ui_overnight_20260920/frontend";
const REVIEW = "D:/moodle/_qoder_ui_overnight_20260920/review";
const CONFIG = path.join(FRONTEND, "vite.config.ts");
const BACKUP = path.join(REVIEW, "vite.config.ts.docprobe.bak");
const OUT = path.join(REVIEW, "doc-timeout-results.md");
const PROXY_PORT = 4489;
const PREVIEW_PORT = 4490;
const CONTROL = { documentDelayMs: 0 };

const sha = (file) => createHash("sha1").update(readFileSync(file)).digest("hex").slice(0, 12);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function setBudget(seconds) {
  const text = readFileSync(CONFIG, "utf8");
  const next = text.replace(/networkTimeoutSeconds: \d+,/, `networkTimeoutSeconds: ${seconds},`);
  if (next === text) throw new Error(`no networkTimeoutSeconds line to set in ${CONFIG}`);
  writeFileSync(CONFIG, next, "utf8");
}

function startProxy() {
  const server = http.createServer(async (req, res) => {
    const isDocument = !/\.(?:js|mjs|css|map|json|wasm|ico|svg|png|jpe?g|gif|webp|avif|woff2?|ttf|otf|webmanifest)$/i
      .test(req.url ?? "");
    if (isDocument && CONTROL.documentDelayMs > 0) await sleep(CONTROL.documentDelayMs);
    const upstream = http.get(
      // `identity`, because the browser's `accept-encoding: gzip` would make the preview
      // hand back encoded bytes that cannot be stamped -- and forwarding them without their
      // content-encoding leaves the browser a document it cannot parse.
      { host: "127.0.0.1", port: PREVIEW_PORT, path: req.url, headers: { ...req.headers, "accept-encoding": "identity" } },
      (up) => {
        const chunks = [];
        up.on("data", (chunk) => chunks.push(chunk));
        up.on("end", () => {
          let body = Buffer.concat(chunks);
          const type = up.headers["content-type"] ?? "";
          const encoded = up.headers["content-encoding"];
          if (type.includes("text/html") && !encoded) {
            // Stamp which document the browser actually received: the only way to tell a
            // fresh network response from a cached one when both render the same page.
            const stamp = `<!--cnx-doc-${Date.now()}-${CONTROL.documentDelayMs}ms-->`;
            body = Buffer.from(body.toString("utf8").replace(/<head>/i, `<head>${stamp}`), "utf8");
          }
          /* Only the semantic headers are forwarded. Copying the upstream framing headers
             (`transfer-encoding`, `content-length`, `connection`) alongside a rewritten
             buffer left the browser's parser waiting for a body that was framed twice, so
             the page never fetched its bundle and no service worker ever registered -- a
             harness fault that looked exactly like a product that would not boot. */
          const headers = {
            "content-type": type || "application/octet-stream",
            "cache-control": "public, max-age=0",
            "content-length": String(body.length),
          };
          if (up.headers.vary) headers.vary = up.headers.vary;
          console.log(`proxy ${req.method} ${req.url} -> ${up.statusCode} ${body.length}B type=${type.slice(0, 24)} delay=${CONTROL.documentDelayMs}`);
          res.writeHead(up.statusCode ?? 200, headers);
          res.end(body);
        });
      },
    );
    upstream.on("error", (error) => {
      console.log(`proxy ${req.method} ${req.url} -> upstream ${error.message}`);
      res.writeHead(502, { "content-type": "text/plain" });
      res.end("proxy upstream failed");
    });
  });
  server.listen(PROXY_PORT, "127.0.0.1");
  return server;
}

async function stampOf(page) {
  // A committed navigation has no scripts yet, so read the stamp once it has appeared.
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const stamp = await readStamp(page);
    if (stamp) return stamp;
    await sleep(250);
  }
  return null;
}

async function readStamp(page) {
  return page.evaluate(() => {
    const match = document.documentElement.innerHTML.match(/<!--cnx-doc-(\d+)-(\d+)ms-->/);
    return match ? { id: Number(match[1]), delay: Number(match[2]) } : null;
  });
}

async function measure(page) {
  const url = `http://127.0.0.1:${PROXY_PORT}/v8/live`;
  // Boot once so the worker installs and claims, then let it control the page.
  await page.goto(url, { waitUntil: "commit" });
  let controlled = false;
  for (let attempt = 0; attempt < 20 && !controlled; attempt += 1) {
    await sleep(1_000);
    controlled = await page.evaluate(() => !!navigator.serviceWorker.controller).catch(() => false);
    if (!controlled && attempt === 5) await page.reload({ waitUntil: "commit" });
  }
  if (!controlled) throw new Error("no service worker ever controlled the page; the cases below would prove nothing");
  await page.reload({ waitUntil: "commit" });
  const cached = await stampOf(page);
  if (!cached) throw new Error("no document stamp reached the page; the proxy is not on the path");

  CONTROL.documentDelayMs = 4_000;
  let started = Date.now();
  await page.reload({ waitUntil: "commit" });
  const after4 = await stampOf(page);
  const t4 = Date.now() - started;

  // Beyond whatever budget this build carries: the cached same-version document is allowed.
  const beyond = Number(readFileSync(CONFIG, "utf8").match(/networkTimeoutSeconds: (\d+),/)[1]);
  CONTROL.documentDelayMs = beyond * 1000 + 2_500;
  started = Date.now();
  await page.reload({ waitUntil: "commit" });
  const afterBeyond = await stampOf(page);
  const tBeyond = Date.now() - started;
  CONTROL.documentDelayMs = 0;

  /* Each document carries the delay that was in force when the proxy made it, so the stamp
     says which answer the browser got: a fresh one is the delay just asked for, a fallback
     is the previously cached document. */
  return {
    cached,
    after4,
    t4,
    afterBeyond,
    tBeyond,
    beyond,
    caseA: after4?.delay === 4_000,
    caseB: afterBeyond?.delay !== beyond * 1000 + 2_500 && afterBeyond !== null,
  };
}

const budgets = process.argv.slice(2).map(Number).filter(Boolean);
if (!budgets.length) throw new Error("usage: node doc-fallback-delay.mjs <seconds> [<seconds>…]");

const original = readFileSync(CONFIG, "utf8");
copyFileSync(CONFIG, BACKUP);
const baselineSha = sha(CONFIG);
appendFileSync(OUT, `\n_measured ${new Date().toISOString()} (proxy ${PROXY_PORT} -> preview ${PREVIEW_PORT})_\n\n`);

const browser = await chromium.launch({ channel: "chrome" }).catch(() => chromium.launch());
const proxy = startProxy();
try {
  for (const budget of budgets) {
    setBudget(budget);
    execFileSync(process.execPath, [path.join(FRONTEND, "node_modules/vite/bin/vite.js"), "build"], {
      cwd: FRONTEND,
      stdio: "pipe",
    });
    const preview = spawn(
      process.execPath,
      [path.join(FRONTEND, "node_modules/vite/bin/vite.js"), "preview", "--host", "127.0.0.1", "--port", String(PREVIEW_PORT)],
      { cwd: FRONTEND, stdio: "ignore" },
    );
    try {
      let up = false;
      for (let i = 0; i < 40 && !up; i += 1) {
        await sleep(1_000);
        up = await new Promise((resolve) => {
          const probe = http.get(`http://127.0.0.1:${PREVIEW_PORT}/v8/live`, (res) => {
            res.resume();
            resolve(true);
          });
          probe.on("error", () => resolve(false));
          probe.setTimeout(3_000, () => resolve(false));
        });
      }
      if (!up) throw new Error("the production preview never answered");
      const context = await browser.newContext({ serviceWorkers: "allow" });
      const page = await context.newPage();
      let result;
      try {
        result = await measure(page);
      } finally {
        await context.close();
      }
      appendFileSync(
        OUT,
        `| budget | cached first | 4 s delay | case A (network wins) | ${result.beyond + 2.5} s delay | case B (fell back) |\n` +
          `|---|---|---|---|---|---|\n` +
          `| ${result.beyond}s | ${result.cached.delay}ms @${result.cached.id} | ${result.after4?.delay}ms @${result.after4?.id}, ${result.t4}ms wall | ${result.caseA ? "PASS" : "FAIL"} | ${result.afterBeyond?.delay}ms @${result.afterBeyond?.id}, ${result.tBeyond}ms wall | ${result.caseB ? "PASS" : "FAIL"} |\n\n`,
      );
      console.log(
        `budget ${result.beyond}s: A ${result.caseA ? "PASS" : "FAIL"} ${JSON.stringify(result.after4)} ` +
          `| B ${result.caseB ? "PASS" : "FAIL"} ${JSON.stringify(result.afterBeyond)}`,
      );
    } finally {
      preview.kill();
      await sleep(1_000);
    }
  }
} finally {
  proxy.close();
  writeFileSync(CONFIG, original, "utf8");
  const restored = sha(CONFIG);
  console.log(`restored vite.config.ts ${baselineSha} -> ${restored} ${restored === baselineSha ? "OK" : "MISMATCH — CHECK BY HAND"}`);
  if (existsSync(BACKUP)) unlinkSync(BACKUP);
  await browser.close();
}
