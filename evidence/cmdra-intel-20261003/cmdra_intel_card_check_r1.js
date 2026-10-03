/* CMDR lane cmdra r1 — does /v8/intelligence still say something, and is it not a server enum?

   The acceptance ruler for this order is the commander's own machine-speech sweep, but a count going to
   0 can also mean "the card stopped rendering". This file is the positive control that distinguishes the
   two: it reads the painted text of the runtime card (`ControlTowerPanel.tsx:49`, testid
   `v17-runtime-status`) and fails when that text is empty, when it carries a machine shape, or when it is
   not one of the four wordings the vocabulary ships.

   One arm per run (`zh` or `en`), one evidence file per arm, one sequential browser — concurrent Chromium
   on this box makes the app count before it has painted.

   usage: node cmdra_intel_card_check_r1.js <base> <out.json> <zh|en> <frontend/src dir>
*/
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4];
const SRC = process.argv[5];
if (!BASE || !OUT || !LOCALE || !SRC) {
  console.error("usage: node cmdra_intel_card_check_r1.js <base> <out> <zh|en> <frontend/src>");
  process.exit(2);
}
const ZH = LOCALE.startsWith("zh");

/* The four shapes, verbatim from cmdr_machine_speech_sweep_r1.js:47-51. */
const SHAPES = [
  { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
  { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
  { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
  { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
];
const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT"];

function machineShapeHit(text) {
  for (const s of SHAPES) {
    const m = text.match(s.re);
    if (!m) continue;
    if (s.kind === "ALLCAPS_WORD" && ALLOW.includes(m[0])) continue;
    if (s.kind === "ALLCAPS_WORD" && /[_]/.test(m[0])) continue;
    return { kind: s.kind, token: m[0] };
  }
  return null;
}

/* The wordings this screen is allowed to paint, read out of the tree the bundle was built from so a copy
   edit cannot make the assertion vacuous. */
const vocab = fs.readFileSync(`${SRC}/lib/displayVocabulary.ts`, "utf8");
const at = vocab.indexOf("const RUNTIME_IDENTITY: Record<string, Label> = {");
const body = at < 0 ? "" : vocab.slice(at, vocab.indexOf("\n};", at));
const rows = [...body.matchAll(/^\s*([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\s*:\s*\{\s*zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"\s*,?\s*\}/gm)];
const allowed = rows.map((m) => (ZH ? m[2] : m[3]));

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  await page.goto(BASE.replace(/\/$/, "") + "/v8/intelligence", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2500);

  const read = await page.evaluate(() => {
    const card = document.querySelector('[data-testid="v17-runtime-status"]');
    const bold = card ? card.querySelector("b") : null;
    const painted = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const text = (n.nodeValue || "").trim();
      if (text.length < 3) continue;
      const el = n.parentElement;
      if (!el || el.closest("script,style,code,pre,noscript")) continue;
      const det = el.closest("details");
      if (det && !det.open) continue;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      if (rg.getClientRects().length === 0) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) continue;
      painted.push(text.slice(0, 120));
    }
    return {
      cardPresent: Boolean(card),
      cardText: card ? (card.textContent || "").replace(/\s+/g, " ").trim() : "",
      valueText: bold ? (bold.textContent || "").replace(/\s+/g, " ").trim() : "",
      paintedCount: painted.length,
      journeyId: localStorage.getItem("citynexus.v8.journey_id") || "",
      docChars: (document.body.innerText || "").length,
    };
  });

  const hits = [];
  const valueHit = machineShapeHit(read.valueText);
  if (valueHit) hits.push({ where: "runtime card value", ...valueHit, text: read.valueText });

  const arms = [
    { id: "card_reached", verdict: read.cardPresent ? "PASS" : "FAIL",
      observed: `cardPresent=${read.cardPresent} journeyId=${read.journeyId || "(none)"} paintedTextNodes=${read.paintedCount} documentChars=${read.docChars}` },
    { id: "value_is_painted_not_empty", verdict: read.valueText.trim().length > 0 ? "PASS" : "FAIL",
      observed: `painted value text = ${JSON.stringify(read.valueText)}` },
    { id: "value_carries_no_machine_shape", verdict: valueHit ? "FAIL" : "PASS",
      observed: valueHit ? JSON.stringify(valueHit) : `no shape in ${JSON.stringify(read.valueText)}` },
    { id: "value_is_one_of_the_shipped_wordings", verdict: allowed.includes(read.valueText) ? "PASS" : "FAIL",
      observed: `${JSON.stringify(read.valueText)} vs table wordings ${JSON.stringify(allowed)}` },
    { id: "no_page_error", verdict: pageErrors.length === 0 ? "PASS" : "FAIL", observed: JSON.stringify(pageErrors.slice(0, 3)) },
  ];
  const reds = arms.filter((a) => a.verdict === "FAIL").map((a) => a.id);
  const report = {
    instrument: "cmdra_intel_card_check_r1",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, viewport: "390x844", src_dir: SRC,
    shapes_reused_from: "cmdr_machine_speech_sweep_r1.js:47-51",
    table_wordings_for_this_arm: allowed, read, arms,
    verdict: reds.length ? "RED" : "GREEN", red_arms: reds,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, locale: LOCALE, verdict: report.verdict, red_arms: reds,
    painted_value: read.valueText }, null, 2));
  process.exit(reds.length ? 1 : 0);
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
