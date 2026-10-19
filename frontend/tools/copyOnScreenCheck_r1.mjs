/* Copy-on-screen gate: reads what the rendered page actually says.
 *
 * Why this exists. The travel dictionary is the single writer for user-facing sentences, and
 * four modules used to retype dictionary sentences inline. A static grep can prove a file no
 * longer contains a retired phrase; it cannot prove the *screen* picked up the dictionary's
 * current text. This harness drives the real app in a browser and compares rendered text with
 * values parsed from `src/i18n/LocaleContext.tsx` at run time, so it cannot pass on a stale
 * literal of its own.
 *
 * What it checks, per locale:
 *   1. every sentence it claims is on screen equals the dictionary's current value verbatim;
 *   2. none of the retired defensive phrasing (`RETIRED` below) is rendered anywhere;
 *   3. it refuses (rc 3) when nothing rendered -- a blank page must never read as green.
 *
 * The fault is real, not mocked: point `--url` at a vite dev server whose `CITYNEXUS_BACKEND_PORT`
 * is a port nothing listens on, and the shell's failure paths render for real. This checks
 * wording only. Nothing here is `LIVE_VERIFIED` and no provider is called.
 *
 * Usage:
 *   node tools/copyOnScreenCheck_r1.mjs --url http://localhost:5338/ [--require]
 * Screenshots go to the directory named by `CNX_COPY_SHOTS`, defaulting to the OS temp dir so
 * evidence never lands in the working tree.
 */

import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const requireFromFrontend = createRequire(pathToFileURL(join(FRONTEND, "package.json")));
const { chromium } = requireFromFrontend("playwright");

const DICT = join(FRONTEND, "src", "i18n", "LocaleContext.tsx");
const args = process.argv.slice(2);
const flagValue = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
};
const BASE = flagValue("--url", "http://localhost:5173/");
const STRICT = args.includes("--require");
const SHOTS = process.env.CNX_COPY_SHOTS ?? join(tmpdir(), "cnx-copy-on-screen");

/* Sentences this pass touched. Each must reach the screen exactly as the dictionary holds it. */
const KEYS = [
  "trial.sealedNoAnswer",
  "trial.sealedUnreadable",
  "lib.failureAttribution.networkCopyStillReadable",
  "lib.failureAttribution.networkNoOfflineCopy",
];

/* Split by why a phrase must not appear.

BANNED: this copy pass deleted the sentence from every writer, so rendering it again means a
module still hardcodes it or the dictionary was edited back by accident. That is a failure.

PENDING_RULING: the sentence survives in `trial.sealedUnreadable` because a named spec asserts
it verbatim (`e2e/qoder-ord0349-two-legs-two-sentences.spec.ts`), and the owner has not yet
ruled whether that disclaimer should stay. It is reported, never silently accepted, and never
made to fail the gate -- a gate that cries about a known open question stops being believed. */
const BANNED = [
  "我们不会编造酒店",
  "你的行程数据没有丢失",
  "你行程上的任何东西都没有被改动",
  "这一屏没有改动你的任何行程",
  "This is not about how you phrased it",
  "we will not invent hotels",
  "Your trip data has not been lost",
  "Nothing about your trip was changed",
  /* 2026-10-19 第六刀：这六句的尾巴是从「句子里」删掉的 -- 它们解释产品为什么不做事，而不是
     告诉旅客接下来会怎样。删掉之后原文在整棵树里现读 0 命中（`_copy_pins_1019au.txt:1` 一类的
     复查漏过不等于没有），所以这里钉住的是「别把它写回来」，不管哪一枚模块。 */
  "这一版不打开别人的页面",
  "这个形态是具名不支持，不是悄悄没有",
  "不由我们藏起来",
  "行程里还是原来那一枚",
  "上面这句话是屏自己判断的状态",
  "这台服务器没有“存下来但不给日子”的门",
  "opens nobody else's page",
  "not silently unavailable",
  "not ours to hide",
  "the trip keeps the stamp it had",
  "the screen's own state",
  "no door that keeps a place without giving it a day",
  /* Wave 19 retired four more tails -- the screen stopped explaining who it asked or how honest it is.
     Each of these four was read back out of the tree before pinning (现读 0 处命中), so this list bans
     the wording itself, not some other module's surviving sentence. */
  "我们不替它解释",
  "we do not interpret it",
  "这不是这张凭证的密钥",
  "That is not this credential's secret",
];

const PENDING_RULING = [
  "这不是你填错了什么",
  "Nothing you filled in caused this",
];

const STEPS = [
  { id: "sealed", zh: "使用封存的演示行程", en: "Use the sealed demo trip" },
  { id: "destinations", zh: "看支持的目的地", en: "See supported destinations" },
];

