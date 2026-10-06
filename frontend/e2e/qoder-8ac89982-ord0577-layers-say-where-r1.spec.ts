/**
 * ORD-0577 续 · 抽屉与桌面侧栏也把"当前屏"说出来（车道 8ac89982）
 *
 * 上一格修的是底栏（十七屏都有答案）。这一格修另外两层：手机抽屉十七行、桌面侧栏十五行，**每一屏都
 * 已经有一行带 `.active`**，可那只是画出来的——`aria-current` 一个都没有（上一枚普查尺量到的：两层
 * 合计 0）。所以读屏用户在这两层里听不到"你在哪"。
 *
 * 这一格给带 `.active` 的那一行补 `aria-current="page"`，零新文案、不新增元素。判四件事：
 *  1. 抽屉（三百九十宽）：每一屏恰有一行带 `aria-current="page"`，且是该屏自己那一行，且**与带
 *     `.active` 的那一枚是同一枚**（防"标记"与"说话"各指一处）；
 *  2. 侧栏（一千二百八十宽）：十五屏各恰有一行带它；只在底栏表里的"行程／我的"两屏在侧栏里根本没有
 *     行，所以那里是 0，按现状记下，不算这条闸的红——那是"名单不全"，是另一件事；
 *  3. **可见文字一字未动**：抽屉与侧栏每一行的可见文字，逐屏逐枚与改动前抓的基线件比（基线是先在未改
 *     的字节上跑出来的，不是我背的）；
 *  4. 负对照：一个不指向任何屏的地址按外壳回退答成今天，所以抽屉里带 current 的必须是今天那一行。
 */
import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const MOBILE_ONLY = ["trips", "me"];
const NEGATIVE_CONTROL = "qoder-0577-not-a-route";

async function readLayers(page: Page, key: string) {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/" + key, { waitUntil: "load" });
  await page.waitForTimeout(1100);
  await page.getByTestId("v8-mobile-menu").click();
  await page.getByTestId("v8-nav-drawer").waitFor({ state: "visible", timeout: 10_000 });
  const drawer = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']")).map((el) => ({
      testid: el.getAttribute("data-testid"),
      aria_current: el.getAttribute("aria-current"),
      active: el.classList.contains("active"),
      text: (el.textContent || "").replace(/\s+/g, " ").trim(),
    })),
  );
  await page.getByTestId("v8-drawer-close").click();

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/v8/" + key, { waitUntil: "load" });
  await page.waitForTimeout(900);
  const sidebar = await page.evaluate(() =>
    Array.from(document.querySelectorAll("nav.v8-nav button")).map((el) => ({
      aria_current: el.getAttribute("aria-current"),
      active: el.classList.contains("active"),
      text: (el.textContent || "").replace(/\s+/g, " ").trim(),
    })),
  );
  return { drawer, sidebar };
}

test.describe("ORD-0577 the drawer and the sidebar say where you are", () => {
  for (const arm of ARMS) {
    test(`layers-say-where-${arm.locale}`, async ({ page }) => {
      test.setTimeout(600_000);
      const baseline = JSON.parse(
        readFileSync(resolve(HERE, `ord0577_layers_baseline_${arm.locale}.json`), "utf8"),
      ) as { screens: { requested: string; drawer: { testid: string; text: string }[];
                        sidebar: { text: string }[] }[] };

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await page.setViewportSize({ width: 390, height: 844 });
      await ensureDemoJourney(page);

      const rows: Record<string, unknown>[] = [];
      for (const screen of baseline.screens) {
        const { drawer, sidebar } = await readLayers(page, screen.requested);
        const drawerCurrent = drawer.filter((r) => r.aria_current === "page").map((r) => r.testid);
        const drawerActive = drawer.filter((r) => r.active).map((r) => r.testid);
        const sidebarCurrent = sidebar.filter((r) => r.aria_current === "page").map((r) => r.text);
        const sidebarActive = sidebar.filter((r) => r.active).map((r) => r.text);
        rows.push({
          requested: screen.requested,
          drawer_current: drawerCurrent,
          drawer_active: drawerActive,
          sidebar_current: sidebarCurrent,
          sidebar_active: sidebarActive,
        });

        expect(drawer.map((r) => r.text), `${arm.locale}: ${screen.requested} -- drawer words moved`).toEqual(
          screen.drawer.map((r) => r.text),
        );
        expect(sidebar.map((r) => r.text), `${arm.locale}: ${screen.requested} -- sidebar words moved`).toEqual(
          screen.sidebar.map((r) => r.text),
        );
        expect(
          drawerCurrent,
          `${arm.locale}: ${screen.requested} -- the drawer says nothing to a screen reader`
        ).toEqual(["v8-drawer-entry-" + screen.requested]);
        expect(drawerCurrent, `${arm.locale}: ${screen.requested} -- the spoken mark drifted off the painted one`)
          .toEqual(drawerActive);

        if (MOBILE_ONLY.includes(screen.requested)) {
          expect(sidebarCurrent, `${arm.locale}: ${screen.requested} has no sidebar row to speak`).toEqual([]);
        } else {
          expect(sidebarCurrent.length, `${arm.locale}: ${screen.requested} -- the sidebar does not mark one row`)
            .toBe(1);
          expect(sidebarCurrent, `${arm.locale}: ${screen.requested} -- the sidebar's mark drifted off the painted one`)
            .toEqual(sidebarActive);
        }
      }

      const control = await readLayers(page, NEGATIVE_CONTROL);
      const controlCurrent = control.drawer.filter((r) => r.aria_current === "page").map((r) => r.testid);
      expect(controlCurrent, "an address naming no screen must still be answered as Today").toEqual([
        "v8-drawer-entry-hub",
      ]);

      writeFileSync(
        evidencePath(`ord0577_layers_fixed_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            negative_control: { requested: NEGATIVE_CONTROL, drawer_current: controlCurrent },
            rows,
          },
          null,
          1,
        ),
        "utf-8",
      );
    });
  }
});
