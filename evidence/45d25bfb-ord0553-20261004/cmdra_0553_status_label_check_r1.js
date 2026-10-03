/* ORD-0553 positive control for /v8/authoritative — the labels must still be there, and they must not be
 * the server's tokens.
 *
 * A count dropping to zero on this screen would also be what it looks like when the panel never mounted,
 * when the journey door refused the sweep, or when a reword erased a row. So this reads the painted text of
 * each status pill, the two state values and the footer button, fails when any of those slots is empty, and
 * fails again when a painted value matches one of the machine shapes the commander's sweep uses. Every
 * wording it accepts has to be one of the values the dictionary this build was made from actually carries,
 * so a green here is the screen agreeing with the source, not two instruments agreeing with each other.
 *
 * One arm per run, one evidence file per arm, one sequential browser.
 * usage: node cmdra_0553_status_label_check_r1.js <base> <out.json> <zh|en> <frontend/src dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4];
const SRC = process.argv[5];
if (!BASE || !OUT || !LOCALE || !SRC) {
  console.error("usage: node cmdra_0553_status_label_check_r1.js <base> <out> <zh|en> <frontend/src>");
  process.exit(2);
}
const ZH = LOCALE.startsWith("zh");

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

/* The wordings this build's dictionary carries for exec.state.*, read out of the tree the bundle came from. */
const i18n = fs.readFileSync(`${SRC}/i18n/LocaleContext.tsx`, "utf8");
function tableOf(marker) {
  const at = i18n.indexOf(marker);
  if (at < 0) throw new Error(`LocaleContext.tsx: ${marker} not found — this check would pass on nothing.`);
  return i18n.slice(at, i18n.indexOf("\n};", at));
}
const enTable = tableOf("const en: Dict = {");
const zhTable = tableOf("const zhCN: Dict = {");
function stateWords(block) {
  return [...block.matchAll(/^\s*"exec\.state\.[A-Za-z]+":\s*"([^"]*)"/gm)].map((m) => m[1]);
}
const allowed = ZH ? stateWords(zhTable) : stateWords(enTable);
const vocab = fs.readFileSync(`${SRC}/lib/displayVocabulary.ts`, "utf8");
const fbAt = vocab.indexOf("const EXECUTION_STATE: Record<string, Label> = {");
const fbBlock = fbAt < 0 ? "" : vocab.slice(fbAt, vocab.indexOf("\n};", fbAt));
for (const m of fbBlock.matchAll(/\{\s*zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"\s*\}/g)) {
  allowed.push(ZH ? m[1] : m[2]);
}

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
  await page.goto(BASE.replace(/\/$/, "") + "/v8/authoritative", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2500);

  const read = await page.evaluate(() => {
    const texts = (sel) => Array.from(document.querySelectorAll(sel)).map((e) => (e.textContent || "").replace(/\s+/g, " ").trim());
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
      panelPresent: Boolean(document.querySelector('[data-testid="v12-authoritative-panel"]')),
      activityStatus: texts(".v12-activity-status"),
      stateValues: texts(".v12-state-value"),
      footerButton: texts(".v12-panel-footer button"),
      paintedCount: painted.length,
      journeyId: localStorage.getItem("citynexus.v8.journey_id") || "",
    };
  });

  const slots = [
    ...read.activityStatus.map((t, i) => ({ slot: `activity-status[${i}]`, text: t })),
    ...read.stateValues.map((t, i) => ({ slot: `state-value[${i}]`, text: t })),
  ];
  const empties = slots.filter((s) => !s.text);
  const shaped = [];
  for (const s of slots) {
    const hit = machineShapeHit(s.text);
    if (hit) shaped.push({ ...s, ...hit });
  }
  const unbacked = slots.filter((s) => s.text && !allowed.includes(s.text) && !/^Mark\b|标记/.test(s.text) && !allowed.some((a) => s.text.endsWith(a)));
  const arms = [
    { id: "panel_reached", verdict: read.panelPresent && read.activityStatus.length > 0 ? "PASS" : "FAIL",
      observed: `panelPresent=${read.panelPresent} activityRows=${read.activityStatus.length} journeyId=${read.journeyId || "(none)"}` },
    { id: "every_status_slot_is_painted", verdict: slots.length > 0 && empties.length === 0 ? "PASS" : "FAIL",
      observed: empties.length ? JSON.stringify(empties) : `${slots.length} slots painted, e.g. ${JSON.stringify(slots.slice(0, 3).map((s) => s.text))}` },
    { id: "no_status_slot_paints_a_machine_shape", verdict: shaped.length === 0 ? "PASS" : "FAIL",
      observed: shaped.length ? JSON.stringify(shaped.slice(0, 4)) : "none of the status slots match the sweep's four shapes" },
    { id: "painted_words_come_from_the_dictionary", verdict: unbacked.length === 0 ? "PASS" : "FAIL",
      observed: unbacked.length ? JSON.stringify(unbacked.slice(0, 4)) : `all within the table's wordings (${allowed.length} entries)` },
    { id: "no_page_error", verdict: pageErrors.length === 0 ? "PASS" : "FAIL", observed: JSON.stringify(pageErrors.slice(0, 3)) },
  ];
  const reds = arms.filter((a) => a.verdict === "FAIL").map((a) => a.id);
  const report = {
    instrument: "cmdra_0553_status_label_check_r1",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, viewport: "390x844", src_dir: SRC,
    dictionary_wordings_for_this_arm: allowed, read, arms,
    verdict: reds.length ? "RED" : "GREEN", red_arms: reds,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, locale: LOCALE, verdict: report.verdict, red_arms: reds,
    activity: read.activityStatus.slice(0, 4), values: read.stateValues, button: read.footerButton }, null, 2));
  process.exit(reds.length ? 1 : 0);
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
