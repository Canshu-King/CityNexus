/* Walk the four traveller tabs in a real browser and measure how much text they hand the user.

   The objective this serves is "make the UI simpler: drop the waffle, the defensive statements and
   the unnecessary declarations". That is only arguable with a number attached, so this prints one
   per screen, in both languages: visible characters, how many explanatory blocks the screen stacks
   (lede / muted / hint / alert / notice / message), and how many buttons it offers.

   It also checks the copy work itself. Every key listed in WATCH is read from
   `src/i18n/LocaleContext.tsx` at run time -- never from a literal in this file -- and the harness
   reports whether the dictionary's current wording actually reached a rendered screen. A key whose
   value carries `{plural:}` or another parameter is judged on the stable text before the first
   brace, and says so, because matching a template against its expanded output would be a false
   green in one direction and a false red in the other.

   Order of operations, disclosed: this run is the measurement that chooses which keys can be
   claimed as on-screen; the claim list is then pinned in the committed copy of the harness so a
   later edit that deletes a reader shows up as a red. Nothing here is `LIVE_VERIFIED` and no
   provider is called: the backend answers from the seeded demo store.

   Each tab is measured twice -- as the traveller lands on it, and after every `aria-expanded=false`
   layer on it has been opened -- because a sentence behind a disclosure is not "on screen" and a
   control behind one is not "unreachable". The two numbers are also the 简洁 metric: how much text
   the screen hands over by default, and how much it hides until asked.

   Usage: node tools/tripTabsWalkCheck_r1.mjs --url http://localhost:5337/ --journey <id> [--expect k:v,k:v]
*/

import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const DICT = join(FRONTEND, "src", "i18n", "LocaleContext.tsx");
const requireFromFrontend = createRequire(pathToFileURL(join(FRONTEND, "package.json")));
const { chromium } = requireFromFrontend("playwright");

const NL = String.fromCharCode(10);
const arg = (name, fallback) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
};
const BASE = arg("--url", "http://localhost:5337/");
const JOURNEY = arg("--journey", "");
const SHOTS = arg("--shots", process.env.CNX_COPY_SHOTS ?? join(tmpdir(), "cnx-trip-tabs-walk"));
const EXPECT = (arg("--expect", "") || "")
  .split(",")
  .filter(Boolean)
  .map((pair) => {
    const [tab, key] = pair.split(":");
    return { tab, key };
  });

const TABS = (arg("--only", "") || "itinerary,stay,bookings,spend").split(",");
/* Which side of the stay tab this run is on. The seeded one-day trip cannot get stay options -- the
   server answers `NOT_APPLICABLE_ZERO_NIGHTS` by name -- so the empty branch is what it shows; a
   two-night journey shows the comparison list instead. One flag says which set of sentences this run
   is allowed to claim, so neither arm can borrow the other's green. */
const STAY_BRANCH = arg("--branch", "empty");
const WANT_WALLET = !process.argv.includes("--no-wallet");

/* Keys this copy campaign moved, retired or re-pointed at the dictionary.

   `always` = the branch every traveller lands on for a seeded trip with no bookings and no provider
   answer, so a failure here means a reader was detached. `sometimes` = a branch this run cannot
   reach (a loading state, a stay list that needs a provider, a disrupted stop). Those are reported,
   never claimed: pretending a branch rendered because its key exists would be exactly the false
   green this harness was built to avoid. */
