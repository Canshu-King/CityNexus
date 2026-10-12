/**
 * ORD-0577 续 · 同一问量到另外两层导航（车道 8ac89982）
 *
 * 上一枚尺量的是底栏：十七屏里答六屏、静十一屏（`qoder-8ac89982-ord0577-off-route-bar-census-r1`）。
 * 这一枚量的是同一屏上的另外两层——手机抽屉（`#v8-nav-drawer`，由汉堡键打开）与桌面侧栏
 * （`nav.v8-nav`）——因为等你裁的甲／乙两条修法，代价取决于"别的层是不是已经把当前屏指出来了"。
 *
 * 读的是渲染结果：每一层里哪一枚行带着 `.active`、带不带 `data-contrast-role="state"`、带不带
 * `aria-current`、行上的字是什么。分母同上一枚：跑的时候现读两张路由表取并集。
 *
 * 两条仪器自检（不判产品，只判尺没瞎）：
 *  1. 正控：抽屉里**必须**恰有一枚行带 `.active`，且它就是当前屏那一枚（抽屉名单含全部十七枚 key），
 *     否则说明我连"有标记"这一档都读不到；
 *  2. 负对照：一个不指向任何屏的地址，按外壳自己的回退应被答成今天那一枚——同一把尺读得到这个回退。
 */
import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-nav-layers-census-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const NEGATIVE_CONTROL = "qoder-0577-not-a-route";

function tableKeys(src: string, table: string): string[] {
  const found = new RegExp("^export const " + table + "\\s*=", "m").exec(src);
  expect(found, table + " missing from " + ROUTES_FILE).not.toBeNull();
  const open = src.indexOf("[", found!.index);
  let depth = 0;
  let end = -1;
  for (let i = open; i < src.length; i += 1) {
    if (src[i] === "[") depth += 1;
    else if (src[i] === "]") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  return [...new Set([...src.slice(open, end + 1).matchAll(/\bkey:\s*"([a-z0-9-]+)"/g)].map((m) => m[1]))];
}

async function readDrawer(page: Page) {
  return page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']"));
    return {
      present: rows.length,
      rows: rows.map((el) => ({
        testid: el.getAttribute("data-testid"),
        active: el.classList.contains("active"),
        contrast_role: el.getAttribute("data-contrast-role"),
        aria_current: el.getAttribute("aria-current"),
        text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      })),
    };
  });
}

async function readSidebar(page: Page) {
  return page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("nav.v8-nav button"));
    return {
      present: rows.length,
      rows: rows.map((el) => ({
        active: el.classList.contains("active"),
        contrast_role: el.getAttribute("data-contrast-role"),
        aria_current: el.getAttribute("aria-current"),
        text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      })),
    };
  });
}

test.describe("ORD-0577 the other two navigation layers", () => {
  for (const arm of ARMS) {
    test(`drawer-and-sidebar-${arm.locale}`, async ({ page }) => {
      /* Phone width for the drawer phase: `.v8-mobile-menu` is display:none above 680px (styles.css
         @media max-width: 680px), so a run at the default viewport cannot open the drawer at all.
         The first version of this ruler forgot this line and reported a timeout as if the control
         were missing; the hamburger probe measured it visible with a 46x27 box on all 17 screens. */
      await page.setViewportSize({ width: 390, height: 844 });
      /* 17 screens x (load + open the drawer + read) plus the same 17 at desktop width does not fit in
         the default 60 s; the run that hit that ceiling reported it as a timeout at a waitForTimeout,
         which says nothing about the product. */
      test.setTimeout(420_000);
      const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
      const desktop = tableKeys(src, "desktopRoutes");
      const mobile = tableKeys(src, "mobileRoutes");
      const screens = [...desktop, ...mobile.filter((k) => !desktop.includes(k))];
      expect(screens.length, "the union of the two tables read empty").toBeGreaterThan(desktop.length - 1);

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await ensureDemoJourney(page);

      const rows: Record<string, unknown>[] = [];
      const walk = async (key: string, isControl: boolean) => {
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1200);
        await page.getByTestId("v8-mobile-menu").click();
        await expect(page.getByTestId("v8-nav-drawer")).toBeVisible({ timeout: 10_000 });
        const drawer = await readDrawer(page);
        await page.getByTestId("v8-drawer-close").click();
        return {
          requested: key,
          control: isControl,
          drawer_rows: drawer.present,
          drawer_marked: drawer.rows.filter((r) => r.active).map((r) => r.testid),
          drawer_aria_current: drawer.rows.filter((r) => r.aria_current).map((r) => r.testid),
          drawer_contrast_state: drawer.rows.filter((r) => r.contrast_role === "state").map((r) => r.testid),
          drawer_marked_text: drawer.rows.filter((r) => r.active).map((r) => r.text),
        };
      };

      for (const key of screens) {
        rows.push(await walk(key, false));
      }
      const control = await walk(NEGATIVE_CONTROL, true);
      rows.push(control);
      expect(
        control.drawer_marked,
        `the negative control was not answered as the Today row (read ${JSON.stringify(control.drawer_marked)})`
      ).toEqual(["v8-drawer-entry-hub"]);

      for (const row of rows.filter((r) => !r.control)) {
        expect(
          (row.drawer_marked as string[]).length,
          `${arm.locale}: ${row.requested} -- ${(row.drawer_marked as string[]).length} drawer rows carry .active`
        ).toBe(1);
        expect(row.drawer_marked, `${arm.locale}: ${row.requested} -- the marked drawer row is not its own`).toEqual([
          "v8-drawer-entry-" + row.requested,
        ]);
      }

      // the desktop sidebar, on a wide viewport, for the same screens
      await page.setViewportSize({ width: 1280, height: 900 });
      const sidebar: Record<string, unknown>[] = [];
      for (const key of screens) {
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(900);
        const bar = await readSidebar(page);
        sidebar.push({
          requested: key,
          rows: bar.present,
          marked_text: bar.rows.filter((r) => r.active).map((r) => r.text),
          aria_current: bar.rows.filter((r) => r.aria_current).map((r) => r.text),
          contrast_state: bar.rows.filter((r) => r.contrast_role === "state").map((r) => r.text),
        });
      }

      const drawerAriaTotal = rows.reduce((n, r) => n + (r.drawer_aria_current as string[]).length, 0);
      const sidebarAriaTotal = sidebar.reduce((n, r) => n + (r.aria_current as string[]).length, 0);
      const sidebarStateTotal = sidebar.reduce((n, r) => n + (r.contrast_state as string[]).length, 0);

      writeFileSync(
        evidencePath(`ord0577_layers_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            drawer_shape: "390x844",
            sidebar_shape: "1280x900",
            denominator: { desktop, mobile, union: screens },
            negative_control: { requested: NEGATIVE_CONTROL, drawer_marked: control.drawer_marked, drawer_marked_text: control.drawer_marked_text },
            drawer_aria_current_rows_total: drawerAriaTotal,
            sidebar_aria_current_rows_total: sidebarAriaTotal,
            sidebar_contrast_state_rows_total: sidebarStateTotal,
            drawer_rows: rows,
            sidebar_rows: sidebar,
          },
          null,
          1
        ),
        "utf-8"
      );
    });
  }
});