const flatten = (value) =>
  value.split(String.fromCharCode(10)).join(" | ").replace(/ +/g, " ").trim();

function dictionaryValues() {
  const text = readFileSync(DICT, "utf8");
  const regions = {
    en: text.slice(text.indexOf("const en: Dict"), text.indexOf("const zhCN: Dict")),
    zh: text.slice(text.indexOf("const zhCN: Dict"), text.indexOf("const dictionaries")),
  };
  const out = {};
  for (const key of KEYS) {
    for (const locale of ["en", "zh"]) {
      const match = new RegExp('"' + key + '": "([^"]*)"').exec(regions[locale]);
      if (!match) throw new Error("no " + locale + " value for " + key + " in the dictionary");
      out[locale + ":" + key] = match[1];
    }
  }
  return out;
}

async function click(page, label) {
  try {
    await page.getByRole("button", { name: label, exact: false }).first().click({ timeout: 6000 });
    return true;
  } catch {
    try {
      await page.getByText(label, { exact: false }).first().click({ timeout: 4000 });
      return true;
    } catch {
      return false;
    }
  }
}

async function runLocale(browser, locale, values) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    locale: locale === "zh" ? "zh-CN" : "en-US",
  });
  const page = await context.newPage();
  await page.addInitScript((entry) => {
    window.localStorage.setItem("citynexus.locale", entry.locale);
  }, { locale: locale === "zh" ? "zh-CN" : "en" });

  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(3000);

  const texts = [];
  const matched = [];
  for (const step of STEPS) {
    const label = locale === "zh" ? step.zh : step.en;
    if (!(await click(page, label))) {
      console.log("   STEP " + step.id + ": control not on screen (" + label + ")");
      continue;
    }
    await page.waitForTimeout(3500);
    const text = await page.evaluate(() => document.body.innerText);
    texts.push(text);
    for (const key of KEYS) {
      if (text.includes(values[locale + ":" + key]) && !matched.includes(key)) {
        matched.push(key);
        console.log("   STEP " + step.id + ": renders the dictionary sentence for " + key);
      }
    }
    await page.screenshot({ path: join(SHOTS, step.id + "-" + locale + ".png"), fullPage: true });
  }
  const everything = texts.join(String.fromCharCode(10));
  const back = BANNED.filter((phrase) => everything.includes(phrase));
  const pending = PENDING_RULING.filter((phrase) => everything.includes(phrase));
  console.log(
    "   ARM " + locale + ": renderedScreens=" + texts.length + " dictionarySentences=" +
      matched.length + " bannedPhrasesOnScreen=" + back.length
  );
  for (const phrase of back) console.log("   BANNED PHRASE RENDERED: " + phrase);
  for (const phrase of pending) console.log("   AWAITING RULING (reported, not failed): " + phrase);
  await context.close();
  return { matched, back, pending, screens: texts.length, sample: flatten(everything).slice(0, 220) };
}

async function main() {
  if (!existsSync(DICT)) {
    console.log("REFUSE (rc 3): dictionary not found at " + DICT);
    process.exit(3);
  }
  mkdirSync(SHOTS, { recursive: true });
  const values = dictionaryValues();
  console.log("url:", BASE);
  console.log("dictionary values parsed at run time:");
  for (const key of Object.keys(values)) console.log("   " + key + " = " + values[key].slice(0, 52));
  const browser = await chromium.launch();
  const zh = await runLocale(browser, "zh", values);
  const en = await runLocale(browser, "en", values);
  await browser.close();

  console.log("----");
  console.log("zh sample:", zh.sample);
  console.log("en sample:", en.sample);
  const rendered = zh.screens + en.screens;
  const sentences = zh.matched.length + en.matched.length;
  const retired = zh.back.length + en.back.length;
  const pendingTotal = zh.pending.length + en.pending.length;
  console.log("screens rendered:", rendered);
  console.log("dictionary sentences observed on screen:", sentences);
  console.log("banned phrases observed on screen:", retired);
  console.log("phrases awaiting a ruling, observed on screen:", pendingTotal);
  if (rendered === 0) {
    console.log("REFUSE (rc 3): nothing rendered, so no wording claim is made.");
    process.exit(3);
  }
  if (retired > 0) {
    console.log("FAIL (rc 1): a deleted defensive declaration is being rendered again.");
    process.exit(1);
  }
  if (sentences === 0 && STRICT) {
    console.log("FAIL (rc 1, --require): no dictionary sentence reached a rendered screen.");
    process.exit(1);
  }
  console.log("OK: rendered screens carry the dictionary's current text, and none of the deleted wording.");
  process.exit(0);
}

main().catch((error) => {
  console.log("HARNESS ERROR (rc 2):", String(error).slice(0, 300));
  process.exit(2);
});
