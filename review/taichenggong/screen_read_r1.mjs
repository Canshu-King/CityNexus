/* ORD-0557 real-screen reading for the two media-type fallbacks this lane moved.
 *
 * What it paints: `GET /api/v1/journeys/<id>/experience` is answered 200 with zero bytes and a
 * Content-Type header that exists and is empty.  The probe in content_type_probe_r1.mjs measured
 * that an empty header value does reach the page as "", which is the only way the classification
 * leaves `attribution.content_type` unset, which is the only way the fallback this order names is
 * the text a traveller reads.  Nothing here is a mock of the copy: the app's own failure view renders
 * it through the product component tree.
 *
 * Three byte states, so the reading carries its own before/after and its own teeth:
 *   tip     the authoritative bytes (改前)
 *   cand    this lane's bytes (改后)          -- must paint exactly the tip words
 *   mutant  candidate with the key name broken -- must paint something else, or the assertion is
 *                                             not watching the mechanism this order paid for
 *
 * Run: node review/taichenggong/screen_read_r1.mjs --state tip|cand|mutant
 * The product file is swapped for the run and written back in a finally; both hashes are printed.
 */

import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const FRONTEND = path.join(REPO, "frontend");
const TARGET_REL = "frontend/src/lib/failureAttribution.ts";
const TARGET = path.join(REPO, TARGET_REL);
const SHOTS = path.join(HERE, "screenshots");
const REF = "refs/heads/mirror/integration-frontend-apple-pass1";

const argv = process.argv.slice(2);
const STATE = (/^--state=(tip|cand|mutant)$/.exec(argv.at(-1) ?? "")?.[1])
  ?? (/^--state$/.test(argv.at(-2) ?? "") ? argv.at(-1) : "");
if (!["tip", "cand", "mutant"].includes(STATE)) {
  console.error("usage: node screen_read_r1.mjs --state=tip|cand|mutant");
  process.exit(2);
}
const { chromium } = createRequire(path.join(FRONTEND, "package.json"))("@playwright/test");
const sha = (text) => createHash("sha256").update(text).digest("hex").slice(0, 12);
const MUTATE_FROM = 'categoryLabel("UNKNOWN"';
const MUTATE_TO = 'categoryLabel("UNKNOWX"';
// What the dev server must be handing the page for each byte state; checked before any word is read.
const SERVED_MARKER = { tip: '?? "未知"', cand: MUTATE_FROM, mutant: MUTATE_TO }[STATE];

/* One port per byte state.  The first cut reused 4613 for all three, and a dev server that outlived
   its own run answered the next run -- so the tip and mutant arms painted the candidate's words and
   looked like "the mutant does not bite".  strictPort cannot detect that (a neighbour is already
   bound), so the port is unique AND the served module is fingerprinted below. */
const PORTS = { tip: 4621, cand: 4622, mutant: 4623 };
const PORT = Number(process.env.CITYNEXUS_TAICHENG_PORT ?? PORTS[STATE]);
const JOURNEY = "11111111-2222-4333-8444-555555555555";

const candBytes = readFileSync(TARGET, "utf8");
if (!candBytes.includes(MUTATE_FROM)) {
  throw new Error("the file on disk is not this lane's candidate bytes; refusing to swap from a wrong base");
}
const tipBytes = spawnSync("git", ["-C", REPO, "show", `${readTip()}:${TARGET_REL}`],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).stdout;
function readTip() {
  const out = spawnSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" }).stdout;
  const tip = out.split(/\s+/)[0] ?? "";
  if (!/^[0-9a-f]{40}$/.test(tip)) throw new Error("cannot read the authoritative tip");
  return tip;
}
if (!tipBytes || tipBytes.length < 1000) throw new Error("could not read the tip bytes");
// replaceAll, not replace: this file carries the same read twice (the cached arm and the no-copy arm),
// and the first cut mutated only the first.  The screen painted the second, so the mutant looked blind
// when it was really only half-applied.
const mutantBytes = candBytes.replaceAll(MUTATE_FROM, MUTATE_TO);
if (mutantBytes === candBytes) throw new Error("mutant patch did not apply");
if (mutantBytes.includes(MUTATE_FROM)) throw new Error("mutant patch was partial; both sites must change");

const bytesFor = { tip: tipBytes, cand: candBytes, mutant: mutantBytes }[STATE];
const tip = readTip();
const rows = [];
const say = (line) => { rows.push(line); console.log(line); };

