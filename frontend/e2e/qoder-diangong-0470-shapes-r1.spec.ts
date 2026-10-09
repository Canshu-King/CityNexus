/* ORD-0470 · lane 电工-0470 · the paste door, walked in every shape.
 *
 * The door itself already shipped on the authoritative tip (commit 78ab7f7bb, arms in
 * e2e/qoder-poi-entry-r1-walkthrough.spec.ts) but every one of those arms measured a single
 * shape: 390x844. This file does not re-prove that arm; it asks the harder question the order
 * states as criterion two -- is the door reachable in *every* shape, hit-tested rather than
 * merely present in the DOM, with the collapsible opened before anything is measured and with
 * the scroll reset before each control so one measurement cannot contaminate the next.
 *
 * Landing is read from the painted screen (the h1 text), never from a data attribute, and the
 * expected words are read out of the shipped copy tables at run time so an arm cannot rot into
 * a second copy of the prose it checks.
 */
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.join(process.cwd(), "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf-8");
const DICTIONARY = "frontend/src/i18n/LocaleContext.tsx";
const PENDING_TABLE = "frontend/src/features/pending/pendingSetCopy.ts";
const IMPORT_TABLE = "frontend/src/features/poiimport/poiImportCopy.ts";
const OUT_DIR = path.join(ROOT, "review", "diangong-0470-r1");

const norm = (s: string) => s.replace(/\s+/g, " ").trim();

/** first quoted run after `from`; handles a value wrapped onto its own line */
function quotedAfter(text: string, from: number, where: string): string {
  const open = text.indexOf('"', from);
  if (open === -1) throw new Error(`${where}: no opening quote after ${from}`);
  let i = open + 1;
  let out = "";
  while (i < text.length) {
    if (text[i] === "\\") {
      const esc = text[i + 1];
      out +=
        esc === "n"
          ? "\n"
          : esc === "u"
            ? String.fromCharCode(parseInt(text.slice(i + 2, i + 6), 16))
            : esc;
      i += esc === "u" ? 6 : 2;
      continue;
    }
    if (text[i] === '"') return out;
    out += text[i];
    i += 1;
  }
  throw new Error(`${where}: string never closed`);
}

/** the nav's own word for the import screen, from the shipped dictionary book */
function navWord(book: "en" | "zh-CN"): string {
  const text = read(DICTIONARY);
  const split = text.indexOf("\nconst zhCN");
  if (split === -1) throw new Error(`${DICTIONARY} no longer splits where this arm reads it`);
  const body = book === "en" ? text.slice(0, split) : text.slice(split);
  const at = body.indexOf('"nav.import":');
  if (at === -1) throw new Error(`nav.import is not in the ${book} book`);
  return norm(quotedAfter(body, at + '"nav.import"'.length + 1, `nav.import`));
}

/** one half of the 待规划 copy table */
function pendingHalf(key: string, book: "en" | "zh-CN"): string {
  const text = read(PENDING_TABLE);
  const enAt = text.indexOf('  en: {');
  const zhAt = text.indexOf('  "zh-CN": {');
  if (enAt === -1 || zhAt === -1) throw new Error(`${PENDING_TABLE} no longer opens the way this arm reads it`);
  const at = text.indexOf(`"${key}":`, book === "en" ? enAt : zhAt);
  if (at === -1) throw new Error(`${key} is not in the ${book} book of ${PENDING_TABLE}`);
  const bound = book === "en" ? zhAt : Infinity;
  if (at > bound) throw new Error(`${key} is not in the ${book} book of ${PENDING_TABLE}`);
  return norm(quotedAfter(text, at + key.length + 3, `${book}:${key}`));
}

