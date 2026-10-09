/* ORD-0470 · lane POI 导入入口 · the import screen gets a door a traveller can read, and its
 * no-data cell gets moves instead of a sentence.
 *
 * What cmdr's order asked for (账本 `### cmdr 19:42` 那块第三节) was one route that really walks to
 * `/v8/import`, proven the house way: 视口内命中、点得到、点完屏上有反应 -- and "路由存在" explicitly
 * does not count as arriving.
 *
 * Measured before this file existed, on the same tip and the same chain (`npm run dev` + its own
 * backend, port from `CITYNEXUS_BACKEND_PORT`): the drawer row and the desktop sidebar already walked
 * there, so arm C below pins that rather than re-fixing it; what no user could reach was the cell
 * that *tells* them there is nothing to plan -- 待规划 on 今天 offered 去城市探索 and 再读一次 only.
 * And the import screen's own nothing-extracted cell was one sentence with no move under it.
 *
 * Every expected sentence in this file is read out of the shipped copy table at run time, never
 * typed in here, so the arm cannot rot into a second copy of the prose it is checking.
 */
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.join(process.cwd(), "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf-8");

const PANEL = "frontend/src/features/poiimport/PoiImportPanel.tsx";
const IMPORT_TABLE = "frontend/src/features/poiimport/poiImportCopy.ts";
const PENDING_TABLE = "frontend/src/features/pending/pendingSetCopy.ts";
const DICTIONARY = "frontend/src/i18n/LocaleContext.tsx";

const norm = (s: string) => s.replace(/\s+/g, " ").trim();
/** the first quoted run after `from` -- handles a value wrapped onto its own line */
function quotedAfter(text: string, from: number, where: string): string {
  const open = text.indexOf('"', from);
  if (open === -1) throw new Error(`${where}: no opening quote after ${from}`);
  let i = open + 1;
  let out = "";
  while (i < text.length) {
    if (text[i] === "\\") {
      const esc = text[i + 1];
      out += esc === "n" ? "\n" : esc === "u" ? String.fromCharCode(parseInt(text.slice(i + 2, i + 6), 16)) : esc;
      i += esc === "u" ? 6 : 2;
      continue;
    }
    if (text[i] === '"') return out;
    out += text[i];
    i += 1;
  }
  throw new Error(`${where}: string never closed`);
}

/** one half of a cell in the import screen's own table (`key: { zh: "…", en: "…" }`) */
function importHalf(key: string, half: "zh" | "en"): string {
  const text = read(IMPORT_TABLE);
  const at = text.indexOf(`  ${key}: {`);
  if (at === -1) throw new Error(`${key} is not a cell of ${IMPORT_TABLE}`);
  const from = text.indexOf(`${half}:`, at);
  if (from === -1 || text.indexOf("\n  }", at) < from) throw new Error(`${key} has no ${half} half`);
  return norm(quotedAfter(text, from + half.length + 1, `${key}.${half}`));
}

/** one half of a cell in the 待规划 table, whose two books are split at `zh: {` */
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

/** what the nav itself calls that screen -- the door must use the same word, not invent a third */
function navWord(key: string, book: "en" | "zh-CN"): string {
  const text = read(DICTIONARY);
  const split = text.indexOf("\nconst zhCN");
  if (split === -1) throw new Error(`${DICTIONARY} no longer splits where this arm reads it`);
  const body = book === "en" ? text.slice(0, split) : text.slice(split);
  const at = body.indexOf(`"nav.${key}":`);
  if (at === -1) throw new Error(`nav.${key} is not in the ${book} book`);
  return norm(quotedAfter(body, at + `nav.${key}`.length + 4, `nav.${key}`));
}

/* The seed project boots the traveller it created, and that traveller is `en-GB`; the shell decides
   the language from localStorage, so an arm that wants a locale has to say it the way the product
   does. Measured the hard way: without this the zh arms read the en glass and fail on copy, which is
   an instrument fault, not a product one -- the same two lines ORD-0545's walkthrough uses. */