async function waitForDev(child) {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    const probe = spawnSync("node", ["-e",
      `fetch("http://127.0.0.1:${PORT}/").then(r=>process.stdout.write(String(r.status))).catch(()=>{})`],
      { encoding: "utf8" });
    if ((probe.stdout ?? "").trim() !== "") return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

mkdirSync(SHOTS, { recursive: true });

/* Pre-flight: a neighbour already listening on this port would make strictPort fail while
   waitForDev still gets an answer -- from the neighbour.  LISTENING only, because a TIME_WAIT
   socket from a run that already ended is not a server. */
const listening = spawnSync("netstat", ["-ano", "-p", "TCP"], { encoding: "utf8" }).stdout
  .split("\n").filter((l) => l.includes("LISTENING") && l.includes(`:${PORT} `));
if (listening.length) {
  console.error(`port ${PORT} is already LISTENING, refusing to read from a neighbour's server`);
  process.exit(3);
}

writeFileSync(TARGET, bytesFor, "utf8");
say(`0 state=${STATE} tip=${tip} bytes written sha=${sha(bytesFor)} (candidate on disk before swap was ${sha(candBytes)})`);

const vite = spawn(process.execPath, [path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js"),
  "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { cwd: FRONTEND, stdio: "ignore" });

try {
  if (!(await waitForDev(vite))) throw new Error(`vite did not answer on ${PORT}`);
  // Arm-lands-before-claiming: the module the server hands out must be the bytes this run wrote.
  const served = await (await fetch(`http://127.0.0.1:${PORT}/src/lib/failureAttribution.ts`)).text();
  if (!served.includes(SERVED_MARKER)) {
    throw new Error(`served module does not carry the ${STATE} marker ${SERVED_MARKER}; the screen would not be this state's bytes`);
  }
  say(`0b served module carries the ${STATE} marker, length ${served.length}`);
  const browser = await chromium.launch();
  for (const locale of ["zh-CN", "en"]) {
    /* serviceWorkers: block, because this app ships and registers one (e2e/qoder-sw-lifecycle.spec.ts
       exists for that fact).  With a controller in place the page answers from cached modules, which
       is exactly how the first three runs all painted the same words no matter which bytes were on
       disk -- the ruler read the server while the screen read the cache. */
    const context = await browser.newContext({ viewport: { width: 390, height: 844 },
      serviceWorkers: "block" });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 90)));
    await page.addInitScript(({ id, loc }) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", loc);
      localStorage.setItem("citynexus.demo.journey_id", id);
    }, { id: JOURNEY, loc: locale });
    /* Matched on the pathname, not on a wildcard pattern: a `**` pattern over the whole path also
       swallows the dev server's own module graph (the request layer lives under src/api/), which is
       how the first cut of this script produced a blank page -- the app's request module was replaced
       by the stub it was supposed to observe. */
    await page.route((url) => url.pathname.startsWith("/api/"), (r) => r.fulfill({ status: 200,
      contentType: "application/json", body: JSON.stringify({ detail: "lane stub" }) }));
    await page.route((url) => /^\/api\/v1\/journeys\/[^/]+\/experience$/.test(url.pathname), (r) => r.fulfill({
      status: 200, headers: { "content-type": "" }, body: "",
    }));
    await page.goto(`http://127.0.0.1:${PORT}/v8/hub`, { waitUntil: "load" });
    /* Prove the bytes the *page* fetched are this state's, before trusting a word it paints. */
    const inPage = await page.evaluate(async () => {
      const t = await (await fetch("/src/lib/failureAttribution.ts")).text();
      return { len: t.length, controller: !!(navigator.serviceWorker && navigator.serviceWorker.controller),
        readKey: t.includes('categoryLabel("UNKNOWN"'), readBrokenKey: t.includes('categoryLabel("UNKNOWX"'),
        literal: t.includes('?? "未知"') };
    });
    const matchesState = (STATE === "tip" && inPage.literal && !inPage.readKey)
      || (STATE === "cand" && inPage.readKey && !inPage.readBrokenKey)
      || (STATE === "mutant" && inPage.readBrokenKey);
    if (!matchesState) {
      throw new Error(`page-fetched bytes do not match state=${STATE}: ${JSON.stringify(inPage)}`);
    }
    say(`0c locale=${locale} page fetched module len=${inPage.len} swController=${inPage.controller} `
      + `readKey=${inPage.readKey} brokenKey=${inPage.readBrokenKey} literal=${inPage.literal} (matches state)`);
    const reason = page.getByTestId("failure-reason");
    let painted = "<not painted>";
    try {
      await reason.waitFor({ state: "visible", timeout: 25_000 });
      painted = (await reason.innerText()).replace(/\s+/g, " ").trim();
    } catch {
      const body = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").trim();
      painted = `<failure-reason never appeared; body starts: ${body.slice(0, 160)}>`;
    }
    const file = path.join(SHOTS, `${STATE}_${locale}.png`);
    await page.screenshot({ path: file, fullPage: false });
    const view = await page.getByTestId("failure-view").innerText().catch(() => "");
    say(`1 state=${STATE} locale=${locale} screen text = ${painted}`);
    say(`2   screenshot=${path.relative(REPO, file).replace(/\\/g, "/")} `
      + `view block=${view.replace(/\s+/g, " ").slice(0, 120)}`);
    say(`3   page errors: ${errors.length ? errors.join(" | ") : "none"}`);
    await context.close();
  }
  await browser.close();
} finally {
  vite.kill("SIGTERM");
  writeFileSync(TARGET, candBytes, "utf8");
  const back = sha(readFileSync(TARGET, "utf8"));
  say(`4 restored candidate bytes: sha=${back} expected=${sha(candBytes)} match=${back === sha(candBytes)}`);
}

writeFileSync(path.join(HERE, `screen_read_${STATE}_r1.txt`), rows.join("\n") + "\n", "utf8");
