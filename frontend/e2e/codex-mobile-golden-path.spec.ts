import { expect, test, type Page } from "@playwright/test";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";

const WIDTHS = [360, 390, 412, 430];

async function pageOverflow(page: Page) {
  return page.evaluate(() => {
    const width = window.innerWidth;
    const scrollWidth = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
    const offenders = Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 2 && rect.height > 2
          && rect.right > width + 1 && !/auto|scroll/.test(style.overflowX) && !element.closest("[data-allow-x]");
      })
      .slice(0, 5)
      .map((element) => element.getAttribute("data-testid") || element.className || element.tagName);
    return { width, scrollWidth, offenders };
  });
}

test.describe("Codex mobile golden path", () => {
  test("Today, Live and Wallet stay inside every target phone width", async ({ page }) => {
    test.setTimeout(120_000);
    await ensureDemoJourney(page);
    const failures: string[] = [];
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 844 });
      for (const screen of [
        { url: "/v8/hub", ready: ["today-heading", "today-attention"], name: "today" },
        { url: "/v8/live", ready: ["v8-live-journey", "live-journey-current"], name: "live" },
        { url: "/v8/bookings", ready: ["v8-bookings"], name: "wallet" },
      ]) {
        await openScreen(page, screen.url, screen.ready);
        const result = await pageOverflow(page);
        if (result.scrollWidth > width + 1 || result.offenders.length) {
          failures.push(`${screen.name}@${width}: ${JSON.stringify(result)}`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("blocked setup explains itself before the sticky action", async ({ page }) => {
    test.setTimeout(60_000);
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/v8", { waitUntil: "load" });
      await expect(page.getByTestId("trial-setup")).toBeVisible();
      const hint = page.getByTestId("trial-required-hint");
      const next = page.getByTestId("trial-next");
      await expect(hint).toBeVisible();
      await expect(next).toBeVisible();
      const geometry = await page.evaluate(() => {
        const box = (id: string) => document.querySelector<HTMLElement>(`[data-testid="${id}"]`)?.getBoundingClientRect();
        const hint = box("trial-required-hint");
        const next = box("trial-next");
        const arrival = box("trial-start");
        const departure = box("trial-end");
        return { hintBottom: hint?.bottom, nextTop: next?.top, arrivalBottom: arrival?.bottom, departureBottom: departure?.bottom };
      });
      expect(geometry.hintBottom, `hint geometry at ${width}`).toBeLessThanOrEqual(geometry.nextTop! + 1);
      expect(geometry.arrivalBottom, `arrival input at ${width}`).toBeLessThanOrEqual(geometry.nextTop! + 1);
      expect(geometry.departureBottom, `departure input at ${width}`).toBeLessThanOrEqual(geometry.nextTop! + 1);
    }
  });

  test("Wallet dark mode keeps commitment and inbox text readable", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark", media: "screen" });
    await ensureDemoJourney(page);
    await openScreen(page, "/v8/bookings", ["v8-bookings"]);
    const colors = await page.evaluate(() => {
      const card = getComputedStyle(document.querySelector(".v8-booking-card")!).backgroundColor;
      const inbox = getComputedStyle(document.querySelector(".v9-inbox")!).backgroundColor;
      const heading = getComputedStyle(document.querySelector(".v8-booking-card h2")!).color;
      const rgb = (value: string) => value.match(/[\d.]+/g)!.slice(0, 3).map(Number);
      const luminance = (value: string) => {
        const channel = rgb(value).map((component) => {
          const normalized = component / 255;
          return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * channel[0] + 0.7152 * channel[1] + 0.0722 * channel[2];
      };
      const values = [luminance(card), luminance(heading)].sort((a, b) => b - a);
      return { card, inbox, heading, headingContrast: (values[0] + 0.05) / (values[1] + 0.05) };
    });
    expect(colors.card).not.toBe("rgb(255, 255, 255)");
    expect(colors.inbox).not.toBe("rgb(255, 255, 255)");
    expect(colors.headingContrast).toBeGreaterThanOrEqual(4.5);
  });
});
