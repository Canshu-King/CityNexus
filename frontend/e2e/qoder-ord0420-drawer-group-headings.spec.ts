/**
 * ORD-0420 -- the drawer's four group headings are read off the screen, in both language arms.
 *
 * The defect: `frontend/src/app/V8Experience.tsx` painted the route registry's machine code
 * (`item.group` = TODAY / PLAN / TRAVEL / SYSTEM) straight into the heading, while every label under
 * it went through the dictionary. On the Chinese arm those four were therefore the only untranslated
 * text on the whole screen; on the English arm the same four looked correct by coincidence, which is
 * why the fix has to be evidenced as "the screen moved with the dictionary", not "the words match".
 *
 *   A1 zh arm at 390x844: the four headings all carry CJK, and Latin-only count is 0;
 *   A2 en arm: the four headings are still exactly the four words travellers read before this change,
 *      so the English screen cannot have moved;
 *   A3 both arms: the drawer's kicker and close button still read from the dictionary (the control
 *      that shows the bug was specific to the headings, not to the whole drawer).
 *
 * The readings are rendered text (`allTextContents`), never a data attribute or a dictionary key.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";

type Arm = {
  locale: string;
  lang: string | null;
  sealText: string | null;
  drawerOpen: number;
  headings: string[];
  kicker: string[];
  close: string[];
  rows: string[];
};

const LATIN_ONLY = /^[\x20-\x7e]+$/;
const CJK = /[一-鿿]/;

async function readArm(browser: Browser, locale: string): Promise<Arm> {
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale,
  });
  const page: Page = await ctx.newPage();
  const out: Arm = {
    locale,
    lang: null,
    sealText: null,
    drawerOpen: 0,
    headings: [],
    kicker: [],
    close: [],
    rows: [],
  };
  try {
    await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
    out.lang = await page.evaluate(() => document.documentElement.lang || null);
    for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                        page.getByText(/sealed demo/i).first()]) {
      if (await cand.count()) {
        out.sealText = (await cand.textContent() || "").trim().slice(0, 40);
        await cand.click();
        await page.waitForTimeout(4000);
        break;
      }
    }
    const ham = page.locator('[aria-controls="v8-nav-drawer"]');
    if (await ham.count()) {
      await ham.first().click();
      await page.waitForTimeout(1200);
    }
    const drawer = page.locator("#v8-nav-drawer");
    out.drawerOpen = await drawer.count();
    if (out.drawerOpen) {
      out.headings = await drawer.locator(".v8-nav-group").allTextContents();
      out.kicker = await drawer.locator(".v8-kicker").allTextContents();
      out.close = await drawer.locator(".v8-quiet-button").allTextContents();
      out.rows = (await drawer.locator("button span").allTextContents()).map((s) => s.trim());
    }
  } finally {
    await ctx.close();
  }
  return out;
}

function report(arm: Arm): string {
  const latin = arm.headings.filter((s) => LATIN_ONLY.test(s.trim())).length;
  const cjk = arm.headings.filter((s) => CJK.test(s)).length;
  return [
    "headings=" + JSON.stringify(arm.headings),
    "heading_count=" + arm.headings.length,
    "latin_only=" + latin,
    "with_cjk=" + cjk,
    "lang=" + arm.lang,
    "drawer_open=" + arm.drawerOpen,
    "kicker=" + JSON.stringify(arm.kicker),
    "close=" + JSON.stringify(arm.close),
    "row_count=" + arm.rows.length,
    "seal=" + JSON.stringify(arm.sealText),
  ].join(" ");
}

test("Q420 A1 the four drawer headings are Chinese on the zh arm", async ({ browser }) => {
  const arm = await readArm(browser, "zh");
  console.log("Q420 A1 zh " + report(arm));
  expect(arm.drawerOpen, "the drawer has to be open before any heading can be read").toBe(1);
  expect(arm.headings.length, "the four groups are TODAY PLAN TRAVEL SYSTEM").toBe(4);
  expect(arm.headings.filter((s) => LATIN_ONLY.test(s.trim())),
    "no heading may still be a Latin machine code").toEqual([]);
  for (const h of arm.headings) expect(CJK.test(h), "each heading must carry a Han character: " + h).toBe(true);
});

test("Q420 A2 the en arm still shows the four words it showed before", async ({ browser }) => {
  const arm = await readArm(browser, "en");
  console.log("Q420 A2 en " + report(arm));
  expect(arm.drawerOpen, "the drawer has to be open before any heading can be read").toBe(1);
  expect(arm.headings, "the English screen must not move: these are the words already shipped")
    .toEqual(["TODAY", "PLAN", "TRAVEL", "SYSTEM"]);
});

test("Q420 A3 the drawer's own neighbours stay dictionary-fed on both arms", async ({ browser }) => {
  const zh = await readArm(browser, "zh");
  const en = await readArm(browser, "en");
  console.log("Q420 A3 zh " + report(zh));
  console.log("Q420 A3 en " + report(en));
  expect(zh.kicker, "the zh kicker was already translated, so it is the control for A1")
    .toEqual(["全部路由"]);
  expect(zh.close, "the zh close button was already translated").toEqual(["关闭"]);
  expect(en.kicker, "the en kicker is the same pair read in English").toEqual(["All routes"]);
  expect(en.close, "the en close button is the same pair read in English").toEqual(["Close"]);
});
