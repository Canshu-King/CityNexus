/**
 * ORD-0577 续 · 桌面宽度下，每一屏在导航里到底有没有入口（车道 8ac89982）
 *
 * 上一枚尺在侧栏那里记下一处"名单不全"：侧栏只遍历 `desktopRoutes`（十五枚），所以只在底栏表里的
 * "行程／我的"两屏在侧栏里连一行都没有。这枚尺把那句话量实：在**桌面宽度**下，底栏与汉堡键都被样式表
 * 藏起来了（`frontend/src/styles.css`，`.v8-mobile-nav, .v8-mobile-menu { display: none }`，只在
 * 680 宽以下的媒体查询里才打开），于是那两屏在桌面宽度上可能**一枚可点的入口都没有**——只能靠手打地址。
 *
 * 只读、不判产品：逐屏（十七屏）、逐层（侧栏／底栏／汉堡键→抽屉）记下"这一屏有没有一枚指向它的入口"，
 * 以及各层本身在两种宽度下到底显不显示。
 *
 * 两条仪器自检：
 *  1. 侧栏行数必须等于 `desktopRoutes` 的枚数（现读源文件），否则分母读错了；
 *  2. 负对照：三百九十宽下侧栏应被藏起、底栏与汉堡键应显示——证明"显不显示"这一列真的在动。
 */
import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-desktop-entries-census-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];

function tableKeys(src: string, table: string): string[] {
  const found = new RegExp("^export const " + table + "\\s*=", "m").exec(src);
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

async function readChrome(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const shown = (el: Element | null) => {
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return getComputedStyle(el).display !== "none" && r.width > 0 && r.height > 0;
    };
    const sidebar = document.querySelector("nav.v8-nav");
    const bar = document.querySelector("nav.v8-mobile-nav");
    const menu = document.querySelector("[data-testid='v8-mobile-menu']");
    return {
      sidebar_shown: shown(sidebar),
      sidebar_rows: Array.from(document.querySelectorAll("nav.v8-nav button")).map(
        (el) => (el.textContent || "").replace(/\s+/g, " ").trim(),
      ),
      bar_shown: shown(bar),
      bar_buttons: Array.from(document.querySelectorAll("nav.v8-mobile-nav button")).map(
        (el) => el.getAttribute("data-testid"),
      ),
      menu_shown: shown(menu),
    };
  });
}

test.describe("ORD-0577 which screens have a chrome entry at desktop width", () => {
  for (const arm of ARMS) {
    test(`desktop-entries-${arm.locale}`, async ({ page }) => {
      test.setTimeout(420_000);
      const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
      const desktop = tableKeys(src, "desktopRoutes");
      const mobile = tableKeys(src, "mobileRoutes");
      const screens = [...desktop, ...mobile.filter((k) => !desktop.includes(k))];

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await page.setViewportSize({ width: 390, height: 844 });
      await ensureDemoJourney(page);

      // negative control: at phone width the sidebar is hidden and the bar and the door are shown
      await page.goto("/v8/hub", { waitUntil: "load" });
      await page.waitForTimeout(1200);
      const phone = await readChrome(page);
      expect(phone.sidebar_shown, "the sidebar is not hidden at phone width -- the shown column is not moving")
        .toBe(false);
      expect(phone.bar_shown && phone.menu_shown, "the bar or the drawer door is missing at phone width").toBe(true);

      await page.setViewportSize({ width: 1280, height: 900 });
      const rows: Record<string, unknown>[] = [];
      for (const key of screens) {
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1000);
        const chrome = await readChrome(page);
        const crumb = await page.evaluate(
          () => (document.querySelector(".v8-breadcrumb strong")?.textContent || "").trim(),
        );
        const row = {
          requested: key,
          breadcrumb: crumb,
          sidebar_shown: chrome.sidebar_shown,
          sidebar_rows: chrome.sidebar_rows.length,
          bar_shown: chrome.bar_shown,
          menu_shown: chrome.menu_shown,
          in_desktop_table: desktop.includes(key),
        };
        rows.push(row);
        expect(chrome.sidebar_rows.length, `${arm.locale}: ${key} -- the sidebar row count is not the desktop table's`)
          .toBe(desktop.length);
      }

      writeFileSync(
        evidencePath(`ord0577_desktop_entries_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            shape: "1280x900",
            denominator: { desktop, mobile, union: screens },
            negative_control_phone_width: {
              sidebar_shown: phone.sidebar_shown,
              bar_shown: phone.bar_shown,
              menu_shown: phone.menu_shown,
            },
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
