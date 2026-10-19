/* Walk the traveller's screens in a real browser and measure how much text they hand the user.

   Four tabs (行程 / 住宿 / 预订 / 花费) are the spine, and the route screens a traveller reaches through
   the drawer are walked too -- 票夹, 城市探索, 住宿屏, 成员与权限, 回收站 -- because that is where this
   campaign's copy actually lives now: several of those screens read their sentences from a
   `features/<area>/<name>Copy.ts` module rather than from the shared dictionary, so a ruler that only
   walked the tabs was grading a fraction of the product.

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

   Usage: node _copycheck_dom_r1.mjs --url http://localhost:5337/ --journey <id> [--expect k:v,k:v]
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
const WANT_PREP = !process.argv.includes("--no-prep");
const WANT_STAY = !process.argv.includes("--no-stay");
const WANT_ACCESS = !process.argv.includes("--no-access");
const WANT_TRASH = !process.argv.includes("--no-trash");

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

/* A sentence the screen says twice is the waffle this campaign is built to find -- one fact with two
   writers, like the recycle bin's "回收站是空的…" followed by a 231-character paragraph explaining that
   the screen only lists what the server reported. That pair was found by reading a screenshot; this is
   the same reading, automated, so the next trim comes from a rendering rather than from a grep over
   source. Only clauses of eight characters or more count, and only what the screen actually painted.

   What it prints is a lead, not a verdict, and the first run proved why. Repeats fall in two kinds:
   a label the screen legitimately shows once per row ("Not chosen yet" x3 on the spend tab, because
   there are three bookings), and a *sentence* the screen really does say twice. The detector cannot
   tell them apart -- it only sees strings -- so each hit has to be traced to the element that painted
   it before anything is cut. Chinese needs no split at all here: the same screen reported nothing
   repeated, because the per-row labels in that language are shorter than the eight-character floor. */
function repeatedClauses(text) {
  const parts = String(text)
    .split(/[。；;]|\s--\s| — |\.\s|(?<=[a-z])\s(?=[A-Z])/)
    .map((part) => part.replace(/\s+/g, " ").trim())
    .filter((part) => part.length >= 8);
  const seen = new Map();
  for (const part of parts) seen.set(part, (seen.get(part) || 0) + 1);
  return [...seen.entries()].filter(([, count]) => count > 1).sort((a, b) => b[1] - a[1]);
}

function reportRepeats(name, text) {
  const repeated = repeatedClauses(text);
  if (!repeated.length) {
    console.log(`   ${name}: nothing is said twice on this screen`);
    return [];
  }
  console.log(`   ${name}: clauses said twice or more (${repeated.length}):`);
  for (const [clause, count] of repeated.slice(0, 6)) {
    console.log(`      x${count} ${clause.slice(0, 110)}`);
  }
  return repeated;
}

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

/* The feature copy modules, read the same way: `src/i18n/LocaleContext.tsx` is no longer the only
   place a traveller-facing sentence lives. `features/access/accessCopy.ts` and
   `features/estimation/estimationLadderCopy.ts` hold their own two-locale tables, and this wave of
   the campaign trimmed those rather than the dictionary, so the on-screen arm has to read them from
   the module files or it would be checking wording the product stopped saying. */
const COPY_MODULES = {
  access: join(FRONTEND, "src", "features", "access", "accessCopy.ts"),
  ladder: join(FRONTEND, "src", "features", "estimation", "estimationLadderCopy.ts"),
  trash: join(FRONTEND, "src", "features", "trash", "journeyTrashCopy.ts"),
};

function moduleTable(file) {
  const tables = { en: {}, "zh-CN": {} };
  let side = null;
  let pending = null;
  for (const line of readFileSync(file, "utf8").split(NL)) {
    if (pending !== null) {
      const value = /^\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')\s*,?\s*$/.exec(line);
      if (value && side) tables[side][pending] = next([value[1], value[2]]);
      pending = null;
      continue;
    }
    const opened = /^  (?:"([A-Za-z][\w-]*)"|([A-Za-z][\w-]*)):\s*\{\s*$/.exec(line);
    if (opened) {
      side = next([opened[1], opened[2]]);
      if (!(side in tables)) side = null;
      continue;
    }
    if (/^  \}/.test(line)) {
      side = null;
      continue;
    }
    if (!side) continue;
    const pair = /^    (?:"([A-Za-z0-9_.\-]+)"|'([A-Za-z0-9_.\-]+)'):\s*(.*)$/.exec(line);
    if (!pair) continue;
    const key = next([pair[1], pair[2]]);
    const rest = pair[3].trim();
    if (!rest) {
      pending = key;
      continue;
    }
    const value = /^"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'/.exec(rest);
    if (value) tables[side][key] = next([value[1], value[2]]);
  }
  return tables;
}

