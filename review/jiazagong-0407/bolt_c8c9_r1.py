"""ORD-0407 slice 2 (加闸工): bolt arms C8 and C9 onto the existing empty-state ruler.

The ruler judged whether the *screen* owns an action; the screen always owns the nav shell, so a cell
with zero actions inside it kept reading green.  C8 now produces two numbers per cell; C9 is the
product requirement and is red by design until the four census cells land their own actions.
Refuses to run twice (idempotent) and asserts the insertion point."""

import io
import sys

SPEC = r"D:\moodle\_qoder_jiazagong_0407\wt\frontend\e2e\qoder-ord0407-empty-state-actions.spec.ts"
TAIL = "    readings.C7 = { widths, by_width: byWidth };\n  });\n});\n"

ARMS = r'''
  /* C8/C9 -- 加闸工, ORD-0407 slice 2.  The arm above judged the whole screen; a traveller reading one
     card cannot use a control that lives in the nav shell, so "the screen has actions" was never the
     question.  C8 produces both numbers for every census cell.  C9 states the requirement (an action
     inside the cell's own notice) and is RED BY DESIGN until the four cells named in the ledger order
     land their buttons -- the owners are 屏读工 (SpendPanel, TwinPanel) and 快钉工 (inbox queue). */
  const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string }> = [
    {
      key: "spend-empty",
      locator: '[data-testid="spend-empty"]',
      expect_text: "现在还没有可加的花费",
      routes: ["spend", "trips", "hub"],
      src: "frontend/src/features/trip/SpendPanel.tsx:105",
    },
    {
      key: "spend-no-lines",
      locator: '[data-testid="spend-no-lines"]',
      expect_text: "这台服务器对这趟行程一条花费项都没有答出来。",
      routes: ["spend", "trips", "hub"],
      src: "frontend/src/features/trip/SpendPanel.tsx:173",
    },
    {
      key: "twin-no-capability",
      locator: "p.v8-empty-note",
      expect_text: "没有记录到明确的能力事实。",
      routes: ["twin"],
      src: "frontend/src/features/traveler-twin/TwinPanel.tsx:33",
    },
    {
      key: "inbox-queue-empty",
      locator: '[data-testid="inbox-pending-empty"]',
      expect_text: "这里没有等你审核的确认单。",
      routes: ["bookings"],
      src: "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:892",
    },
  ];

  /** One cell's two numbers, on the first probed route where the cell's own sentence is rendered. */
  async function cellActionNumbers(page: Page, cell: (typeof CENSUS_CELLS)[number]) {
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      const found = await page.evaluate(
        (arg: any) => {
          const [sel, txt] = arg;
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
            route,
            cell_root: `${el.tagName.toLowerCase()} -> ${root.tagName.toLowerCase()}.${String(root.className).slice(0, 40)}`,
            cell_text: (el.innerText ?? "").replace(/\s+/g, " ").trim().slice(0, 160),
            actions_inside: inside.length,
            actions_inside_names: inside.map(nameOf),
            actions_on_screen: screen.length,
            actions_on_screen_outside_nav: screen.length - nav.length,
            actions_in_nav: nav.length,
          };
        },
        [cell.locator, cell.expect_text],
      );
      if (found) return found;
    }
    return null;
  }

  test("C8 each census cell reports two numbers -- actions inside its own notice and actions on the screen", async ({
    page,
  }) => {
    const id = await stageJourneyId(page);
    await boot(page, id, "zh-CN");
    const rows: Record<string, any> = {};
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell);
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
    const id = await stageJourneyId(page);
    await boot(page, id, "zh-CN");
    const perCell: Record<string, any> = {};
    const empty: string[] = [];
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell);
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
'''

src = io.open(SPEC, encoding="utf-8", newline="").read()
if "CENSUS_CELLS" in src:
    print("ABORT already applied -- the arms are present")
    sys.exit(1)
if not src.endswith(TAIL):
    print("ABORT tail anchor not found; last 120 chars:", repr(src[-120:]))
    sys.exit(1)
new = src[: -len("});\n")] + ARMS
io.open(SPEC, "w", encoding="utf-8", newline="").write(new)
print("APPLIED C8/C9, bytes %d -> %d" % (len(src), len(new)))