const WATCH = {
  itinerary: {
    always: ["itinerary.dayByDay"],
    disclosure: [],
    sometimes: [
      "itinerary.weekLabel",
      "itinerary.stopCount",
      "itinerary.stopDisrupted",
      "itinerary.emptyReadingPlaces",
      "itinerary.lengthUnknown",
      "itinerary.emptyTitle",
    ],
  },
  stay: {
    always: [
      "hub.stayLabel",
      "stay.noneToCompare",
      "hub.stayOutcomeUnknown",
      "stay.reacquire",
      "stay.anotherCity",
    ],
    disclosure: [],
    // The comparison branch needs stay options, which no provider answers for on a clean store.
    sometimes: [
      "stay.chooseTitle",
      "stay.rankedCount",
      "stay.priceLabel",
      "stay.pricePerNight",
      "stay.priceUnavailable",
      "stay.walkingLabel",
      "stay.cancellationLabel",
      "stay.whyLabel",
      "stay.chosenLabel",
      "stay.choose",
    ],
  },
  bookings: {
    always: [],
    // Measured, not assumed: the 预订 tab of this workspace is the journey inbox. The wallet face
    // (`v8-bookings`, with `bookings.kicker` / `bookings.title` / `bookings.lede` / `bookings.noStay`)
    // is mounted by the standalone `route === "bookings"` screen in `app/v8PanelRegistry.tsx`, and
    // opening every `aria-expanded=false` layer on this tab did not bring it on screen. So those
    // four keys are reported as not-reachable-here, and the shell route that owns them is walked
    // separately -- claiming them from this tab would be a false green.
    disclosure: [],
    sometimes: [
      "bookings.kicker",
      "bookings.title",
      "bookings.lede",
      "bookings.noStay",
      "bookings.priceUnknown",
      "bookings.notChosen",
      "bookings.stayEvidence",
    ],
  },
  spend: {
    always: ["spend.emptyBody"],
    disclosure: [],
    sometimes: [],
  },
};

/* The stay tab's two branches, chosen by --branch: whichever list this run cannot reach becomes the
   reported set, and the set it does reach becomes the claim. */
/* Two of the comparison-branch labels need more than a stay list: 「/ 晚」 needs an option that
   carries a price (the seeded catalogue returns one without, so the screen says 暂无价格 instead),
   and 已选择这家 needs a stay the traveller has chosen. Measured, not assumed -- both read NOT
   RENDERED on a one-option seeded list -- so they stay reported rather than claimed. */
const NEEDS_MORE = ["stay.pricePerNight", "stay.chosenLabel"];

if (STAY_BRANCH === "comparison") {
  const stay = WATCH.stay;
  WATCH.stay = {
    always: stay.sometimes.filter((key) => !NEEDS_MORE.includes(key)),
    disclosure: [],
    sometimes: [...stay.always, ...stay.sometimes.filter((key) => NEEDS_MORE.includes(key))],
  };
}

/* A kicker styled with `text-transform: uppercase` reports different *innerText* than the
   dictionary's value, which is a stylesheet fact, not a wording fact. Folding the comparison keeps
   the claim about the words; the screenshot still shows the case the traveller sees. */
const fold = (value) => value.toLowerCase();

function dictionaryRegions() {
  const text = readFileSync(DICT, "utf8");
  const enStart = text.indexOf("const en: Dict");
  const zhStart = text.indexOf("const zhCN: Dict");
  const end = text.indexOf("const dictionaries");
  if (!(enStart >= 0 && zhStart > enStart && end > zhStart)) {
    throw new Error("dictionary layout changed: locale block anchors not found");
  }
  return { en: text.slice(enStart, zhStart), zh: text.slice(zhStart, end) };
}

/** Current value of one key in one locale, parsed now so the harness cannot pass on its own stale literal. */
function valueOf(regions, locale, key) {
  const match = new RegExp('"' + key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + '": "([^"]*)"')
    .exec(regions[locale]);
  return match ? match[1] : null;
}

/** The part of a value a screen can be matched against verbatim: the stable text beside any `{param}`. */
function probe(value) {
  const open = value.indexOf("{");
  const parameterised = open >= 0;
  let fragment = parameterised ? value.slice(0, open) : value;
  let side = "before the template";
  if (fragment.replace(/\s+/g, "").length < 2 && parameterised) {
    const close = value.lastIndexOf("}");
    fragment = close >= 0 ? value.slice(close + 1) : "";
    side = "after the template";
  }
  const text = fragment.replace(/\s+/g, " ").trim();
  // A two-character label like 「价格」 is matched, but it is a weak match: the report says so
  // instead of lending it the confidence of a full sentence.
  return { text, judgable: text.length >= 2, parameterised, side, weak: text.length < 4 };
}

