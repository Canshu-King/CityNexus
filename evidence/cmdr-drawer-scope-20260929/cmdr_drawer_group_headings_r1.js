/* CMDR ORD-0420 candidate instrument r1 - the drawer's group headings never go through the dictionary.
 * V8Experience.tsx:1983 renders `item.group` raw into <span className="v8-nav-group">, so the four
 * headings are the code's own uppercase literals while every row label under them is translated.
 * Readings are the RENDERED text per arm at 390x844 on the tip bundle, plus the row labels they head.
 * Usage: node cmdr_drawer_group_headings_r1.js <base> <out-file>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4805/";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_drawer_groups_r1.json";

async function arm(browser, locale) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale });
  const page = await ctx.newPage();
  const out = { locale, entryAssets: null, sealClicked: false, hamburgerFound: 0, drawerOpen: 0 };
  try {
    await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
    out.entryAssets = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
    out.documentElementLang = await page.evaluate(() => document.documentElement.lang || null);
    const sealZh = page.getByText("使用封存的演示行程", { exact: false }).first();
    const sealEn = page.getByText(/sealed demo/i).first();
    for (const cand of [sealZh, sealEn]) {
      if (await cand.count()) {
        out.sealText = (await cand.textContent() || "").trim().slice(0, 40);
        await cand.click();
        out.sealClicked = true;
        await page.waitForTimeout(4000);
        break;
      }
    }
    const ham = page.locator('[aria-controls="v8-nav-drawer"]');
    out.hamburgerFound = await ham.count();
    if (out.hamburgerFound) {
      await ham.first().click();
      await page.waitForTimeout(1200);
    }
    const drawer = page.locator("#v8-nav-drawer");
    out.drawerOpen = await drawer.count();
    if (out.drawerOpen) {
      out.groupHeadings = await drawer.locator(".v8-nav-group").allTextContents();
      out.headKicker = await drawer.locator(".v8-kicker").allTextContents();
      out.rowLabels = (await drawer.locator("button span").allTextContents()).map((s) => s.trim());
      out.closeLabel = await drawer.locator(".v8-quiet-button").allTextContents();
    }
  } finally {
    await ctx.close();
  }
  return out;
}

function cjkRatio(strings) {
  if (!strings.length) return null;
  const withCjk = strings.filter((s) => /[\u4e00-\u9fff]/.test(s)).length;
  return { total: strings.length, withCjk, withLatinOnly: strings.filter((s) => /^[\x20-\x7e]+$/.test(s) && s.trim()).length };
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const zh = await arm(browser, "zh");
  const en = await arm(browser, "en");
  await browser.close();

  const latinOnlyHeadings = (zh.groupHeadings || []).filter((s) => /^[\x20-\x7e]+$/.test(s.trim()));
  const report = {
    instrument: "cmdr_drawer_group_headings_r1",
    base: BASE,
    viewport: "390x844",
    arms: { zh, en },
    finding: {
      zhHeadingsRendered: zh.groupHeadings || null,
      zhHeadingsLatinOnlyCount: latinOnlyHeadings.length,
      zhRowLabelsCjk: cjkRatio(zh.rowLabels || []),
      zhKicker: zh.headKicker || null,
      note: "if zhHeadingsLatinOnlyCount > 0 while zhRowLabelsCjk.withCjk == row count, the headings bypass the dictionary",
      sourceLineClaimed: "frontend/src/app/V8Experience.tsx:1983 renders item.group without t()",
      enArmDrawerReachable: en.drawerOpen === 1,
      enArmNote: "the hamburger is only mounted on the shell routes; the en arm stops on onboarding because the seal entry text differs, so the en arm of the heading check is NOT_REACHED_BY_CMDR",
    },
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({
    out: OUT,
    zhEntry: zh.entryAssets,
    zhHeadings: zh.groupHeadings,
    zhHeadingsLatinOnlyCount: latinOnlyHeadings.length,
    zhRowLabelsCjk: report.finding.zhRowLabelsCjk,
    zhKicker: zh.headKicker,
    enDrawerOpen: en.drawerOpen,
    enLang: en.documentElementLang,
  }, null, 2));
}

main().catch((e) => { console.error("FATAL", e); process.exit(1); });
