"""Temporary diagnostic arm (加闸工): dump what each probed screen actually renders, so the C8 route
table is written from the screen rather than from a guess. Removed before the branch is committed."""

import io

SPEC = r"D:\moodle\_qoder_jiazagong_0407\wt\frontend\e2e\qoder-ord0407-empty-state-actions.spec.ts"
TAIL = "  });\n});\n"

DUMP = r'''  test("C8D dump every probed screen", async ({ page }) => {
    const id = await stageJourneyId(page);
    await boot(page, id, "zh-CN");
    const lines: string[] = [];
    const routes = ["hub", "trips", "spend", "bookings", "twin", "stay", "me"];
    const probes = [
      '[data-testid="spend-empty"]',
      '[data-testid="spend-no-lines"]',
      '[data-testid="inbox-pending-empty"]',
      "p.v8-empty-note",
      '[data-testid="spend-declared"]',
    ];
    for (const route of routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      await page.waitForTimeout(3000);
      const shot = await page.evaluate((sel: any) => {
        const t = (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 300);
        const found: Record<string, number> = {};
        for (const s of sel) found[s] = document.querySelectorAll(s).length;
        const clickables = Array.from(document.querySelectorAll("button, [role=tab]"))
          .map((e) => ((e as HTMLElement).innerText || e.getAttribute("aria-label") || "").replace(/\s+/g, "").slice(0, 12))
          .filter((x) => x.length > 0)
          .slice(0, 30);
        return { t, found, clickables, url: location.pathname };
      }, probes);
      lines.push(`ROUTE ${route} url=${shot.url}`);
      lines.push(`  text: ${shot.t}`);
      lines.push(`  probes: ${JSON.stringify(shot.found)}`);
      lines.push(`  clickables: ${shot.clickables.join(" | ")}`);
      if (route === "trips") {
        const before = shot.t;
        await page.evaluate(() => {
          const el = Array.from(document.querySelectorAll("button, [role=tab]")).find(
            (e) => ((e as HTMLElement).innerText || "").replace(/\s+/g, "").indexOf("花费") >= 0,
          );
          if (el) (el as HTMLElement).click();
        });
        await page.waitForTimeout(2500);
        const after = await page.evaluate((sel: any) => {
          const found: Record<string, number> = {};
          for (const s of sel) found[s] = document.querySelectorAll(s).length;
          return { t: (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 300), found };
        }, probes);
        lines.push(`  AFTER-CLICK-花费 tab_changed=${before !== after.t}`);
        lines.push(`  after text: ${after.t}`);
        lines.push(`  after probes: ${JSON.stringify(after.found)}`);
      }
    }
    writeFileSync("D:/moodle/_qoder_jiazagong_0407/dump_screens_r1.txt", lines.join("\n"), "utf-8");
  });
});
'''

src = io.open(SPEC, encoding="utf-8", newline="").read()
assert src.endswith(TAIL), repr(src[-40:])
io.open(SPEC, "w", encoding="utf-8", newline="").write(src[: -len(TAIL)] + "  });\n" + DUMP)
print("DUMP ARM ADDED")
