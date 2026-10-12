/**
 * ORD-0577 probe: on which screens is the drawer's own door (the hamburger) actually visible at phone width?
 * Read-only, no clicks. Exists because the two-layer census timed out clicking it, and "the control is not
 * there" and "my click was wrong" are different facts -- this tells them apart before any assertion is written.
 */
import { test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";

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

test("ORD-0577 probe: hamburger visibility per screen at 390x844", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
  const desktop = tableKeys(src, "desktopRoutes");
  const mobile = tableKeys(src, "mobileRoutes");
  const screens = [...desktop, ...mobile.filter((k) => !desktop.includes(k))];
  await page.addInitScript(() => {
    try {
      localStorage.setItem("citynexus.locale", "zh-CN");
    } catch {}
  });
  await ensureDemoJourney(page);
  const rows: Record<string, unknown>[] = [];
  for (const key of screens) {
    await page.goto("/v8/" + key, { waitUntil: "load" });
    await page.waitForTimeout(1400);
    rows.push(
      await page.evaluate((k) => {
        const menu = document.querySelector("[data-testid='v8-mobile-menu']");
        const topbar = document.querySelector(".v8-topbar");
        const bar = document.querySelector("nav.v8-mobile-nav");
        const rect = menu ? menu.getBoundingClientRect() : null;
        const style = menu ? getComputedStyle(menu) : null;
        return {
          requested: k,
          menu_present: Boolean(menu),
          menu_display: style ? style.display : null,
          menu_box: rect ? [Math.round(rect.width), Math.round(rect.height)] : null,
          topbar_present: Boolean(topbar),
          topbar_display: topbar ? getComputedStyle(topbar).display : null,
          bar_present: Boolean(bar),
        };
      }, key)
    );
  }
  writeFileSync(
    evidencePath("ord0577_hamburger_probe.json"),
    JSON.stringify({ screens, rows }, null, 1),
    "utf-8"
  );
});
