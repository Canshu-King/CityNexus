import { expect, test, type Page } from "@playwright/test";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * Mission 003 ruling ④ — the theme root contract.
 *
 * System / Light / Dark, persisted, resolved onto `<html data-theme>`, defaulting to the OS
 * for anyone who never chose.  The part a `@media (prefers-color-scheme: dark)` block can
 * never express is a *pinned* choice: "the OS is light and the traveller chose dark" has no
 * media query that matches it.  So the nodes below drive the OS and the stored choice
 * independently, and the legibility node runs in exactly that mismatched combination.
 *
 * A switch is not a cover for an unreadable theme: `theme-pinned-dark-legible-on-light-os`
 * scans the painted text in the combination nobody could reach before the contract existed.
 */

const FILE = "e2e/qoder-theme-contract.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

async function rootTheme(page: Page): Promise<string | null> {
  return page.evaluate(() => document.documentElement.dataset.theme ?? null);
}

async function setChoice(page: Page, choice: string | null) {
  await page.addInitScript((value) => {
    if (value === null) localStorage.removeItem("citynexus.theme");
    else localStorage.setItem("citynexus.theme", value as string);
  }, choice);
}

/** WCAG relative luminance, computed in the page against what is actually painted. */
async function contrastFailures(page: Page) {
  return page.evaluate(() => {
    const luminance = (r: number, g: number, b: number) => {
      const channel = (value: number) => {
        const c = value / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      };
      return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
    };
    const parse = (colour: string) => {
      const match = colour.match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const [r, g, b, a] = match[1].split(",").map((part) => Number.parseFloat(part.trim()));
      return { r, g, b, a: a === undefined ? 1 : a };
    };
    const composite = (element: Element) => {
      let node: HTMLElement | null = element as HTMLElement;
      let acc = { r: 255, g: 255, b: 255 };
      const stack: { r: number; g: number; b: number; a: number }[] = [];
      while (node) {
        const parsed = parse(getComputedStyle(node).backgroundColor);
        if (parsed && parsed.a > 0) stack.push(parsed);
        node = node.parentElement;
      }
      for (const layer of stack.reverse()) {
        acc = {
          r: acc.r * (1 - layer.a) + layer.r * layer.a,
          g: acc.g * (1 - layer.a) + layer.g * layer.a,
          b: acc.b * (1 - layer.a) + layer.b * layer.a,
        };
      }
      return acc;
    };
    const failures: string[] = [];
    const seen = new Set<Element>();
    for (const element of Array.from(document.querySelectorAll("b, strong, span, p, small, a, button, h1, h2, h3"))) {
      if (seen.has(element)) continue;
      seen.add(element);
      const style = getComputedStyle(element);
      if (style.visibility === "hidden" || style.display === "none") continue;
      const rect = element.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) continue;
      const text = Array.from(element.childNodes)
        .filter((child) => child.nodeType === Node.TEXT_NODE)
        .map((child) => child.textContent ?? "")
        .join("")
        .trim();
      if (!text) continue;
      const foreground = parse(style.color);
      if (!foreground) continue;
      const background = composite(element);
      const first = luminance(foreground.r, foreground.g, foreground.b);
      const second = luminance(background.r, background.g, background.b);
      const ratio = (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
      const size = parseFloat(style.fontSize) || 16;
      const bold = Number(style.fontWeight) >= 700;
      const required = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5;
      if (ratio < required) {
        const describe = (element: Element) =>
          `${element.tagName.toLowerCase()}${
            element.classList.length ? `.${Array.from(element.classList).join(".")}` : ""
          }`;
        failures.push(
          `${describe(element)} (in ${describe(element.parentElement ?? element)}) `
          + `"${text.slice(0, 34)}" ${ratio.toFixed(2)}/${required} ${size}px/${style.fontWeight}`,
        );
      }
    }
    return failures;
  });
}