async function reachTrips(page) {
  const present = async () => (await page.locator("#trips-tab-itinerary").count()) > 0;
  if (await present()) return "already";
  const direct = page.locator('[data-testid="nav-trips"]');
  if ((await direct.count()) > 0) {
    await direct.first().click({ timeout: 6000 });
    await page.waitForTimeout(2500);
    if (await present()) return "nav-trips";
  }
  const menu = page.locator('[data-testid="v8-mobile-menu"]');
  if ((await menu.count()) > 0) {
    await menu.first().click({ timeout: 6000 });
    await page.waitForTimeout(900);
    if ((await direct.count()) > 0) {
      await direct.first().click({ timeout: 6000 });
      await page.waitForTimeout(2500);
      if (await present()) return "drawer+nav-trips";
    }
  }
  return null;
}

async function describeFailure(page) {
  // An instrument that only says "it did not work" is worse than a silent one.
  return page.evaluate(() => {
    const visible = (node) => {
      const style = window.getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden") return false;
      const box = node.getBoundingClientRect();
      return box.width > 1 && box.height > 1;
    };
    const buttons = Array.from(document.querySelectorAll("button"))
      .filter(visible)
      .slice(0, 40)
      .map((node) => (node.getAttribute("data-testid") || "") + " " + node.innerText.replace(/\s+/g, " ").trim().slice(0, 24));
    return {
      url: window.location.href,
      testIds: Array.from(document.querySelectorAll("[data-testid]"))
        .map((node) => node.getAttribute("data-testid"))
        .slice(0, 40),
      buttons,
      body: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 160),
    };
  });
}

/* The standalone 票夹 / wallet screen, reached through the drawer the same way a traveller does.

   Its nav label is read from the dictionary at run time, because this branch's whole claim is that
   the screen's words come from there -- a hardcoded label in this file would pass while the product
   renamed the button. */
const WALLET_KEYS = [
  "bookings.kicker",
  "bookings.title",
  "bookings.lede",
  "bookings.importNote",
  "bookings.noStay",
];

async function walkWallet(page, regions, locale) {
  const label = valueOf(regions, locale, "nav.bookings");
  if (!label) {
    console.log("   wallet route: nav.bookings has no dictionary value, so it was not attempted.");
    return { reached: false, observations: [] };
  }
  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(5000);
  const menu = page.locator('[data-testid="v8-mobile-menu"]');
  if ((await menu.count()) > 0) {
    await menu.first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(900);
  }
  const nav = page.locator("#v8-nav-drawer").getByRole("button", { name: label, exact: true });
  let reached = false;
  if ((await nav.count()) > 0) {
    await nav.first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(2500);
    reached = (await page.locator('[data-testid="v8-bookings"]').count()) > 0;
  }
  if (!reached) {
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll("button"))
        .map((node) => node.innerText.replace(/\s+/g, " ").trim())
        .filter(Boolean)
        .slice(0, 30)
    );
    console.log(`   wallet route: NOT REACHED via label "${label}"; buttons on page: ${visible.join(" | ").slice(0, 260)}`);
    return { reached: false, observations: [] };
  }
  const text = (await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ");
  const chars = text.trim().length;
  const observations = [];
  for (const key of WALLET_KEYS) {
    const value = valueOf(regions, locale, key);
    const p = probe(value === null ? "" : value);
    observations.push({
      key,
      state: value !== null && p.judgable && fold(text).includes(fold(p.text)) ? "ON SCREEN" : "NOT RENDERED",
      value: p.text,
    });
  }
  console.log(`   wallet route: reached, chars=${chars}`);
  for (const item of observations) {
    console.log(`      wallet | ${item.state}: ${item.key} = ${item.value}`);
  }
  await page.screenshot({ path: join(SHOTS, `wallet-${locale}.png`), fullPage: true });
  return { reached: true, observations };
}