const next = (values) => values.find((value) => value !== undefined && value !== "") ?? "";

/** `{en, zh}` for one module key, with the locale names the two shapes use folded into one. */
function moduleValue(table, locale, key) {
  const side = locale === "zh" ? "zh-CN" : "en";
  return table[side][key] ?? null;
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
  "bookings.authorityExplicit",
  "bookings.authoritySub",
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

/* The destination-preparation screen, reached the same way a traveller reaches it, and asked the
   same question the copy campaign cares about: does the dictionary's current wording land in the
   verdict cell? The city typed here is the one the seeded store already holds, so the server can
   actually answer; the answer itself is what the panel renders, unchanged. */
const PREP_CITY = arg("--city", "北京");

async function walkPreparation(page, regions, locale) {
  const label = valueOf(regions, locale, "nav.discover");
  if (!label) {
    console.log("   preparation screen: NOT ATTEMPTED (nav.discover has no dictionary value)");
    return { reached: false, note: "nav.discover has no dictionary value" };
  }
  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(5000);
  const menu = page.locator('[data-testid="v8-mobile-menu"]');
  if ((await menu.count()) > 0) {
    await menu.first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(900);
  }
  const nav = page.locator("#v8-nav-drawer").getByRole("button", { name: label, exact: true });
  if ((await nav.count()) === 0) {
    console.log(`   preparation screen: NOT REACHED (no "${label}" entry in the drawer)`);
    return { reached: false, note: 'no "' + label + '" entry in the drawer' };
  }
  await nav.first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const panel = page.locator('[data-testid="prep-panel"]');
  if ((await panel.count()) === 0) {
    console.log(`   preparation screen: NOT REACHED (reached "${label}" but prep-panel is not on it)`);
    return { reached: false, note: 'prep-panel not on the "' + label + '" screen' };
  }

  await page.locator('[data-testid="prep-query"]').fill(PREP_CITY);
  await page.locator('[data-testid="prep-check"]').click({ timeout: 8000 });
  await page.waitForTimeout(6000);
  const verdict = await page.locator('[data-testid="prep-verdict-body"]').innerText().catch(() => "");
  const title = await page.locator('[data-testid="prep-verdict-title"]').innerText().catch(() => "");
  const folded = (verdict + " " + title).replace(/\s+/g, " ").trim();
  console.log(`   preparation screen: reached, verdict reads "${folded.slice(0, 90)}"`);
  const rendered = [];
  const notRendered = [];
  for (const key of PREP_KEYS) {
    const value = valueOf(regions, locale, key);
    const p = probe(value === null ? "" : value);
    if (!p.judgable) continue;
    (fold(folded).includes(fold(p.text)) ? rendered : notRendered).push(key);
  }
  console.log("      prep keys whose wording is on the verdict cell:", rendered.join(", ") || "(none of the watched set)");
  console.log("      prep keys not on this cell:", notRendered.join(", ") || "(none)");
  await page.screenshot({ path: join(SHOTS, `preparation-${locale}.png`), fullPage: true });
  return { reached: true, rendered, notRendered, verdict: folded };
}

/* The verdict cell shows one of these per server answer; which one is the server's choice, so the
   arm claims only that *some* dictionary wording landed, and names the one it saw. */
const PREP_KEYS = [
  "prep.current", "prep.missing", "prep.stale", "prep.ambiguous", "prep.unnamed",
  "prep.providerTransient", "prep.notAnswered", "prep.verdictBody",
];

/* The stay screen, reached the same way. Its copy still lives inside the component (that is the
   remaining 172-site backlog), so there is no dictionary value to compare against -- what this arm
   buys is a baseline: how many characters the screen hands a traveller, and the words themselves,
   so the next trim can be measured rather than described. */
async function walkStayScreen(page, regions, locale) {
  const label = valueOf(regions, locale, "nav.stay");
  if (!label) {
    console.log("   stay screen: NOT ATTEMPTED (nav.stay has no dictionary value)");
    return { reached: false };
  }
  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(5000);
  const menu = page.locator('[data-testid="v8-mobile-menu"]');
  if ((await menu.count()) > 0) {
    await menu.first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(900);
  }
  const nav = page.locator("#v8-nav-drawer").getByRole("button", { name: label, exact: true });
  if ((await nav.count()) === 0) {
    console.log(`   stay screen: NOT REACHED (no "${label}" entry in the drawer)`);
    return { reached: false };
  }
  await nav.first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(4000);
  const seen = await page.evaluate(() => {
    const main = document.querySelector("main") || document.body;
    return (main.innerText || "").replace(/\s+/g, " ").trim();
  });
  if (!seen) {
    console.log(`   stay screen: reached "${label}" but the main region rendered no text`);
    return { reached: false };
  }
  console.log(`   stay screen: reached, chars=${seen.length}`);
  console.log(`      ${seen.slice(0, 220)}`);

  /* The estimation ladder is mounted inside this screen (`features/stay/StayExplorer.tsx`), and its
     sentences come from `estimationLadderCopy.ts`, not the shared dictionary. Which rung sentence
     the panel picks is the module's decision, so this reports what it saw instead of claiming a
     branch: a trim of one of these lines shows up here as the trimmed wording landing. */
  const ladder = moduleTable(COPY_MODULES.ladder);
  const ladderOnScreen = [];
  const ladderOff = [];
  for (const key of LADDER_KEYS) {
    const value = moduleValue(ladder, locale, key);
    if (value === null) {
      console.log(`      ladder | KEY ABSENT FROM MODULE: ${key}`);
      ladderOff.push(key);
      continue;
    }
    const p = probe(value);
    (p.judgable && fold(seen).includes(fold(p.text)) ? ladderOnScreen : ladderOff).push(key);
    console.log(`      ladder | ${ladderOnScreen.includes(key) ? "ON SCREEN" : "not on this screen"}: ${key} = ${p.text}`);
  }

  await page.screenshot({ path: join(SHOTS, `stay-screen-${locale}.png`), fullPage: true });
  return { reached: true, chars: seen.length, ladderOnScreen, ladderOff };
}

/* The 成员与权限 screen (`features/access/accessCopy.ts`, mounted at the `access` route by
   `app/v8PanelRegistry.tsx`). This is the first time the walker goes there: the sentences this wave
   trimmed live in this module, and until one of them is read off a rendered screen the trim is only
   a diff. Nothing is claimed as `always` here until a run says which branch the seeded journey
   actually lands on. */
const ACCESS_KEYS = [
  "access.title",
  "access.sub",
  "access.pickLabel",
  "access.pickEmpty",
  "access.pickLoading",
  "access.scopeDoorSilent",
  "access.adminCapUnanswered",
  "access.doorAbsent",
  "access.doorPresent",
  "access.refuseOwnerCannotLeave",
];
const LADDER_KEYS = [
  "ladder.method.noCandidates",
  "ladder.pre.noAmount",
  "ladder.method.noSource",
  "ladder.method.noConfidence",
  "ladder.verify.open",
];
/* What the 06:4x run actually read off these two screens, in both languages, so it is now claimed:
   `ladder.method.noCandidates` on the stay screen's empty branch (the ladder is mounted inside
   `features/stay/StayExplorer.tsx`), and the three headings of the 成员与权限 screen. The claim is on
   the key, not on the wording -- the sentence is re-read from the module file at run time -- so a
   trim that keeps the reader moves the reading instead of breaking it, and a trim that detaches the
   reader goes red. */
const LADDER_CLAIMED = ["ladder.method.noCandidates"];
const ACCESS_CLAIMED = ["access.title", "access.sub", "access.pickLabel"];
/* The 回收站 screen's own sentences. Nothing is claimed here yet: this is the first run that goes in,
   and which of these the seeded store shows (an empty bin, a bin with one trip in it, or a bin the
   server will not answer for) is the server's answer, not this file's guess. */
const TRASH_KEYS = [
  "trash.title",
  "trash.sub",
  "trash.empty",
  "trash.empty.why",
  "trash.count",
  "trash.rowState",
  "trash.transport",
  "trash.recoveryMissing",
  "trash.noViewer",
  "trash.recoveryRefusedNoSeat",
  "trash.action",
];
const TRASH_CLAIMED = [];

/* One module-backed route screen, reached the way a traveller reaches it: through the drawer, by the
   label the dictionary gives that nav entry. Written once because the 成员与权限 screen and the 回收站
   screen are the same measurement -- chars, and which of the module's sentences actually landed.

   The nav label is read from the dictionary at run time, never typed here: this branch's claim is that
   the screens speak the dictionary, so a hardcoded label would pass while the product renamed the
   button. Failure always says which door it could not get through. */
async function walkModuleFace(page, regions, locale, opts) {
  const { name, navKey, testId, moduleFile, keys } = opts;
  const label = valueOf(regions, locale, navKey);
  if (!label) {
    console.log(`   ${name}: NOT ATTEMPTED (${navKey} has no dictionary value)`);
    return { reached: false, note: `${navKey} has no dictionary value` };
  }
  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(5000);
  const menu = page.locator('[data-testid="v8-mobile-menu"]');
  if ((await menu.count()) > 0) {
    await menu.first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(900);
  }
  const nav = page.locator("#v8-nav-drawer").getByRole("button", { name: label, exact: true });
  if ((await nav.count()) === 0) {
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll("button"))
        .map((node) => node.innerText.replace(/\s+/g, " ").trim())
        .filter(Boolean)
        .slice(0, 30)
    );
    console.log(
      `   ${name}: NOT REACHED (no "${label}" entry in the drawer); buttons: ${visible.join(" | ").slice(0, 260)}`
    );
    return { reached: false, note: 'no "' + label + '" entry in the drawer' };
  }
  await nav.first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const mounted = (await page.locator(`[data-testid="${testId}"]`).count()) > 0;
  const panel = await page.evaluate((id) => {
    const host =
      document.querySelector('[data-testid="' + id + '"]') ||
      document.querySelector("main") ||
      document.body;
    return (host.innerText || "").replace(/\s+/g, " ").trim();
  }, testId);
  if (!mounted || !panel) {
    console.log(
      `   ${name}: clicked "${label}" but ${testId} mounted=${mounted}, text ${panel.length} chars`
    );
    return { reached: false, note: `${testId} mounted=${mounted}` };
  }
  console.log(`   ${name}: reached, chars=${panel.length}`);
  reportRepeats(name, panel);
  console.log(`      ${panel.slice(0, 220)}`);
  const table = moduleTable(moduleFile);
  const entries = [];
  for (const key of keys) {
    const value = moduleValue(table, locale, key);
    if (value === null) {
      console.log(`      ${name} | KEY ABSENT FROM MODULE: ${key}`);
      entries.push({ key, text: "", hit: false, absent: true, weak: false });
      continue;
    }
    const p = probe(value);
    entries.push({
      key,
      text: p.text,
      hit: p.judgable && fold(panel).includes(fold(p.text)),
      absent: false,
      parameterised: p.parameterised,
      side: p.side,
      weak: p.weak,
    });
  }
  /* A five-character reading like 「在回收站里」 is also inside the screen's sub-heading, so on an EMPTY
     bin it matches without its own row ever rendering. A short label can be flagged as weak, but a
     five-character phrase is above that threshold, so the honest fix is to name the carrier: the
     reading stays, and it says which other sentence it could have come from. */
  for (const entry of entries) {
    const carrier = entries.find(
      (other) =>
        other !== entry &&
        other.hit &&
        entry.hit &&
        other.text.length > entry.text.length &&
        fold(other.text).includes(fold(entry.text))
    );
    entry.carrier = carrier ? carrier.key : "";
    const flags = [];
    if (entry.parameterised) flags.push(entry.side);
    if (entry.weak) flags.push("short label");
    if (entry.carrier) flags.push("carried by " + entry.carrier);
    console.log(
      `      ${name} | ${entry.hit ? "ON SCREEN" : "not on this branch"}` +
        (flags.length ? ` [${flags.join(", ")}]` : "") +
        `: ${entry.key} = ${entry.text.slice(0, 96)}`
    );
  }
  const onScreen = entries.filter((entry) => entry.hit).map((entry) => entry.key);
  const off = entries.filter((entry) => !entry.hit).map((entry) => entry.key);
  const weak = entries.filter((entry) => entry.hit && (entry.weak || entry.carrier)).map((entry) => entry.key);
  await page.screenshot({ path: join(SHOTS, `${name.split(" ")[0]}-${locale}.png`), fullPage: true });
  return { reached: true, chars: panel.length, onScreen, off, weak };
}

