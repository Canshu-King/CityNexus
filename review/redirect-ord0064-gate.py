"""Redirect the ORD-0064 family gate per ORD-0212: the hub keeps only the tight verdict.

Written as a file because the replacement text contains comment lines that the shell scan reads as
UNC paths.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-trip-shape-and-budget.spec.ts"

OLD = '''      await openHubWithJourney(page, ["today-heading", "budget-advisory"]);
      const advisory = page.getByTestId("budget-advisory");
      const text = (await advisory.innerText()).replace(/\\s+/g, " ").trim();
      seen[arm.currency] = text;
      expect(
        text.includes("¥"),
        node("budget-line-never-borrows-a-symbol",
          `${arm.currency}: the advisory prints a symbol again, and ¥ is ambiguous between CNY and JPY: ${JSON.stringify(text)}`),
      ).toBe(false);
      expect(
        text,
        node("budget-line-never-borrows-a-symbol", `${arm.currency}: the ISO code the money is in never reaches the line`),
      ).toContain(arm.currency);
      // An incomparable floor must not produce a tightness verdict: that would be comparing
      // yen against yuan and reporting the result as advice.
      expect(
        await advisory.getAttribute("data-tight"),
        node("budget-line-never-borrows-a-symbol",
          `${arm.currency}: floor_comparable=${arm.comparable} but the screen chose ${JSON.stringify(
            await advisory.getAttribute("data-tight"),
          )}, expected ${arm.wantTight}`),
      ).toBe(arm.wantTight);'''

NEW = '''      /* ORD-0212 (user, 15:00): the hub keeps only the `tight` verdict.  A non-tight reference
         no longer renders the advisory at all, so the two arms now assert different things:
         JPY (incomparable, non-tight) -> the block is absent from the hub, and CNY (comparable,
         tight) -> the block is present with its verdict.  The full text+hint pair still lives on
         the budget-review surface. */
      if (arm.wantTight === "true") {
        await openHubWithJourney(page, ["today-heading", "budget-advisory"]);
        const advisory = page.getByTestId("budget-advisory");
        const text = (await advisory.innerText()).replace(/\\s+/g, " ").trim();
        seen[arm.currency] = text;
        expect(
          text.includes("¥"),
          node("budget-line-never-borrows-a-symbol",
            `${arm.currency}: the advisory prints a symbol again, and ¥ is ambiguous between CNY and JPY: ${JSON.stringify(text)}`),
        ).toBe(false);
        expect(
          text,
          node("budget-line-never-borrows-a-symbol", `${arm.currency}: the ISO code the money is in never reaches the line`),
        ).toContain(arm.currency);
        expect(
          await advisory.getAttribute("data-tight"),
          node("budget-line-never-borrows-a-symbol",
            `${arm.currency}: floor_comparable=${arm.comparable} but the screen chose ${JSON.stringify(
              await advisory.getAttribute("data-tight"),
            )}, expected ${arm.wantTight}`),
        ).toBe(arm.wantTight);
      } else {
        await openHubWithJourney(page, ["today-heading"]);
        await page.waitForTimeout(1_500);
        const advisoryCount = await page.getByTestId("budget-advisory").count();
        const hubText = (await page.locator("body").innerText()).replace(/\\s+/g, " ");
        seen[arm.currency] = `budget-advisory count=${advisoryCount}`;
        expect(
          advisoryCount,
          node("budget-line-never-borrows-a-symbol",
            `${arm.currency}: the hub still renders the averaged-reference advisory that ORD-0212 removed (count=${advisoryCount})`),
        ).toBe(0);
        expect(
          /每人每天约/.test(hubText),
          node("budget-line-never-borrows-a-symbol",
            `${arm.currency}: the derived per-person number still appears on the hub without its tier: "${hubText.slice(0, 200)}"`),
        ).toBe(false);
      }'''


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    count = text.count(OLD)
    if count != 1:
        print(f"ABORT: anchor appears {count} times, expected 1")
        return 2
    text = text.replace(OLD, NEW, 1)
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    print("redirected:", "ORD-0212" in text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