async function walk(browser, locale) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    locale: locale === "zh" ? "zh-CN" : "en-US",
  });
  const page = await context.newPage();
  await page.addInitScript((entry) => {
    window.localStorage.setItem("citynexus.locale", entry.locale);
    window.localStorage.setItem("citynexus.v8.journey_id", entry.journey);
  }, { locale: locale === "zh" ? "zh-CN" : "en", journey: JOURNEY });

  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(6000);

  const route = await reachTrips(page);
  if (!route) {
    const dump = await describeFailure(page);
    console.log(`ARM ${locale}: REACHED NO TRIPS SCREEN.`);
    console.log("   url:", dump.url);
    console.log("   data-testid on page:", dump.testIds.join(" / ").slice(0, 400));
    console.log("   visible buttons:", dump.buttons.join(" | ").slice(0, 500));
    console.log("   body:", dump.body);
    await page.screenshot({ path: join(SHOTS, `no-trips-${locale}.png`), fullPage: true });
    await context.close();
    return { screens: [], failed: true };
  }
  console.log(`ARM ${locale}: trips screen via ${route}`);

  const regions = dictionaryRegions();
  const screens = [];
  // Every tab is measured from a pristine load. Opening a disclosure can raise a sheet or a
  // backdrop that swallows the next click, and a reading polluted by the previous tab's state is
  // not a reading -- so the harness pays one reload per tab and gets four independent numbers.
  const openTrips = async () => {
    await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
    await page.waitForTimeout(5000);
    return reachTrips(page);
  };
  for (const tab of TABS) {
    if ((await openTrips()) === null) {
      console.log(`   ${tab}: the trips screen did not come back, so this tab has no reading.`);
      continue;
    }
    await page.locator(`#trips-tab-${tab}`).click({ timeout: 8000 });
    await page.waitForTimeout(2200);
    const measure = await page.evaluate(() => {
      const visible = (node) => {
        const style = window.getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const box = node.getBoundingClientRect();
        return box.width > 1 && box.height > 1;
      };
      const pick = (selector) => Array.from(document.querySelectorAll(selector)).filter(visible);
      const panel = document.querySelector('[role="tabpanel"]') || document.body;
      const body = document.body.innerText || "";
      return {
        panelChars: (panel.innerText || "").replace(/\s+/g, " ").trim().length,
        chars: body.replace(/\s+/g, " ").trim().length,
        explainBlocks: pick(".v8-lede, .v8-muted, .v8-hint, [role=alert], .v8-notice, .v8-message").length,
        buttons: pick("button").length,
        panelText: panel.innerText || "",
        text: body,
      };
    });
    const observe = (keys, branch, text, observations) => {
      for (const key of keys) {
        const value = valueOf(regions, locale, key);
        if (value === null) {
          observations.push({ key, branch, state: "KEY NOT IN DICTIONARY", value: "" });
          continue;
        }
        const p = probe(value);
        if (!p.judgable) {
          observations.push({ key, branch, state: "NOT JUDGED (no stable fragment)", value: p.text });
          continue;
        }
        const onScreen = fold(text).includes(fold(p.text));
        const flags = [p.parameterised ? `template ${p.side}` : "", p.weak ? "short label" : ""]
          .filter(Boolean)
          .join(", ");
        const off = branch === "sometimes" ? "branch not reached" : "NOT RENDERED";
        observations.push({ key, branch, state: onScreen ? "ON SCREEN" : off, value: p.text, flags });
      }
    };

    const collapsed = measure.text.replace(/\s+/g, " ");
    const observations = [];
    const watch = WATCH[tab] || { always: [], disclosure: [], sometimes: [] };
    observe(watch.always, "always", collapsed, observations);
    observe(watch.sometimes, "sometimes", collapsed, observations);

    await page.screenshot({ path: join(SHOTS, `tab-${tab}-${locale}.png`), fullPage: true });
    // Now open every collapsed layer this screen offers and measure again. A sentence behind a
    // disclosure is not "on screen", and measuring without opening it would report a reachable
    // control as unreachable -- a false red this harness produced once before being fixed.
    const opened = await page.evaluate(() => {
      const visible = (node) => {
        const style = window.getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const box = node.getBoundingClientRect();
        return box.width > 1 && box.height > 1;
      };
      const targets = Array.from(document.querySelectorAll('[aria-expanded="false"]')).filter(visible);
      for (const node of targets.slice(0, 12)) node.click();
      return targets.length;
    });
    await page.waitForTimeout(1500);
    const expanded = await page.evaluate(() => {
      const visible = (node) => {
        const style = window.getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const box = node.getBoundingClientRect();
        return box.width > 1 && box.height > 1;
      };
      const pick = (selector) => Array.from(document.querySelectorAll(selector)).filter(visible);
      const body = document.body.innerText || "";
      return {
        chars: body.replace(/\s+/g, " ").trim().length,
        explainBlocks: pick(".v8-lede, .v8-muted, .v8-hint, [role=alert], .v8-notice, .v8-message").length,
        buttons: pick("button").length,
        text: body,
      };
    });
    observe(watch.disclosure, "disclosure", expanded.text.replace(/\s+/g, " "), observations);

    console.log(
      `   ${tab}: chars=${measure.chars} panelChars=${measure.panelChars} ` +
        `explainBlocks=${measure.explainBlocks} buttons=${measure.buttons} ` +
        `| disclosures opened=${opened} charsAfterOpening=${expanded.chars} ` +
        `explainBlocksAfter=${expanded.explainBlocks} buttonsAfter=${expanded.buttons}`
    );
    for (const item of observations) {
      console.log(
        `      ${item.branch} | ${item.state}${item.flags ? " [" + item.flags + "]" : ""}: ` +
          `${item.key} = ${item.value}`
      );
    }
    await page.screenshot({ path: join(SHOTS, `tab-${tab}-${locale}-open.png`), fullPage: true });
    screens.push({ tab, observations, chars: measure.chars, panelChars: measure.panelChars });
  }

  // The wallet face lives on its own shell route, so it is walked there rather than claimed here.
  const wallet = WANT_WALLET
    ? await walkWallet(page, regions, locale)
    : { reached: false, observations: [] };

  const problems = [];
  if (wallet.reached) {
    for (const item of wallet.observations) {
      if (item.state !== "ON SCREEN") problems.push(`wallet: ${item.key} reads "${item.state}"`);
    }
  }
  for (const screen of screens) {
    for (const item of screen.observations) {
      if (item.branch !== "sometimes" && item.state !== "ON SCREEN") {
        problems.push(`${screen.tab}: ${item.key} (${item.branch} branch) reads "${item.state}"`);
      }
    }
    for (const wanted of EXPECT.filter((item) => item.tab === screen.tab)) {
      const hit = screen.observations.find((o) => o.key === wanted.key);
      if (!hit) {
        problems.push(`${screen.tab}: ${wanted.key} is claimed but not in the watch list`);
        continue;
      }
      if (hit.state !== "ON SCREEN") {
        problems.push(`${screen.tab}: ${wanted.key} claimed on screen, observed "${hit.state}"`);
      }
    }
  }
  await context.close();
  return { screens, failed: false, problems };
}

