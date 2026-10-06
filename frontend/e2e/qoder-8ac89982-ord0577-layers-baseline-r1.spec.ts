/**
 * ORD-0577 · 基线抓取（只读，不判）：把抽屉与桌面侧栏每一行的可见文字按屏记下来。
 *
 * 存在的理由：给"可见文字一字未动"这一句找一份**改动前**的读数。给一枚按钮加 `aria-current`
 * 从构造上就不该动文字，但"从构造上不该"是推理，不是量——所以先在改动前的字节上抓一份，
 * 交成基线件，让后面那把闸逐屏逐枚去比。
 */
import { test } from "@playwright/test";
import { writeFileSync } from "node:fs";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const SCREENS = [
  "hub", "live", "map", "studio", "stay", "discover", "import", "bookings", "footprints",
  "agent", "authoritative", "intelligence", "twin", "trash", "access", "trips", "me",
];

test.describe("ORD-0577 baseline capture: the two layers' visible words", () => {
  for (const arm of ARMS) {
    test(`capture-${arm.locale}`, async ({ page }) => {
      test.setTimeout(420_000);
      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await page.setViewportSize({ width: 390, height: 844 });
      await ensureDemoJourney(page);

      const screens: Record<string, unknown>[] = [];
      for (const key of SCREENS) {
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1100);
        await page.getByTestId("v8-mobile-menu").click();
        await page.getByTestId("v8-nav-drawer").waitFor({ state: "visible", timeout: 10_000 });
        const drawer = await page.evaluate(() => {
          const rows = Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']"));
          return { rows: rows.map((el) => ({ testid: el.getAttribute("data-testid"),
                                             text: (el.textContent || "").replace(/\s+/g, " ").trim() })) };
        });
        await page.getByTestId("v8-drawer-close").click();

        await page.setViewportSize({ width: 1280, height: 900 });
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(900);
        const sidebar = await page.evaluate(() => {
          const rows = Array.from(document.querySelectorAll("nav.v8-nav button"));
          return { rows: rows.map((el) => ({ text: (el.textContent || "").replace(/\s+/g, " ").trim() })) };
        });
        await page.setViewportSize({ width: 390, height: 844 });

        screens.push({ requested: key, drawer: drawer.rows, sidebar: sidebar.rows });
      }
      writeFileSync(
        evidencePath(`ord0577_layers_baseline_${arm.locale}.json`),
        JSON.stringify({ arm: arm.locale, screens }, null, 1),
        "utf-8",
      );
    });
  }
});
