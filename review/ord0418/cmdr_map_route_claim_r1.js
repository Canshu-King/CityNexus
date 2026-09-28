/* CMDR ORD-0418 r1 -- is the map caption allowed to say "provider-backed route"?
 *
 * The claim lives in a `v8-sr-only` span: nobody sees it, a screen reader speaks it. So the assertion is
 * made on the text that would actually be read, and on proof that the element is readable at all
 * (computed style must not be display:none / visibility:hidden -- a clipped sr-only element is in the
 * accessibility tree, a hidden one is not). No data attribute is consulted anywhere.
 *
 * Three stages are run through the SAME instrument with the SAME expectations, so the counter-arm is a
 * real red and not a re-labelled pass:
 *   before  -- the tip: the sentence is unconditional, so the zero-legs journey fails the predicate.
 *   after   -- this branch: the claim only appears when route.length > 0.
 *   mutant  -- the condition deleted again (a throwaway build, never committed): must go red again.
 *
 * Cells: two journeys that differ exactly in whether a route can be drawn --
 *   sealed demo journey  : active_plan.legs 0, mobility_facts 0, provider_mesh.mobility.* all NOT_CONFIGURED
 *   journey 6cbdbc65-... : active_plan.legs 0, but one option whose 7 legs all resolve to a
 *                          mobility_fact with geometry  => route.length 7 > 0
 * Each in zh and en.
 *
 * Usage: node cmdr_map_route_claim_r1.js <base> <out-file> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:54434/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0419_20260929/probe/map_claim_after.json";
const LABEL = process.argv[4] || "after";
const CLAIM = { "zh-CN": "供应商支持的路线", en: "Provider-backed route" };
const ZERO_SENTENCE = { "zh-CN": "这里没有画路线", en: "No route is drawn" };
const NO_PROVIDER = { "zh-CN": "没有配置算路服务", en: "no routing provider configured" };
const NOT_ROUTED = { "zh-CN": "图上不存在来自算路服务的路线", en: "came from a routing provider" };
const JOURNEYS = { "legs-zero": "22222222-2222-4222-8222-222222222222", "legs-seven": "6cbdbc65-904a-40c7-a778-f981690f25d0" };

async function readCaption(page, locale) {
  return page.evaluate(({ claim, zero, noProvider, notRouted }) => {
    const cap = document.querySelector(".v8-map-caption");
    if (!cap) return { caption_present: false };
    const spans = Array.from(cap.querySelectorAll("span")).map((s) => {
      const cs = getComputedStyle(s);
      return { cls: s.className, text: (s.textContent || "").trim(),
               speakable: cs.display !== "none" && cs.visibility !== "hidden" && cs.contentVisibility !== "hidden" };
    });
    const spoken = spans.filter((s) => s.speakable).map((s) => s.text).join(" ");
    const bold = cap.querySelector("b");
    return { caption_present: true, spoken, legs_said: bold ? (bold.textContent || "").trim() : null,
             spans, has_claim: spoken.includes(claim), has_zero_sentence: spoken.includes(zero),
             /* which of the two zero-legs sentences actually fired -- the order asks the replacement to
                name WHY there are no legs, so "a sentence appeared" is not enough */
             which_sentence: spoken.includes(noProvider) ? "noRouteNoProvider"
               : spoken.includes(notRouted) ? "noRouteNotRouted" : (spoken.includes(zero) ? "unknown" : "none") };
  }, { claim: CLAIM[locale], zero: ZERO_SENTENCE[locale], noProvider: NO_PROVIDER[locale],
       notRouted: NOT_ROUTED[locale] });
}

async function cell(browser, journeyKey, locale) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  const rec = { label: LABEL, journey: journeyKey, arm: locale, errors };
  try {
    await page.addInitScript(([key, id]) => { try { localStorage.setItem(key, id); } catch (e) {} },
                             ["citynexus.v8.journey_id", JOURNEYS[journeyKey]]);
    await page.goto(`${BASE}/v8/map`, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(3500); }
    if (locale === "en") {
      const lang = page.locator("[data-testid='topbar-language']").first();
      if ((await lang.innerText()).trim() === "EN") { await lang.click(); await page.waitForTimeout(1200); }
    }
    await page.goto(`${BASE}/v8/map`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2500);
    rec.reading = await readCaption(page, locale);
    rec.server = await page.evaluate(() => {
      const el = document.querySelector("[data-testid='v8-map-panel']");
      return { panel_present: !!el };
    });
    /* the predicate the order sets: the claim may be spoken only when a route exists */
    const legs = parseInt(String(rec.reading.legs_said || "0").replace(/\D+/g, ""), 10) || 0;
    rec.route_length_said = legs;
    rec.verdict = {
      claim_only_when_route_exists: legs > 0 ? rec.reading.has_claim : !rec.reading.has_claim,
      zero_case_names_the_reason: legs > 0 || rec.reading.has_zero_sentence,
      zero_case_names_the_cause: legs > 0 || rec.reading.which_sentence !== "none" && rec.reading.which_sentence !== "unknown",
      caption_speakable: rec.reading.caption_present && rec.reading.spans.some((s) => s.speakable && s.text),
    };
    rec.pass = Object.values(rec.verdict).every(Boolean);
  } catch (e) {
    rec.fatal = String(e).slice(0, 200);
    rec.pass = false;
  }
  rec.errors = errors;
  await page.screenshot({ path: OUT.replace(/\.json$/, "") + `_${LABEL}_${journeyKey}_${locale}.png` });
  await page.close();
  console.log("%s %-11s %-5s legs_said=%-3s claim=%-5s zero_sentence=%-5s speakable=%-5s => %s%s",
              LABEL, journeyKey, locale, rec.route_length_said, rec.reading && rec.reading.has_claim,
              rec.reading && rec.reading.has_zero_sentence, rec.reading && rec.reading.caption_present,
              rec.pass ? "PASS" : "FAIL", rec.fatal ? " FATAL=" + rec.fatal.slice(0, 70) : "");
  if (!rec.pass) console.log("      red at:", JSON.stringify(rec.verdict), "| spoken:", JSON.stringify((rec.reading || {}).spoken || "").slice(0, 150));
  return rec;
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const j of Object.keys(JOURNEYS)) for (const l of ["zh-CN", "en"]) results.push(await cell(browser, j, l));
  const failing = results.filter((r) => !r.pass).length;
  fs.writeFileSync(OUT, JSON.stringify({ at: new Date().toISOString(), base: BASE, label: LABEL,
                                         journeys: JOURNEYS, failing, results }, null, 1), "utf-8");
  console.log("%s cells=%d failing=%d -> %s", LABEL, results.length, failing, OUT);
  await browser.close();
  process.exit(failing ? 3 : 0);
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
