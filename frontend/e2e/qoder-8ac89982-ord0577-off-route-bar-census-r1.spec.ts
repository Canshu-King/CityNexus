/**
 * ORD-0577 · 底栏在"主路由之外"的屏上到底答不答"你在哪"（车道 8ac89982）
 *
 * 派单原话：`/v8/trash` 与 `/v8/stay` 这类屏上四枚按钮无人带 `aria-current`、也无人带
 * `data-contrast-role="state"`，底栏在"四枚主路由之外"仍不回答"你在哪"。两条路可走：把该屏归到最近的
 * 一枚主路由并具名规则，或明确画一枚"不在主路由上"的状态。验收要两臂逐屏读数、且不许改动可见文字。
 *
 * 这枚尺先只做**量**，不做判：分母不是我背下来的名单，是从 `src/routes/v8Routes.ts` 两张表里现读出来的
 * key（`desktopRoutes` + `mobileRoutes`），所以新加一屏藏不住。逐屏读回来的是：落点路径（判有没有被弹回）、
 * 底栏每枚按钮的 `aria-current` / `data-contrast-role` / class / 可见文字、以及"带 current 的枚数"。
 *
 * 三条仪器自检（它们不判产品，只判尺自己没瞎）：
 *  1. 分母非空，且与源文件两张表的 key 集合逐枚相同；
 *  2. 底栏那几枚主路由键：在自己那一屏上必须恰有一枚带 current —— 计数器证明它能看见"有"；
 *  3. 负对照：一个不存在的路由必须被弹回（`landed_key` 不等于请求的 key），证明"落点"这一列真的在动。
 */
import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-off-route-bar-census-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const NEGATIVE_CONTROL = "qoder-0577-not-a-route";

function tableKeys(src: string, table: string): string[] {
  const decl = new RegExp("^export const " + table + "\\s*=", "m");
  const found = decl.exec(src);
  expect(found, table + " is missing from " + ROUTES_FILE + " -- the denominator would be empty").not.toBeNull();
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
  const body = src.slice(open, end + 1);
  const keys = [...body.matchAll(/\bkey:\s*"([a-z0-9-]+)"/g)].map((m) => m[1]);
  return [...new Set(keys)];
}

test.describe("ORD-0577 the bar on screens outside the main routes", () => {
  for (const arm of ARMS) {
    test(`off-route-census-${arm.locale}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
      const desktop = tableKeys(src, "desktopRoutes");
      const mobile = tableKeys(src, "mobileRoutes");
      expect(desktop.length, "the desktop table read empty").toBeGreaterThan(3);
      expect(mobile.length, "the mobile table read empty").toBeGreaterThan(3);

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await ensureDemoJourney(page);

      const readBar = async () =>
        page.evaluate(() => {
          const nav = document.querySelector("nav.v8-mobile-nav");
          const buttons = Array.from(document.querySelectorAll("nav.v8-mobile-nav button"));
          const crumb = document.querySelector(".v8-breadcrumb strong");
          return {
            landed_href: location.href,
            breadcrumb: (crumb?.textContent || "").trim(),
            bar_present: Boolean(nav),
            bar_label: nav ? nav.getAttribute("aria-label") : null,
            buttons: buttons.map((el) => ({
              testid: el.getAttribute("data-testid"),
              aria_current: el.getAttribute("aria-current"),
              contrast_role: el.getAttribute("data-contrast-role"),
              active_class: el.classList.contains("active"),
              text: (el.textContent || "").replace(/\s+/g, " ").trim(),
            })),
          };
        });

      const rows: Record<string, unknown>[] = [];
      /* The denominator is the union of both tables: `trips` and `me` are bar items that live only in
         `mobileRoutes`, so iterating the desktop table alone would have left two main-route screens
         unmeasured -- which is how a census gets a denominator that flatters it. */
      const screens = [...desktop, ...mobile.filter((k) => !desktop.includes(k))];
      expect(screens.length, "the union of the two tables read empty").toBeGreaterThan(desktop.length - 1);
      for (const key of screens) {
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1500);
        const bar = await readBar();
        const landed = (bar.landed_href.match(/\/v8\/([a-z0-9-]+)/) || [])[1] ?? "";
        const current = bar.buttons.filter((b) => b.aria_current === "page").map((b) => b.testid);
        const state = bar.buttons.filter((b) => b.contrast_role === "state").map((b) => b.testid);
        rows.push({
          requested: key,
          landed,
          url_key_unchanged: landed === key,
          in_mobile_bar: mobile.includes(key),
          breadcrumb: bar.breadcrumb,
          bar_present: bar.bar_present,
          bar_label: bar.bar_label,
          buttons: bar.buttons.length,
          current,
          state,
          silent: bar.bar_present && current.length === 0 && state.length === 0,
          texts: bar.buttons.map((b) => b.text),
        });
      }

      /* Negative control: a route that names no screen is not bounced in the address -- the resolver
         (V8Experience.tsx addressFromPath) answers `hub` and leaves the URL alone. So the control
         asserts on the shell's own answer, and records the unchanged address as a fact rather than
         pretending it is the signal. */
      await page.goto("/v8/" + NEGATIVE_CONTROL, { waitUntil: "load" });
      await page.waitForTimeout(1200);
      const control = await readBar();
      const controlCurrent = control.buttons
        .filter((b) => b.aria_current === "page")
        .map((b) => b.testid);
      expect(
        controlCurrent,
        `the negative control was not answered as Today -- the counter cannot see a positive answer (read ${JSON.stringify(controlCurrent)})`
      ).toEqual(["nav-hub"]);

      const mobileRows = rows.filter((r) => r.in_mobile_bar);
      for (const row of mobileRows) {
        expect(
          (row.current as string[]).length,
          `${arm.locale}: ${row.requested} is a main-route screen but ${(row.current as string[]).length} buttons claim current`
        ).toBe(1);
      }

      const silent = rows.filter((r) => r.silent).map((r) => r.requested);
      const addressMoved = rows.filter((r) => !r.url_key_unchanged).map((r) => r.requested);
      writeFileSync(
        evidencePath(`ord0577_census_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            shape: "390x844",
            denominator: { desktop, mobile, union: screens },
            negative_control: { requested: NEGATIVE_CONTROL, answered_as: controlCurrent, breadcrumb: control.breadcrumb },
            silent_on_screens: silent,
            requested_keys_whose_address_moved: addressMoved,
            rows,
          },
          null,
          1
        ),
        "utf-8"
      );
    });
  }
});
