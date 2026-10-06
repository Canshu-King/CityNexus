/**
 * ORD-0577 续 · 那处"桌面宽度下两屏没有入口"到底有多宽（车道 8ac89982）
 *
 * 上一枚尺在一千二百八十宽下量到：侧栏列出桌面表那十五枚、底栏与汉堡键被样式表藏起来，于是只在底栏表里的
 * `trips` 与 `me` 两屏没有任何可点的入口。这枚尺问的是**这个洞有多宽**：在手机宽、六百八十断点上下、
 * 与更大的桌面宽度上各读一遍"侧栏显不显示／底栏显不显示／汉堡键显不显示／侧栏几行"，把"哪一段窗口宽度
 * 上那两屏进不去"这条线量出来——断点是样式表里写的那个数，这里让它自己从字节里读出来，不写死。
 *
 * 只读、不判产品。两条仪器自检：断点读自 `frontend/src/styles.css` 里真的把 `.v8-mobile-menu` 打开的
 * 那一条媒体查询；负对照在手机宽（侧栏藏、底栏与门显），宽屏则反过来。
 */
import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-entry-gap-width-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";
const STYLES_FILE = "src/styles.css";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const WIDTHS = [390, 680, 681, 900, 1280];
const MOBILE_ONLY = ["trips", "me"];

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

/** The max-width of the media query that turns .v8-mobile-menu on; not written down by hand. */
function breakpointPx(css: string): number {
  const rule = css.indexOf(".v8-mobile-menu { display: block");
  expect(rule, "styles.css no longer turns .v8-mobile-menu on -- this ruler would be measuring a fiction")
    .toBeGreaterThan(0);
  const queries = [...css.matchAll(/@media \(max-width: (\d+)px\)/g)].filter((m) => (m.index ?? 0) < rule);
  expect(queries.length, "no media query precedes that rule").toBeGreaterThan(0);
  return Number(queries[queries.length - 1][1]);
}

async function readChrome(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const shown = (el: Element | null) => {
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return getComputedStyle(el).display !== "none" && r.width > 0 && r.height > 0;
    };
    const sidebar = document.querySelector("nav.v8-nav");
    return {
      sidebar_shown: shown(sidebar),
      sidebar_rows: document.querySelectorAll("nav.v8-nav button").length,
      bar_shown: shown(document.querySelector("nav.v8-mobile-nav")),
      menu_shown: shown(document.querySelector("[data-testid='v8-mobile-menu']")),
    };
  });
}

test.describe("ORD-0577 how wide is the missing-entry gap", () => {
  for (const arm of ARMS) {
    test(`gap-width-${arm.locale}`, async ({ page }) => {
      test.setTimeout(300_000);
      const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
      const desktop = tableKeys(src, "desktopRoutes");
      const mobile = tableKeys(src, "mobileRoutes");
      const screens = [...desktop, ...mobile.filter((k) => !desktop.includes(k))];
      const bp = breakpointPx(readFileSync(resolve(FRONTEND, STYLES_FILE), "utf8"));

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await page.setViewportSize({ width: 390, height: 900 });
      await ensureDemoJourney(page);

      const rows: Record<string, unknown>[] = [];
      for (const width of WIDTHS) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto("/v8/hub", { waitUntil: "load" });
        await page.waitForTimeout(1000);
        const chrome = await readChrome(page);
        const row = {
          width,
          at_or_below_breakpoint: width <= bp,
          sidebar_shown: chrome.sidebar_shown,
          sidebar_rows: chrome.sidebar_rows,
          bar_shown: chrome.bar_shown,
          menu_shown: chrome.menu_shown,
          screens_with_no_clickable_entry:
            chrome.sidebar_shown && !chrome.bar_shown && !chrome.menu_shown ? MOBILE_ONLY : [],
        };
        rows.push(row);
        // the columns must actually change across the run, or they are not measuring anything
        if (width === 390) {
          expect(chrome.sidebar_shown, "the sidebar is not hidden at phone width").toBe(false);
          expect(chrome.bar_shown && chrome.menu_shown, "the bar or the door is missing at phone width").toBe(true);
        }
        if (width === 1280) {
          expect(chrome.sidebar_shown && !chrome.bar_shown && !chrome.menu_shown,
                 "at desktop width the sidebar is shown and the bar and the door are hidden").toBe(true);
          expect(chrome.sidebar_rows, "the desktop sidebar row count is not the desktop table's")
            .toBe(desktop.length);
        }
      }

      const gapWidths = rows.filter((r) => (r.screens_with_no_clickable_entry as string[]).length > 0).map((r) => r.width);
      writeFileSync(
        evidencePath(`ord0577_gap_width_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            css_breakpoint_px: bp,
            widths_probed: WIDTHS,
            denominator: { desktop, mobile, union: screens },
            widths_where_those_two_screens_have_no_entry: gapWidths,
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