async function openInLocale(page: import("@playwright/test").Page, locale: string, route: string) {
  await page.addInitScript((l) => localStorage.setItem("citynexus.locale", l), locale);
  await page.goto(route);
  expect(await page.evaluate(() => localStorage.getItem("citynexus.locale"))).toBe(locale);
}

const LOCALES = [
  { locale: "zh-CN", book: "zh-CN" as const, half: "zh" as const },
  { locale: "en-GB", book: "en" as const, half: "en" as const },
];

/** centre of a control, and what the browser would actually receive at that point */
async function centreHit(page: import("@playwright/test").Page, testId: string) {
  const box = await page.getByTestId(testId).boundingBox();
  expect(box, `${testId} has no box to aim at`).not.toBeNull();
  const found = await page.evaluate(({ tid, x, y }) => {
    const own = document.querySelector(`[data-testid="${tid}"]`);
    const hit = document.elementFromPoint(x, y);
    return {
      tag: `${hit?.tagName}.${hit?.className}`.slice(0, 80),
      is_own: !!own && (own === hit || own.contains(hit)),
      in_viewport: hit !== null,
    };
  }, { tid: testId, x: (box!.x + box!.width / 2) | 0, y: (box!.y + box!.height / 2) | 0 });
  return { box: box!, testId, ...found };
}

