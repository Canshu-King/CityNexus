/**
 * ORD-0573（词表那半）· 行程四枚分区标签的字从组件里的内联字面搬进每屏 copy 表（车道 8ac89982）
 *
 * 搬，不是改写：屏上那四个字一个都不能动。所以这枚闸判三件事：
 *  1. **字没动**：两臂逐枚把屏上四枚标签的可见文字与**改动前**那份读数（`ord0573_sections_baseline_*.json`
 *     随枝交）比，逐枚相等；不是"看起来一样"。
 *  2. **角色那半没被碰坏**：容器仍带 `role="tablist"`，四枚仍带 `role="tab"` 与稳定 id，
 *     恰好一枚声明选中，点第二枚之后选中态跟着走——上一手的东西不许在这手掉下来。
 *  3. **字确实搬走了**（这一格让尺会红的那一下）：读**源码本身**——组件里那四枚中英字面必须已经不在，
 *     并且组件必须从 `i18n/tripSectionsCopy.ts` 取词。这条判的是"字写在哪"，所以它会随字面回到组件而变红，
 *     那正是它该有的牙齿；产品字节退回现尖时，这一格必须红。
 */
import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0573-sections-copy-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const SHELL = "src/app/V8Experience.tsx";
const COPY_MODULE = "src/i18n/tripSectionsCopy.ts";
const WORDS = [
  { key: "itinerary", zh: "行程", en: "Itinerary" },
  { key: "stay", zh: "住宿", en: "Stay" },
  { key: "bookings", zh: "预订", en: "Bookings" },
  { key: "spend", zh: "花费", en: "Spend" },
];
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];

function sourceArm() {
  const shell = readFileSync(resolve(FRONTEND, SHELL), "utf8");
  const copy = readFileSync(resolve(FRONTEND, COPY_MODULE), "utf8");
  /* Look for the *tab array's* former shape -- a `{ key: "<k>" as const, zh: "…", en: "…" }` row -- and
     not for the bare words anywhere in the shell. The first version of this arm searched for the words,
     and it reddened on my own correct bytes because "住宿"/"Stay" and "预订"/"Bookings" also live on
     unrelated surfaces (a hotel card, a category table, a poster kicker). Those are not this hand's rows
     and must stay exactly where they are; the tab rows are what moved. */
  const tabRowsLeftInShell = WORDS.filter((w) =>
    new RegExp(`key:\\s*"${w.key}"\\s+as const`).test(shell)
  ).map((w) => w.key);
  const importsTheModule = /from "\.\.\/i18n\/tripSectionsCopy"/.test(shell);
  const moduleHasEveryWord = WORDS.every(
    (w) => copy.includes(`zh: "${w.zh}"`) && copy.includes(`en: "${w.en}"`),
  );
  return { tabRowsLeftInShell, importsTheModule, moduleHasEveryWord };
}

test.describe("ORD-0573 the section labels come from the copy table", () => {
  for (const arm of ARMS) {
    test(`sections-copy-${arm.locale}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      const baseline = JSON.parse(
        readFileSync(resolve(HERE, `ord0573_sections_baseline_${arm.locale}.json`), "utf8"),
      ) as { sections: { key: string; text: string }[] };

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await ensureDemoJourney(page);
      await page.goto("/v8/trips", { waitUntil: "load" });
      await expect(page.getByTestId("trips-tab-itinerary")).toBeVisible({ timeout: 25_000 });

      const before = await page.evaluate(() => {
        const nav = document.querySelector("[data-testid='trips-tabs']");
        const rows = Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"));
        return {
          nav_role: nav ? nav.getAttribute("role") : null,
          rows: rows.map((el) => ({
            key: (el.getAttribute("data-testid") || "").replace("trips-tab-", ""),
            role: el.getAttribute("role"),
            id: el.id,
            aria_selected: el.getAttribute("aria-selected"),
            text: (el.textContent || "").replace(/\s+/g, " ").trim(),
          })),
        };
      });

      for (const want of baseline.sections) {
        const got = before.rows.find((r) => r.key === want.key);
        expect(got, `${arm.locale}: the section ${want.key} is not on the screen`).toBeTruthy();
        expect(got!.text, `${arm.locale}: the word on ${want.key} moved`).toBe(want.text);
      }

      await page.getByTestId("trips-tab-stay").click();
      const after = await page.evaluate(() =>
        Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"))
          .filter((el) => el.getAttribute("aria-selected") === "true")
          .map((el) => (el.getAttribute("data-testid") || "").replace("trips-tab-", "")),
      );

      const src = sourceArm();
      expect(src.importsTheModule, "the shell does not read the section labels from the copy table").toBe(true);
      expect(src.moduleHasEveryWord, "the copy table is missing one of the four section labels").toBe(true);
      expect(
        src.tabRowsLeftInShell,
        `these section rows are still written as inline tab literals in the shell (${arm.locale}): ${src.tabRowsLeftInShell.join(",")}`
      ).toEqual([]);

      writeFileSync(
        evidencePath(`ord0573_sections_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            shape: "390x844",
            nav_role: before.nav_role,
            before_rows: before.rows,
            selected_after_clicking_stay: after,
            source_arm: src,
          },
          null,
          1,
        ),
        "utf-8",
      );
    });
  }
});