/** one half of the import screen's own copy table (`key: { zh: "…", en: "…" }`) */
function importHalf(key: string, half: "zh" | "en"): string {
  const text = read(IMPORT_TABLE);
  const at = text.indexOf(`  ${key}: {`);
  if (at === -1) throw new Error(`${key} is not a cell of ${IMPORT_TABLE}`);
  const from = text.indexOf(`${half}:`, at);
  if (from === -1 || text.indexOf("\n  }", at) < from) throw new Error(`${key} has no ${half} half`);
  return norm(quotedAfter(text, from + half.length + 1, `${key}.${half}`));
}

const LOCALES = [
  { locale: "zh-CN", book: "zh-CN" as const, half: "zh" as const },
  { locale: "en-GB", book: "en" as const, half: "en" as const },
];

/* The shell switches layout at `@media (max-width: 680px)` (styles.css:185): below it the sidebar
   is `display:none` and the nav lives behind a hamburger fold; above it the fold does not exist at
   all. Measuring only one side of that line is how a door looks reachable when it is not.

   The tap floor is layered the way Amendment F-2 states it: `>=44 CSS px` on the touch/mobile layer,
   and on the desktop layer `30px = compact fine-pointer visual density; mobile/touch hit target is
   superseded by the >=44px accessibility contract.` One 44 applied to every shape is not a stricter
   arm, it is a wrong one -- it reports the product's own desktop density as a defect. */
const SHAPES = [
  { key: "phone-390x844", width: 390, height: 844, fold: true, minPx: 44 },
  { key: "phone-360x640", width: 360, height: 640, fold: true, minPx: 44 },
  { key: "landscape-844x390", width: 844, height: 390, fold: false, minPx: 30 },
  { key: "tablet-768x1024", width: 768, height: 1024, fold: false, minPx: 30 },
  { key: "desktop-1280x800", width: 1280, height: 800, fold: false, minPx: 30 },
];

/* Appended per arm rather than flushed at the end: the module scope does not survive across arms, so
   the first version of this instrument collected thirty rows in an array and wrote exactly one. */
const OUT_FILE = path.join(OUT_DIR, "SHAPE_SWEEP.jsonl");
function record(row: Record<string, unknown>) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.appendFileSync(OUT_FILE, JSON.stringify(row) + "\n", "utf-8");
}

async function openInLocale(
  page: import("@playwright/test").Page,
  locale: string,
  route: string,
) {
  await page.addInitScript((l) => localStorage.setItem("citynexus.locale", l), locale);
  await page.goto(route);
  expect(await page.evaluate(() => localStorage.getItem("citynexus.locale"))).toBe(locale);
}

/**
 * Reset, aim, hit-test.  Every measurement starts from the top of *both* scrollers: the page and
 * the drawer, which is its own `overflow-y:auto` box (styles.css, `#v8-nav-drawer`).  A scroll left
 * over from the previous control moves the next one, so an arm that does not reset is measuring the
 * previous arm's position.  The box must carry both a width and a height -- `boundingBox()` without
 * them yields NaN, and a NaN comparison passes silently, which is a fake defect waiting to be
 * reported as a real one.
 */
async function hitTest(
  page: import("@playwright/test").Page,
  locator: import("@playwright/test").Locator,
  name: string,
  minPx: number,
) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    const drawer = document.querySelector("#v8-nav-drawer");
    if (drawer) drawer.scrollTop = 0;
  });
  await locator.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const box = await locator.boundingBox();
  expect(box, `${name} has no box to aim at`).not.toBeNull();
  expect(Number.isFinite(box!.x) && Number.isFinite(box!.y), `${name} box is not a position`).toBe(true);
  expect(Math.round(box!.width), `${name} has no width`).toBeGreaterThan(0);
  expect(Math.round(box!.height), `${name} is below the ${minPx}px floor of its layer`).toBeGreaterThanOrEqual(minPx);
  const handle = await locator.elementHandle();
  const found = await page.evaluate(({ own, x, y }) => {
    const hit = document.elementFromPoint(x, y);
    return {
      tag: `${hit?.tagName}.${hit?.className}`.slice(0, 90),
      is_own: !!own && (own === hit || own.contains(hit)),
    };
  }, { own: handle, x: Math.round(box!.x + box!.width / 2), y: Math.round(box!.y + box!.height / 2) });
  expect(found.is_own, `something covers ${name}: ${found.tag}`).toBe(true);
  return { width: Math.round(box!.width), height: Math.round(box!.height), min_px: minPx };
}