async function main() {
  if (!JOURNEY) {
    console.log("REFUSE (rc 3): --journey is required, otherwise every tab is an empty shell.");
    process.exit(3);
  }
  mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const zh = await walk(browser, "zh");
  const en = await walk(browser, "en");
  await browser.close();

  console.log("----");
  const tabs = zh.screens.length + en.screens.length;
  console.log("tabs rendered:", tabs, "(zh", zh.screens.length, "/ en", en.screens.length + ")");
  console.log("claims that failed:", zh.problems?.length ?? 0, "/", en.problems?.length ?? 0);
  for (const problem of [...(zh.problems ?? []), ...(en.problems ?? [])]) {
    console.log("   CLAIM RED:", problem);
  }
  if (zh.failed || en.failed) {
    console.log("FAIL (rc 1): the trips screen was never reached, so no wording reading is made.");
    process.exit(1);
  }
  if (tabs < TABS.length * 2) {
    console.log(
      `FAIL (rc 1): fewer than ${TABS.length * 2} tab screens rendered, so the readings mean nothing.`
    );
    process.exit(1);
  }
  if ((zh.problems ?? []).length + (en.problems ?? []).length > 0) {
    console.log("FAIL (rc 1): a pinned on-screen claim is no longer true.");
    process.exit(1);
  }
  process.exit(0);
}

main().catch((error) => {
  console.log("HARNESS ERROR (rc 2):", String(error).slice(0, 300), NL);
  process.exit(2);
});