test.describe("Ruling ④ the theme root contract", () => {
  test("theme-system-default-follows-the-os", async ({ page }) => {
    test.setTimeout(120_000);
    await setChoice(page, null);
    for (const [scheme, want] of [
      ["light", "light"],
      ["dark", "dark"],
    ] as const) {
      await page.emulateMedia({ colorScheme: scheme, media: "screen" });
      await page.setViewportSize({ width: 390, height: 844 });
      await ensureDemoJourney(page);
      await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
      const got = await rootTheme(page);
      expect(
        got,
        node("theme-system-default-follows-the-os",
          `with no stored choice and the OS at ${scheme}, the root said ${JSON.stringify(got)}`),
      ).toBe(want);
    }
  });

  test("theme-choice-persists-and-overrides-the-os", async ({ page }) => {
    test.setTimeout(120_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    await setChoice(page, "dark");
    await ensureDemoJourney(page);
    await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
    const first = await rootTheme(page);
    await page.reload({ waitUntil: "networkidle" });
    const after = await rootTheme(page);
    expect(
      first,
      node("theme-choice-persists-and-overrides-the-os",
        "a pinned dark choice on a light OS must win; the media query alone could never say this"),
    ).toBe("dark");
    expect(
      after,
      node("theme-choice-persists-and-overrides-the-os",
        `the choice did not survive a reload (${first} -> ${after})`),
    ).toBe("dark");
    // And the inverse pin must hold too.
    await setChoice(page, "light");
    await page.emulateMedia({ colorScheme: "dark", media: "screen" });
    await page.reload({ waitUntil: "networkidle" });
    await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
    expect(
      await rootTheme(page),
      node("theme-choice-persists-and-overrides-the-os",
        "a pinned light choice must survive a dark OS"),
    ).toBe("light");
  });

  test("theme-pinned-dark-legible-on-light-os", async ({ page }) => {
    test.setTimeout(150_000);
    /* The combination that did not exist before the contract: the traveller's device is in
       light mode and they chose dark.  A switch that paints an unreadable theme is not a
       feature, so the scan runs here rather than only under a dark OS. */
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    await setChoice(page, "dark");
    await ensureDemoJourney(page);
    const scanned: Record<string, string[]> = {};
    for (const [route, anchors] of [
      ["/v8/hub", ["today-heading", "today-attention"]],
      ["/v8/live", ["v8-live-journey", "live-journey-current"]],
    ] as const) {
      await openScreen(page, route, anchors);
      const failures = await contrastFailures(page);
      scanned[route] = failures;
      expect(
        failures,
        node("theme-pinned-dark-legible-on-light-os",
          `pinned dark on a light OS left ${failures.length} unreadable text node(s) on ${route}: `
          + JSON.stringify(failures.slice(0, 6))),
      ).toEqual([]);
    }
    writeFileSync(
      evidencePath("ui-overnight/theme-pinned-dark.json"),
      JSON.stringify({ generatedBy: "e345b9d6", order: "RULING-4", scanned }, null, 2) + "\n",
      "utf-8",
    );
  });

  test("theme-root-attribute-is-the-only-dark-switch", async () => {
    test.setTimeout(120_000);
    /* The stylesheets must not keep a private OS-driven path alongside the contract, or a
       pinned choice silently stops meaning anything on those surfaces.  Read from disk:
       fetching `/styles.css` from the dev server returns a transformed JS module, which
       would let this pass without ever looking at CSS. */
    const names = ["styles.css", "design-tokens.css", "v10.css"];
    const read = names.map((name) => {
      const path = fileURLToPath(new URL(`../src/${name}`, import.meta.url));
      return { name, text: existsSync(path) ? readFileSync(path, "utf-8") : null };
    });
    const unread = read.filter((item) => item.text === null).map((item) => item.name);
    expect(
      unread,
      node("theme-root-attribute-is-the-only-dark-switch",
        `could not read these stylesheets, so the guard saw nothing: ${JSON.stringify(unread)}`),
    ).toEqual([]);
    const offenders = read
      .filter((item) => /prefers-color-scheme:\s*dark/.test(item.text ?? ""))
      .map((item) => item.name);
    expect(
      offenders,
      node("theme-root-attribute-is-the-only-dark-switch",
        `these stylesheets still key dark off the OS directly: ${JSON.stringify(offenders)}. `
        + "A pinned choice cannot override a media query, so those surfaces would ignore the switch"),
    ).toEqual([]);
  });
});