/** the import screen as the traveller sees it: the painted heading, read as text */
async function paintedImportTitle(page: import("@playwright/test").Page): Promise<string> {
  const h1 = page.locator('[data-testid="poi-import"] h1');
  await expect(h1, "the import screen did not paint a heading").toHaveCount(1);
  return norm(await h1.innerText());
}

for (const { locale, book, half } of LOCALES) {
  for (const shape of SHAPES) {
    test(`抽屉/侧栏那一格在 ${shape.key} 点得到并落到导入屏 [${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: shape.width, height: shape.height });
      await openInLocale(page, locale, "/v8/hub");
      let row: import("@playwright/test").Locator;
      let rowName: string;
      if (shape.fold) {
        // the fold is closed on arrival: measuring the row before opening it is a fake "unreachable"
        const menu = page.getByTestId("v8-mobile-menu");
        await expect(menu, "the hamburger is gone from the mobile shape").toBeVisible();
        await menu.click();
        await expect(page.getByTestId("v8-nav-drawer"), "the fold did not open").toBeVisible();
        row = page.getByTestId("v8-drawer-entry-import");
        rowName = "v8-drawer-entry-import";
      } else {
        // above the breakpoint there is no fold to open; the nav is the sidebar itself
        await expect(page.locator(".v8-sidebar"), "the sidebar is not the layout at this width").toBeVisible();
        row = page.locator(".v8-sidebar .v8-nav button").filter({ hasText: navWord(book) });
        rowName = "sidebar import row";
      }
      await expect(row, `the nav row for the import screen is missing at ${shape.key}`).toHaveCount(1);
      expect(norm(await row.innerText()), "the row says something other than the dictionary").toBe(navWord(book));
      const box = await hitTest(page, row, rowName, shape.minPx);
      await row.click();
      await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 30_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/import");
      const title = await paintedImportTitle(page);
      expect(title).toBe(importHalf("title", half));
      record({
        locale, shape: shape.key, door: shape.fold ? "drawer-row" : "sidebar-row",
        label_matches_dictionary: true, hit_own: true, ...box, landed: true, painted_title: title,
      });
    });

    test(`待规划那一格在 ${shape.key} 点得到并落到导入屏 [${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: shape.width, height: shape.height });
      await openInLocale(page, locale, "/v8/hub");
      const cell = page.getByTestId("pending-empty");
      await expect(cell, "the 待规划 cell did not come up empty on this seed").toBeVisible({ timeout: 45_000 });
      const door = page.getByTestId("pending-empty-import");
      await expect(door, "the hub carries no import door in this shape").toHaveCount(1);
      expect(norm(await door.innerText()), "the hub door says something other than the dictionary").toBe(
        pendingHalf("pending.empty.import", book),
      );
      const box = await hitTest(page, door, "pending-empty-import", shape.minPx);
      await door.click();
      await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 30_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/import");
      const title = await paintedImportTitle(page);
      expect(title).toBe(importHalf("title", half));
      record({ locale, shape: shape.key, door: "hub-pending-empty", hit_own: true, ...box, landed: true });
    });

    test(`地址直接落到导入屏在 ${shape.key} 也算数 [${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: shape.width, height: shape.height });
      await openInLocale(page, locale, "/v8/import");
      await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 45_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/import");
      expect(await paintedImportTitle(page)).toBe(importHalf("title", half));
      const box = await hitTest(page, page.getByTestId("poi-import-parse"), "poi-import-parse", shape.minPx);
      record({ locale, shape: shape.key, door: "deep-link", landed: true, ...box });
    });
  }
}