function walkAccessFace(page, regions, locale) {
  return walkModuleFace(page, regions, locale, {
    name: "access screen",
    navKey: "nav.access",
    testId: "access-panel",
    moduleFile: COPY_MODULES.access,
    keys: ACCESS_KEYS,
  });
}

function walkTrashFace(page, regions, locale) {
  return walkModuleFace(page, regions, locale, {
    name: "trash screen",
    navKey: "nav.trash",
    testId: "journey-trash-panel",
    moduleFile: COPY_MODULES.trash,
    keys: TRASH_KEYS,
  });
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
    reportRepeats(`${tab} tab`, measure.text);
    await page.screenshot({ path: join(SHOTS, `tab-${tab}-${locale}-open.png`), fullPage: true });
    screens.push({ tab, observations, chars: measure.chars, panelChars: measure.panelChars });
  }

  // The wallet face lives on its own shell route, so it is walked there rather than claimed here.
  const wallet = WANT_WALLET
    ? await walkWallet(page, regions, locale)
    : { reached: false, observations: [] };
  const prep = WANT_PREP ? await walkPreparation(page, regions, locale) : { reached: false };
  const stayScreen = WANT_STAY ? await walkStayScreen(page, regions, locale) : { reached: false };
  const access = WANT_ACCESS ? await walkAccessFace(page, regions, locale) : { reached: false };
  const trash = WANT_TRASH ? await walkTrashFace(page, regions, locale) : { reached: false };

  const problems = [];
  if (prep.reached && prep.verdict && (prep.rendered ?? []).length === 0) {
    problems.push("preparation: the verdict cell renders wording that is in no dictionary key");
  }
  if (wallet.reached) {
    for (const item of wallet.observations) {
      if (item.state !== "ON SCREEN") problems.push(`wallet: ${item.key} reads "${item.state}"`);
    }
  }
  if (stayScreen.reached) {
    for (const key of LADDER_CLAIMED) {
      if (!(stayScreen.ladderOnScreen ?? []).includes(key)) {
        problems.push(
          `stay screen: ${key} is claimed on screen, the ladder read puts it in: ` +
            ((stayScreen.ladderOff ?? []).includes(key) ? "not on this screen" : "not measured")
        );
      }
    }
  }
  for (const arm of [
    { screen: "access screen", result: access, claimed: ACCESS_CLAIMED },
    { screen: "trash screen", result: trash, claimed: TRASH_CLAIMED },
  ]) {
    if (!arm.result.reached) continue;
    for (const key of arm.claimed) {
      if ((arm.result.weak ?? []).includes(key)) {
        problems.push(`${arm.screen}: ${key} is claimed on a short label -- claim a full sentence`);
      }
      if (!(arm.result.onScreen ?? []).includes(key)) {
        problems.push(
          `${arm.screen}: ${key} is claimed on screen, the module read puts it in: ` +
            ((arm.result.off ?? []).includes(key) ? "not on this branch" : "not measured")
        );
      }
    }
  }
  console.log(
    "   module route arms: wallet=" + (wallet.reached ? "reached" : "not reached") +
      ", access=" + (access.reached ? "reached" : "not reached") +
      ", trash=" + (trash.reached ? "reached" : "not reached") +
      ", preparation=" + (prep.reached ? "reached" : "not reached") +
      ", stay screen=" + (stayScreen.reached ? "reached" : "not reached")
  );
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