test.describe("ORD-0470 the paste door, walked as a user", () => {
  for (const { locale, book, half } of LOCALES) {
    test(`hub 待规划空态的第二枚门 -> 导入屏 [${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await openInLocale(page, locale, "/v8/hub");
      const cell = page.getByTestId("pending-empty");
      await expect(cell, "the 待规划 cell did not come up empty on this journey").toBeVisible({ timeout: 45_000 });

      // the sentence beside the doors has to name both of them, or the row contradicts the copy
      const sentence = norm(await cell.innerText());
      expect(sentence).toContain(pendingHalf("pending.empty", book));
      expect(sentence, `the lead sentence does not point at the second door: ${sentence}`).toContain(
        norm(pendingHalf("pending.empty.next", book)),
      );

      const door = page.getByTestId("pending-empty-import");
      await expect(door, "the import door is not mounted in the empty cell").toHaveCount(1);
      const label = norm(await door.innerText());
      expect(label, `the door must say what the nav says: ${label}`).toBe(navWord("import", book));
      await door.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      const hit = await centreHit(page, "pending-empty-import");
      expect(Math.round(hit.box.height), "the door is below the 44px tap floor").toBeGreaterThanOrEqual(44);
      expect(hit.is_own, `something covers the door: ${hit.tag}`).toBe(true);

      await door.click();
      await expect(page.getByTestId("poi-import"), "the press did not paint the import screen").toBeVisible({ timeout: 30_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/import");
      // and the screen it landed on is the import screen, not the drawer's copy of some other panel
      await expect(page.getByTestId("poi-import-parse"), "landed on a shell without the parse door").toHaveCount(1);
    });

    test(`导入屏没有条目时给得出下一步 [${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await openInLocale(page, locale, "/v8/import");
      await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 45_000 });

      await page.getByTestId("poi-import-text").fill("..");
      const answered = page.waitForResponse((r) => r.url().includes("/poi-import/parse"), { timeout: 30_000 });
      await page.getByTestId("poi-import-parse").click();
      const body = await (await answered).json();
      expect(body.counts?.extracted, "this arm needs a paste that extracts nothing").toBe(0);
      const empty = page.getByTestId("poi-import-empty");
      await expect(empty).toBeVisible({ timeout: 30_000 });

      /* the sentence is still only a sentence: the controls are its siblings, so the cell-by-cell
         walkthrough gate (ORD-0545 slice 4) keeps reading the same text it read before this order. */
      expect(norm(await empty.innerText())).toBe(importHalf("emptyExtracted", half));

      const row = page.getByTestId("poi-import-empty-actions");
      await expect(row, "the no-data cell still has no move under it").toBeVisible();
      await row.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      const clear = await centreHit(page, "poi-import-empty-clear");
      expect(Math.round(clear.box.height), "清空重写 is below the 44px tap floor").toBeGreaterThanOrEqual(44);
      expect(clear.is_own, `something covers 清空重写: ${clear.tag}`).toBe(true);
      expect(norm(await page.getByTestId("poi-import-empty-clear").innerText())).toBe(importHalf("emptyClearAction", half));
      expect(norm(await page.getByTestId("poi-import-empty-discover").innerText())).toBe(importHalf("emptyDiscoverAction", half));
      /* The second door is a verb phrase (去城市探索 / Open City Discovery) while the nav's cell for
         that screen is the bare place name (城市探索 / City Discovery), so the honest claim here is
         "it says the nav's own word for the screen it goes to" -- containment, not equality. The
         hub's door above is checked at equality, because that one *is* the place name. */
      const discoverLabel = norm(await page.getByTestId("poi-import-empty-discover").innerText());
      expect(discoverLabel, `the second door does not name its destination: ${discoverLabel}`).toContain(
        navWord("discover", book),
      );

      // move 1: rewriting is a real move on this screen, not a repaint of the same refusal
      await page.getByTestId("poi-import-empty-clear").click();
      await expect(page.getByTestId("poi-import-text")).toHaveValue("");
      await expect(page.getByTestId("poi-import-empty")).toHaveCount(0);
      await expect(page.getByTestId("poi-import-empty-actions"), "the move row outlived the cell it belongs to").toHaveCount(0);
      await expect(page.getByTestId("poi-import-parse")).toBeDisabled();
      expect(norm(await page.getByTestId("poi-import-char-count").innerText())).toContain("0");
      expect(await page.evaluate(() => document.activeElement?.id)).toBe("poi-import-text");

      // move 2: the other door changes the screen
      await page.getByTestId("poi-import-text").fill("..");
      const again = page.waitForResponse((r) => r.url().includes("/poi-import/parse"), { timeout: 30_000 });
      await page.getByTestId("poi-import-parse").click();
      await (await again).json();
      await expect(page.getByTestId("poi-import-empty-discover")).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("poi-import-empty-discover").click();
      await expect(page.getByTestId("prep-panel"), "the second door did not land on City Discovery").toBeVisible({ timeout: 30_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/discover");
    });

    test(`抽屉那一格仍然走得通（回归钉）[${locale}]`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await openInLocale(page, locale, "/v8/hub");
      await page.getByTestId("v8-mobile-menu").click();
      const row = page.getByTestId("v8-drawer-entry-import");
      await expect(row, "the drawer lost the row this order was told not to duplicate").toHaveCount(1);
      expect(norm(await row.innerText())).toBe(navWord("import", book));
      await row.click();
      await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 30_000 });
      expect(new URL(page.url()).pathname).toBe("/v8/import");
    });
  }
});

/* the shipped source must still be the thing that paints these cells -- a marker that moved out of
   the window the gate reads is a failure, not a guess */
test("ORD-0470 形状锁：两枚门都是兄弟节点，不藏进句子", async () => {
  const panel = read(PANEL);
  const at = panel.indexOf('data-testid="poi-import-empty"');
  expect(at, "the no-data cell is gone from the shipped panel").toBeGreaterThan(0);
  const window = panel.slice(at, at + 1_600);
  expect(window).toContain('poiImportCopy(locale, "emptyExtracted")');
  expect(window).toContain('data-testid="poi-import-empty-actions"');
  expect(window).toContain('poiImportCopy(locale, "emptyClearAction")');
  expect(window).toContain('poiImportCopy(locale, "emptyDiscoverAction")');
  // the actions row opens after the sentence closes -- it is not nested inside it
  const sentenceEnd = window.indexOf("</p>");
  const actionsStart = window.indexOf('data-testid="poi-import-empty-actions"');
  expect(sentenceEnd, "the sentence never closes where this arm reads it").toBeGreaterThan(0);
  expect(actionsStart, "the move row is not after the sentence").toBeGreaterThan(sentenceEnd);
});
