  const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string; tab_text?: string; journey?: string }> = [
    {
      key: "spend-empty",
      locator: '[data-testid="spend-empty"]',
      expect_text: "现在还没有可加的花费",
      routes: ["trips"],
      tab_text: "花费",
      journey: "unlocatable",
      src: "frontend/src/features/trip/SpendPanel.tsx:105",
    },
    {
      key: "spend-no-lines",
      locator: '[data-testid="spend-no-lines"]',
      expect_text: "这台服务器对这趟行程一条花费项都没有答出来。",
      routes: ["trips"],
      tab_text: "花费",
      journey: "unlocatable",
      src: "frontend/src/features/trip/SpendPanel.tsx:173",
    },
    {
      key: "twin-no-capability",
      locator: "p.v8-empty-note",
      expect_text: "没有记录到明确的能力事实。",
      routes: ["twin"],
      journey: "staged",
      src: "frontend/src/features/traveler-twin/TwinPanel.tsx:33",
    },
    {
      key: "inbox-queue-empty",
      locator: '[data-testid="inbox-pending-empty"]',
      expect_text: "这里没有等你审核的确认单。",
      routes: ["bookings"],
      journey: "staged",
      src: "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:892",
    },
  ];

  /** Wait until the boot skeleton has left the page: measuring a shell that is still filling in is
      how the first run of this arm reported "cell not rendered" for a cell that does exist. */
  async function settleShell(page: Page) {
    await page
      .waitForFunction(
        () => {
          const t = (document.body && document.body.innerText) || "";
          return t.indexOf("正在准备城市周末行程") < 0 && document.querySelectorAll("[data-testid]").length > 3;
        },
        undefined,
        { timeout: 20_000 },
      )
      .catch(() => undefined);
  }

  async function measureCell(page: Page, cell: (typeof CENSUS_CELLS)[number], route: string) {
    return page.evaluate(
        (arg: any) => {
          const [sel, txt, rt] = arg;
          const CTRL = "button, a[href], input, select, textarea, [role=button]";
          const visible = (n: Element) => {
            const r = n.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          };
          const hits = Array.from(document.querySelectorAll(sel)).filter(
            (el) => ((el as HTMLElement).innerText ?? "").replace(/\s+/g, " ").indexOf(txt) >= 0,
          );
          if (!hits.length) return null;
          const el = hits[0] as HTMLElement;
          const leaf = ["p", "b", "span", "small", "dt", "dd", "code", "li"];
          const root = leaf.indexOf(el.tagName.toLowerCase()) >= 0 ? el.parentElement ?? el : el;
          const inside = Array.from(root.querySelectorAll(CTRL)).filter(visible);
          const screen = Array.from(document.querySelectorAll(CTRL)).filter(visible);
          const nav = screen.filter(
            (n) => !root.contains(n) && !!(n as HTMLElement).closest("nav, .v8-mobile-nav, [data-testid*='nav']"),
          );
          const nameOf = (n: Element) =>
            ((( n as HTMLElement).innerText ?? (n as any).getAttribute("aria-label") ?? "") as string)
              .replace(/\s+/g, " ")
              .trim()
              .slice(0, 40);
          return {
            route: rt,
            cell_root: `${el.tagName.toLowerCase()} -> ${root.tagName.toLowerCase()}.${String(root.className).slice(0, 40)}`,
            cell_text: (el.innerText ?? "").replace(/\s+/g, " ").trim().slice(0, 160),
            actions_inside: inside.length,
            actions_inside_names: inside.map(nameOf),
            actions_on_screen: screen.length,
            actions_on_screen_outside_nav: screen.length - nav.length,
            actions_in_nav: nav.length,
          };
        },
    [cell.locator, cell.expect_text, route],
  );
}

  /** One cell's two numbers: probe each route, and for a cell behind a section tab click that tab too. */
  async function cellActionNumbers(
    page: Page,
    cell: (typeof CENSUS_CELLS)[number],
    ids: { staged: string; unlocatable: string },
  ) {
    const which = cell.journey === "unlocatable" ? ids.unlocatable : ids.staged;
    await boot(page, which, "zh-CN");
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      await settleShell(page);
      if (cell.tab_text) {
        const opened = await page.evaluate((txt: string) => {
          const el = Array.from(document.querySelectorAll("button, [role=tab]")).find(
            (e) => ((e as HTMLElement).innerText ?? "").replace(/\s+/g, "").indexOf(txt) >= 0,
          );
          if (!el) return 0;
          (el as HTMLElement).click();
          return 1;
        }, cell.tab_text);
        if (opened) await page.waitForTimeout(1500);
      }
      const onTab = await measureCell(page, cell, route);
      if (onTab) return { ...onTab, reached_by: cell.tab_text ? `tab:${cell.tab_text}` : "route" };
      let found = await measureCell(page, cell, route);
      if (found) return { ...found, reached_by: "route" };
      if (cell.tab_text) {
        const clicked = await page.evaluate((txt: string) => {
          const els = Array.from(document.querySelectorAll("button, [role=tab], a")).filter(
            (e) => ((e as HTMLElement).innerText ?? "").replace(/\s+/g, "").indexOf(txt) >= 0,
          );
          if (!els.length) return 0;
          (els[0] as HTMLElement).click();
          return 1;
        }, cell.tab_text);
        if (clicked) {
          await page.waitForTimeout(1500);
          found = await measureCell(page, cell, route);
          attempts.push({ via: "tab", found });
          if (found) return { ...found, reached_by: `tab:${cell.tab_text}` };
        }
      }
      // the screen may own several tabs; sweep them once before giving up on this route
      for (let i = 0; i < 8; i++) {
        const opened = await page.evaluate((idx: number) => {
          const els = Array.from(document.querySelectorAll("button, [role=tab]")).filter((e) => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          if (idx >= els.length) return 0;
          (els[idx] as HTMLElement).click();
          return 1;
        }, i);
        if (!opened) break;
        await page.waitForTimeout(600);
        found = await measureCell(page, cell, route);
        if (found) return { ...found, reached_by: `tab-sweep#${i}` };
      }
    }
    return null;
  }

  test("C8 each census cell reports two numbers -- actions inside its own notice and actions on the screen", async ({
    page,
  }) => {
    const ids = { staged: await stageJourneyId(page), unlocatable: (await createUnlocatableJourney(page)).journey_id };
    const rows: Record<string, any> = {};
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell, ids);
      expect(
        one,
        node("C8", `${cell.src}: the empty state rendered on none of the probed routes, so there is nothing to count`),
      ).not.toBeNull();
      expect(
        String(one.cell_text),
        node("C8", `${cell.src}: the cell found does not say the sentence the ruler is told to expect`),
      ).toContain(cell.expect_text);
      expect(Number.isInteger(one.actions_inside), node("C8", `${cell.src}: no in-cell number was produced`)).toBe(true);
      expect(
        Number.isInteger(one.actions_on_screen),
        node("C8", `${cell.src}: no whole-screen number was produced`),
      ).toBe(true);
      rows[cell.key] = one;
    }
    /* The blindness this arm exists for is now a recorded fact, not a pass: a screen may own a dozen nav
       controls while the cell itself owns none.  A cell that does have an action simply stops appearing
       here -- nothing in this file has to be rewritten for that. */
    const zero = Object.entries(rows).filter(([, r]) => r.actions_inside === 0);
    for (const [key, r] of zero) {
      expect(
        r.actions_on_screen,
        node("C8", `${key} reads zero inside and the screen owns no control either -- that is a different defect`),
      ).toBeGreaterThan(0);
    }
    readings.C8 = {
      rule: "in-cell counts visible controls that are descendants of the cell's own notice block; whole-screen counts every visible control on the page, split by nav shell",
      cells: rows,
      cells_with_zero_inside: zero.map(([key]) => key),
    };
    await page.screenshot({ path: evidencePath(`ord0407/${RUN}__C8_two_numbers.png`) });
  });

  test("C9 every census cell owns at least one action inside its own notice (red by design until ORD-0407 slice 2 lands)", async ({
    page,
  }) => {
    const ids = { staged: await stageJourneyId(page), unlocatable: (await createUnlocatableJourney(page)).journey_id };
    const perCell: Record<string, any> = {};
    const empty: string[] = [];
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell, ids);
      expect(one, node("C9", `${cell.src}: cell not rendered, so the requirement cannot be judged`)).not.toBeNull();
      perCell[cell.key] = { route: one.route, actions_inside: one.actions_inside, names: one.actions_inside_names };
      if (one.actions_inside < 1) empty.push(`${cell.key}=${one.actions_inside}`);
    }
    readings.C9 = { per_cell: perCell, cells_without_own_action: empty };
    expect(
      empty,
      node("C9", `cells whose own notice offers no action, so the sentence names a remedy with no door: ${empty.join(", ")}`),
    ).toEqual([]);
  });
});
